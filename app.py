import os
import time
import socket
import threading
from collections import deque
import cv2
from flask import Flask, render_template, jsonify, request, send_from_directory

app = Flask(__name__)

# --- Cấu hình Thư mục Lưu trữ (Base Directory) ---
def get_base_dir():
    target = "/home/debian/NguyenVanQuan"
    try:
        if not os.path.exists(target):
            os.makedirs(target, exist_ok=True)
        # Kiểm tra xem có quyền ghi vào thư mục này không
        test_file = os.path.join(target, "perm_test.tmp")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return target
    except Exception:
        # Fallback về thư mục cục bộ của dự án
        local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NguyenVanQuan")
        os.makedirs(local_dir, exist_ok=True)
        return local_dir

BASE_DIR = get_base_dir()
print(f"[*] Base Directory sử dụng: {BASE_DIR}")

# --- Trạng thái Chia sẻ Giữa các Luồng (Shared State) ---
state = {
    "pot_voltage": 1.65,          # Điện áp biến trở giả lập (0.0V - 3.3V)
    "pwm15_duty": 50.0,           # Duty cycle của Luồng 2 (15ms PWM) - tính từ pot_voltage
    "pwm40_duty": 50.0,           # Duty cycle của Luồng 4 (40ms PWM) - đọc từ cau6.txt
    "blur_kernel": 15,            # Kích thước bộ lọc Gaussian Blur (Luồng 3)
    "blur_status": "Chưa bắt đầu", # Trạng thái thực thi của Luồng 3
    "gpio25_state": 0,            # Trạng thái logic hiện tại của GPIO_25 (Luồng 1)
    "gpio12_state_15ms": 0,       # Trạng thái logic PWM 15ms trên GPIO_12 (Luồng 2)
    "gpio12_state_40ms": 0,       # Trạng thái logic PWM 40ms trên GPIO_12 (Luồng 4)
    "socket_logs": deque(maxlen=50), # Nhật ký giao tiếp TCP Socket Client-Server
    "thread_logs": deque(maxlen=50), # Nhật ký chung của 4 luồng
}

# Khóa đồng bộ cho Shared State
state_lock = threading.Lock()

def add_thread_log(message):
    timestamp = time.strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    with state_lock:
        state["thread_logs"].append(log_line)
    print(log_line)

def add_socket_log(message):
    timestamp = time.strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    with state_lock:
        state["socket_logs"].append(log_line)
    print(f"[Socket] {log_line}")

# Khởi tạo file cau6.txt mặc định (Duty cycle = 50%)
def init_files():
    cau6_path = os.path.join(BASE_DIR, "cau6.txt")
    if not os.path.exists(cau6_path):
        try:
            with open(cau6_path, "w") as f:
                f.write("50")
            add_thread_log(f"Đã tạo file mặc định {cau6_path} với giá trị 50%")
        except Exception as e:
            add_thread_log(f"Lỗi khởi tạo file: {e}")

# ==========================================
# LUỒNG 1: Phát xung vuông 13kHz (GPIO_25)
# ==========================================
def thread_1_square_wave():
    add_thread_log("Luồng 1: Đã khởi chạy (Phát xung 13kHz trên GPIO_25)")
    freq = 13000.0  # 13 kHz
    period = 1.0 / freq
    half_period = period / 2.0
    
    # Để tránh tốn 100% CPU trên hệ điều hành không thời gian thực,
    # chúng ta cập nhật trạng thái logic hiển thị theo thời gian thực tế.
    while True:
        t = time.time()
        # Tính toán mức logic tại thời điểm t
        current_state = 1 if int(t * freq * 2) % 2 == 0 else 0
        with state_lock:
            state["gpio25_state"] = current_state
        time.sleep(0.001)  # Cập nhật trạng thái hiển thị mỗi 1ms

