#!/bin/bash

# Script to run the Raspberry Pi / Beaglebone Black Multi-thread Simulation

# Navigate to project directory
CDPATH= cd "$(dirname "$0")"

echo "=========================================================="
echo "   Raspberry Pi / Beaglebone Black Thread Simulator       "
echo "=========================================================="
echo ""
echo "[*] Cấu hình môi trường..."
echo "    - Thư mục lưu trữ: /home/debian/NguyenVanQuan"
echo "    - Cổng Socket Server: 65432"
echo "    - Cổng Flask Web Server: 5000"
echo ""

# Check dependencies
echo "[*] Kiểm tra các thư viện Python..."
python3 -c "import flask, cv2, numpy, PIL" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[!] Một số thư viện bị thiếu. Đang tiến hành cài đặt..."
    pip3 install flask opencv-python numpy pillow
else
    echo "[+] Tất cả các thư viện cần thiết đã sẵn sàng."
fi

echo ""
echo "[*] Khởi chạy ứng dụng mô phỏng..."
echo "[*] Truy cập giao diện Web Dashboard tại: http://localhost:5000"
echo "[*] Nhấn Ctrl+C để dừng mô phỏng."
echo "----------------------------------------------------------"

# Run Flask application
python3 app.py
