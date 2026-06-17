# 🍓 Raspberry Pi & Beaglebone Black Multi-Thread Simulator

Hệ thống mô phỏng đa luồng (Multi-threading) và lập trình Client-Server Socket trên Linux, đi kèm giao diện điều khiển Web Dashboard cao cấp phong cách Glassmorphism Dark Mode.

Dự án này được thiết kế nhằm đáp ứng và kiểm thử chính xác các yêu cầu bài tập nhúng thực hành của sinh viên trên môi trường Raspberry Pi 4B hoặc Beaglebone Black.

---

## 🛠️ Cấu Trúc Dự Án

- `app.py`: Code Python chính quản lý 4 luồng nghiệp vụ, luồng Socket Server/Client và Flask Web Server.
- `templates/index.html`: Giao diện Web Dashboard trực quan, tích hợp máy hiện sóng (Oscilloscope) thời gian thực và các bảng điều khiển.
- `HoVaTenSV/`: Thư mục mô phỏng cục bộ trong trường hợp chạy trên máy cá nhân không có thư mục gốc `/home/debian`.
- `/home/debian/HoVaTenSV/`: Thư mục chính dùng trên kit thực tế (đã được tạo và cấu hình quyền ghi trên hệ thống Linux này).
- `run_simulation.sh`: Shell script để khởi chạy nhanh chương trình.

---

## ⚙️ Chi Tiết Hoạt Động của 4 Luồng & Socket

### 1. Luồng 1 (GPIO 25 - Xung vuông 13kHz)
- **Yêu cầu**: Phát xung vuông tần số 13kHz tại chân GPIO_25 của Raspberry Pi 4B.
- **Mô phỏng**: Phân tích logic và tính toán trạng thái tắt/bật chính xác theo trục thời gian thực. Được hiển thị trực quan dưới dạng sóng màu vàng (CH1) trên Oscilloscope trên giao diện Web.

### 2. Luồng 2 (GPIO 12 - PWM 15ms + ADS1115)
- **Yêu cầu**: Phát xung PWM chu kỳ 15ms tại chân GPIO_12. Độ rộng xung được điều khiển bằng điện áp đọc từ biến trở kết nối với ADS1115.
- **Mô phỏng**: Cung cấp slider giả lập điện áp biến trở (0V - 3.3V) trên Web Dashboard. Hệ thống tự động ánh xạ mức điện áp sang độ rộng xung tương ứng (0% - 100%). Sóng hiển thị màu xanh lam (CH2).

### 3. Luồng 3 (Gaussian Blur Xử lý ảnh)
- **Yêu cầu**: Làm mờ Gaussian ảnh chân dung nhóm tại `/home/debian/HoVaTenSV/anh.*` và lưu kết quả vào `/home/debian/HoVaTenSV/cau5.*`.
- **Mô phỏng**: Tự động giám sát ảnh chân dung nhóm có sẵn. Sử dụng thư viện `OpenCV` để thực hiện thuật toán làm mờ theo bán kính lọc (Kernel Size) điều chỉnh động từ giao diện Web. Ảnh gốc và ảnh sau khi mờ được hiển thị song song.

### 4. Luồng 4 (GPIO 12 - PWM 40ms + Flask UI)
- **Yêu cầu**: Sử dụng Flask để nhập độ rộng xung (1% - 100%), lưu vào `/home/debian/HoVaTenSV/cau6.txt`. Luồng 4 đọc file này để phát xung PWM chu kỳ 40ms tại chân GPIO_12.
- **Mô phỏng**: Người dùng nhập số hoặc kéo slider trên Web Dashboard, click "Ghi nhận cau6.txt" để ghi vào file. Luồng 4 tự động đọc file này để cập nhật độ rộng xung. Sóng hiển thị màu hồng (CH3).

### 🌐 Lập Trình Client - Server (Slide 112 Phần 7.1)
- **Socket Server (Port 65432)**: Nhận lệnh từ Client và gửi phản hồi trạng thái điện áp, duty cycle hoặc mức logic các chân GPIO.
- **Socket Client**: Định kỳ kết nối đến Server sau mỗi 3 giây, gửi các truy vấn và nhận dữ liệu. Toàn bộ log giao tiếp được cập nhật trực tiếp trên console của Web Dashboard.

---

## 🚀 Hướng Dẫn Chạy Mô Phỏng

1. Mở Terminal và di chuyển vào thư mục dự án:
   ```bash
   cd /home/dat/Desktop/Pi_Simulation
   ```

2. Khởi chạy thông qua shell script:
   ```bash
   ./run_simulation.sh
   ```

3. Truy cập vào trình duyệt web theo địa chỉ:
   [http://localhost:5000](http://localhost:5000)