# ==========================================
# LUỒNG 2: Phát xung PWM 15ms (GPIO_12) + ADS1115
# ==========================================
def thread_2_pwm_15ms():
    add_thread_log("Luồng 2: Đã khởi chạy (PWM 15ms trên GPIO_12 - Đọc từ ADS1115)")
    # Chu kỳ 15ms = 0.015s
    period = 0.015
    
    while True:
        with state_lock:
            voltage = state["pot_voltage"]
        
        # Giả lập đọc ADC từ ADS1115 (0V - 3.3V) và ánh xạ sang duty cycle (0% - 100%)
        duty_cycle = (voltage / 3.3) * 100.0
        duty_cycle = max(0.0, min(100.0, duty_cycle))
        
        with state_lock:
            state["pwm15_duty"] = duty_cycle
            
        # Tính toán trạng thái logic hiện tại
        t = time.time()
        pos_in_period = t % period
        pulse_width = (duty_cycle / 100.0) * period
        current_state = 1 if pos_in_period < pulse_width else 0
        
        with state_lock:
            state["gpio12_state_15ms"] = current_state
            
        time.sleep(0.002)  # Cập nhật trạng thái hiển thị mỗi 2ms

# ==========================================
# LUỒNG 3: Gaussian Blur ảnh chân dung nhóm
# ==========================================
def thread_3_gaussian_blur():
    add_thread_log("Luồng 3: Đã khởi chạy (Gaussian Blur)")
    last_kernel = -1
    last_mtime = 0
    
    while True:
        with state_lock:
            kernel_size = state["blur_kernel"]
            
        # Đảm bảo kernel size là số lẻ và lớn hơn 0
        kernel_size = max(1, kernel_size)
        if kernel_size % 2 == 0:
            kernel_size += 1
            
        # Tìm file ảnh nguồn (anh.jpg hoặc anh.png)
        input_file = None
        ext = None
        for e in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
            p = os.path.join(BASE_DIR, f"anh.{e}")
            if os.path.exists(p):
                input_file = p
                ext = e
                break
                
        if not input_file:
            with state_lock:
                state["blur_status"] = "Chờ ảnh đầu vào (anh.jpg hoặc anh.png)"
            time.sleep(1)
            continue
            
        try:
            mtime = os.path.getmtime(input_file)
            # Chỉ chạy lại nếu kernel thay đổi hoặc file ảnh thay đổi
            if kernel_size != last_kernel or mtime != last_mtime:
                add_thread_log(f"Luồng 3: Phát hiện thay đổi. Đang áp dụng Gaussian Blur (kernel={kernel_size})...")
                with state_lock:
                    state["blur_status"] = "Đang xử lý..."
                
                # Đọc ảnh sử dụng OpenCV
                img = cv2.imread(input_file)
                if img is None:
                    raise Exception("Không thể đọc định dạng ảnh")
                    
                # Áp dụng Gaussian Blur
                blurred_img = cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)
                
                # Lưu ảnh kết quả (cau5.*)
                output_file = os.path.join(BASE_DIR, f"cau5.{ext}")
                cv2.imwrite(output_file, blurred_img)
                
                last_kernel = kernel_size
                last_mtime = mtime
                
                add_thread_log(f"Luồng 3: Đã lưu kết quả làm mờ vào {output_file}")
                with state_lock:
                    state["blur_status"] = "Hoàn thành thành công"
        except Exception as e:
            add_thread_log(f"Luồng 3: Lỗi xử lý ảnh: {e}")
            with state_lock:
                state["blur_status"] = f"Lỗi: {e}"
                
        time.sleep(1)

