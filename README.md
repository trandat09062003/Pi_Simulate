# Mô Phỏng Hệ Thống Đa Luồng - Raspberry Pi 4B & Beaglebone Black

Đây là source code bài tập thực hành môn Hệ nhúng. Project này mô phỏng lại 4 luồng xử lý tín hiệu và điều khiển trên Linux, giúp test code và logic dễ dàng hơn trên máy tính cá nhân mà không cần chạy trực tiếp trên kit phần cứng (Raspberry Pi/Beaglebone).

## Cấu trúc project

- `app.py`: File code chính. Trong này chứa 4 luồng thực thi yêu cầu của đề bài, xử lý Socket Client/Server và chạy Flask server để hiển thị kết quả.
- `templates/index.html`: Giao diện web dashboard để điều khiển các thông số (kéo thanh trượt) và xem máy hiện sóng (oscilloscope) của các chân GPIO.
- `NguyenVanQuan/`: Thư mục để chứa file ảnh test (mô phỏng đường dẫn `/home/debian/NguyenVanQuan/` trên kit thật).
- `run_simulation.sh`: File script để khởi chạy nhanh project.

## Chi tiết 4 luồng nghiệp vụ

1. **Luồng 1 (GPIO 25 - Xung vuông 13kHz)**: 
   - Mô phỏng phát xung vuông ở tần số 13kHz tại chân GPIO_25.
   - Trạng thái được tính toán và cập nhật liên tục để vẽ lên biểu đồ sóng.

2. **Luồng 2 (GPIO 12 - PWM 15ms + ADS1115)**: 
   - Mô phỏng đọc điện áp từ biến trở qua module ADS1115.
   - Từ mức điện áp (0V - 3.3V) sẽ đổi ra duty cycle để phát PWM chu kỳ 15ms tại chân GPIO_12. Có thể chỉnh điện áp giả lập này trực tiếp trên giao diện web.

3. **Luồng 3 (Xử lý ảnh Gaussian Blur)**: 
   - Tự động quét lấy ảnh trong file `anh.*` (nằm ở `/home/debian/NguyenVanQuan/` hoặc thư mục local), áp dụng bộ lọc Gaussian Blur bằng OpenCV và lưu kết quả ra `cau5.*`.
   - Có thể chỉnh độ mờ (Kernel size) trên dashboard.

4. **Luồng 4 (GPIO 12 - PWM 40ms + Flask)**: 
   - Có chỗ trên giao diện web cho phép nhập độ rộng xung (1-100%) và lưu vào file `cau6.txt`.
   - Luồng này sẽ liên tục đọc thông số từ `cau6.txt` để thay đổi độ rộng của PWM (chu kỳ 40ms).

## Giao tiếp Socket Client - Server (Slide 112)
- Có một TCP Server chạy ở port `65432` để trả về các thông số hiện tại của hệ thống.
- Một TCP Client cứ mỗi 3 giây sẽ kết nối và gửi data qua lại để test. Các log giao tiếp này sẽ được in trực tiếp lên tab terminal trên giao diện web.

## Cách chạy thử

Chỉ cần cài sẵn Python 3 trên máy (dùng Ubuntu/Linux hoặc WSL).

```bash
# Cài đặt các thư viện cần thiết nếu chưa có
pip3 install flask opencv-python numpy pillow

# Cấp quyền và chạy script
chmod +x run_simulation.sh
./run_simulation.sh
```

Sau khi terminal báo chạy thành công, mở trình duyệt lên và vào link: `http://localhost:5000` để sử dụng dashboard mô phỏng.