# ==========================================
# LUỒNG 4: Phát xung PWM 40ms (GPIO_12) + Flask File Reader
# ==========================================
def thread_4_pwm_40ms():
    add_thread_log("Luồng 4: Đã khởi chạy (PWM 40ms trên GPIO_12 - Đọc cau6.txt)")
    # Chu kỳ 40ms = 0.040s
    period = 0.040
    cau6_path = os.path.join(BASE_DIR, "cau6.txt")
    
    while True:
        # Đọc độ rộng xung từ file cau6.txt
        duty_cycle = 50.0
        if os.path.exists(cau6_path):
            try:
                with open(cau6_path, "r") as f:
                    content = f.read().strip()
                    if content:
                        duty_cycle = float(content)
                        # Giới hạn từ 1 đến 100%
                        duty_cycle = max(1.0, min(100.0, duty_cycle))
            except Exception as e:
                # Đọc lỗi thì giữ nguyên giá trị trước đó hoặc mặc định
                pass
                
        with state_lock:
            state["pwm40_duty"] = duty_cycle
            
        # Tính toán trạng thái logic hiện tại
        t = time.time()
        pos_in_period = t % period
        pulse_width = (duty_cycle / 100.0) * period
        current_state = 1 if pos_in_period < pulse_width else 0
        
        with state_lock:
            state["gpio12_state_40ms"] = current_state
            
        time.sleep(0.002)  # Cập nhật trạng thái hiển thị mỗi 2ms

# ==========================================
# LUỒNG GIAO TIẾP TCP SOCKET: SERVER & CLIENT
# ==========================================
def socket_server_thread():
    add_socket_log("Khởi động Socket Server trên cổng 65432...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Cho phép tái sử dụng địa chỉ port ngay lập tức khi restart
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(("127.0.0.1", 65432))
        server_socket.listen(5)
        add_socket_log("Socket Server đang lắng nghe tại 127.0.0.1:65432")
    except Exception as e:
        add_socket_log(f"Lỗi khởi động Socket Server: {e}")
        return

    while True:
        try:
            conn, addr = server_socket.accept()
            add_socket_log(f"Kết nối mới từ Client: {addr[0]}:{addr[1]}")
            
            # Xử lý kết nối trong một luồng riêng để không chặn server
            t = threading.Thread(target=handle_socket_client, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            add_socket_log(f"Lỗi chấp nhận kết nối: {e}")
            break

def handle_socket_client(conn, addr):
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            command = data.decode("utf-8").strip()
            response = "ERR: Unknown command"
            
            if command == "GET_POT":
                with state_lock:
                    response = f"POT_VOLTAGE:{state['pot_voltage']:.2f}V"
            elif command == "GET_PWM40":
                with state_lock:
                    response = f"PWM40_DUTY:{state['pwm40_duty']:.1f}%"
            elif command.startswith("SET_PWM40:"):
                try:
                    val = float(command.split(":")[1])
                    val = max(1.0, min(100.0, val))
                    # Lưu vào file cau6.txt để giả lập ghi nhận thông tin
                    cau6_path = os.path.join(BASE_DIR, "cau6.txt")
                    with open(cau6_path, "w") as f:
                        f.write(f"{val:.1f}")
                    response = f"OK: Set PWM40 to {val:.1f}%"
                    add_socket_log(f"Cập nhật PWM40 qua Socket: {val:.1f}%")
                except Exception as ex:
                    response = f"ERR: {ex}"
            elif command == "GET_GPIO":
                with state_lock:
                    response = f"GPIO25:{state['gpio25_state']}, GPIO12_15ms:{state['gpio12_state_15ms']}, GPIO12_40ms:{state['gpio12_state_40ms']}"
            
            conn.sendall(response.encode("utf-8"))
    except Exception as e:
        add_socket_log(f"Lỗi trao đổi với Client {addr}: {e}")
    finally:
        conn.close()
        add_socket_log(f"Đóng kết nối với Client: {addr[0]}:{addr[1]}")

def socket_client_thread():
    time.sleep(2)  # Đợi server khởi động xong
    add_socket_log("Khởi động Socket Client định kỳ...")
    
    commands = ["GET_POT", "GET_GPIO", "GET_PWM40"]
    cmd_idx = 0
    
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(("127.0.0.1", 65432))
            
            # Luân phiên gửi các lệnh để kiểm tra
            cmd = commands[cmd_idx]
            client_socket.sendall(cmd.encode("utf-8"))
            data = client_socket.recv(1024)
            
            add_socket_log(f"Gửi: '{cmd}' -> Nhận: '{data.decode('utf-8')}'")
            client_socket.close()
            
            # Chuyển sang lệnh tiếp theo
            cmd_idx = (cmd_idx + 1) % len(commands)
        except Exception as e:
            add_socket_log(f"Client kết nối Server thất bại: {e}")
            
        time.sleep(3)  # Định kỳ 3 giây truy vấn 1 lần

# ==========================================
# CÁC ROUTE API FLASK CHO WEB DASHBOARD
# ==========================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    # Phản hồi trạng thái hiện tại dưới dạng JSON
    with state_lock:
        return jsonify({
            "pot_voltage": state["pot_voltage"],
            "pwm15_duty": state["pwm15_duty"],
            "pwm40_duty": state["pwm40_duty"],
            "blur_kernel": state["blur_kernel"],
            "blur_status": state["blur_status"],
            "gpio25_state": state["gpio25_state"],
            "gpio12_state_15ms": state["gpio12_state_15ms"],
            "gpio12_state_40ms": state["gpio12_state_40ms"],
            "socket_logs": list(state["socket_logs"]),
            "thread_logs": list(state["thread_logs"]),
            "base_dir": BASE_DIR
        })

@app.route("/api/set_pot", methods=["POST"])
def api_set_pot():
    data = request.json
    val = float(data.get("voltage", 1.65))
    val = max(0.0, min(3.3, val))
    with state_lock:
        state["pot_voltage"] = val
    return jsonify({"status": "success", "voltage": val})

@app.route("/api/set_pwm40", methods=["POST"])
def api_set_pwm40():
    data = request.json
    val = float(data.get("duty_cycle", 50.0))
    val = max(1.0, min(100.0, val))
    
    # Ghi vào file cau6.txt (Đáp ứng yêu cầu ghi file)
    cau6_path = os.path.join(BASE_DIR, "cau6.txt")
    try:
        with open(cau6_path, "w") as f:
            f.write(f"{val:.1f}")
        add_thread_log(f"Web UI: Đã ghi {val:.1f}% vào file {cau6_path}")
        return jsonify({"status": "success", "duty_cycle": val})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/set_blur", methods=["POST"])
def api_set_blur():
    data = request.json
    val = int(data.get("kernel", 15))
    val = max(1, min(99, val))
    # Phải là số lẻ
    if val % 2 == 0:
        val += 1
    with state_lock:
        state["blur_kernel"] = val
    return jsonify({"status": "success", "kernel": val})

# --- Các route phục vụ hiển thị ảnh gốc và ảnh mờ ---
@app.route("/image/original")
def serve_original():
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        p = os.path.join(BASE_DIR, f"anh.{ext}")
        if os.path.exists(p):
            return send_from_directory(BASE_DIR, f"anh.{ext}")
    return "Không tìm thấy ảnh gốc", 404

@app.route("/image/blurred")
def serve_blurred():
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        p = os.path.join(BASE_DIR, f"cau5.{ext}")
        if os.path.exists(p):
            # Thêm timestamp vào query string ở Client để tránh browser cache ảnh cũ
            return send_from_directory(BASE_DIR, f"cau5.{ext}")
    return "Không tìm thấy ảnh đã xử lý", 404

# --- Đảm bảo không cache ảnh trên web ---
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# ==========================================
# KHỞI CHẠY HỆ THỐNG
# ==========================================
if __name__ == "__main__":
    init_files()
    
    # Khởi chạy 4 luồng nghiệp vụ mô phỏng
    t1 = threading.Thread(target=thread_1_square_wave, daemon=True)
    t2 = threading.Thread(target=thread_2_pwm_15ms, daemon=True)
    t3 = threading.Thread(target=thread_3_gaussian_blur, daemon=True)
    t4 = threading.Thread(target=thread_4_pwm_40ms, daemon=True)
    
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    
    # Khởi chạy các luồng Socket Client & Server
    t_server = threading.Thread(target=socket_server_thread, daemon=True)
    t_client = threading.Thread(target=socket_client_thread, daemon=True)
    
    t_server.start()
    t_client.start()
    
    # Chạy Flask Server
    add_thread_log("Khởi động Flask Web Server trên cổng 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
