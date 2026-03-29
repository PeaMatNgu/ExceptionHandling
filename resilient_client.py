import time
import json
import os
import inspect
import functools
import requests
from datetime import datetime

# Cấu hình mạng
SERVER_IP = "192.168.72.139"  # Địa chỉ IP của máy VM1
LOG_FILE = "forensic_report.json"

# --- CẢI TIẾN 1: GHI NHẬT KÝ NGỮ CẢNH LỖI (Forensic Logger) ---
def forensic_logger(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Chụp lại "hiện trường" thực thi tại thời điểm xảy ra lỗi
            stack = inspect.trace()
            last_frame = stack[-1][0] if stack else None
            local_vars = last_frame.f_locals if last_frame else {}
            
            error_entry = {
                "timestamp": datetime.now().isoformat(),
                "function": func.__name__,
                "exception_type": type(e).__name__,
                "error_message": str(e),
                # Lưu các biến cục bộ để phân tích nguyên nhân gốc rễ
                "context_snapshot": {k: str(v) for k, v in local_vars.items() if k != 'wrapper'}
            }
            
            # Lưu trữ bền vững vào file JSON
            reports = []
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    try: reports = json.load(f)
                    except: reports = []
            
            reports.append(error_entry)
            with open(LOG_FILE, "w") as f:
                json.dump(reports, f, indent=4)
            
            print(f"--> [PHÂN TÍCH] Đã ghi lại ngữ cảnh lỗi vào {LOG_FILE}")
            raise e
    return wrapper

# --- CẢI TIẾN 2: MÔ HÌNH BỘ NGẮT MẠCH (Circuit Breaker) ---
class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=10):
        self.failure_threshold = failure_threshold # Ngưỡng lỗi để ngắt mạch
        self.recovery_timeout = recovery_timeout   # Thời gian chờ để thử lại
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED" # Các trạng thái: CLOSED (Đóng), OPEN (Mở/Ngắt), HALF_OPEN (Thử nghiệm)

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Kiểm tra nếu mạch đang NGẮT, xem đã đến lúc thử lại chưa
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    print("\n[HỆ THỐNG] Đang thử khôi phục (Trạng thái HALF_OPEN)...")
                    self.state = "HALF_OPEN"
                else:
                    # Chặn yêu cầu ngay lập tức để bảo vệ tài nguyên
                    raise Exception("MẠCH_ĐANG_NGẮT: Yêu cầu bị chặn để tránh gây sập hệ thống dây chuyền.")

            try:
                result = func(*args, **kwargs)
                # Nếu gọi thành công trong trạng thái HALF_OPEN -> Đóng mạch trở lại
                if self.state == "HALF_OPEN":
                    print("[HỆ THỐNG] Dịch vụ đã hồi phục. Reset về trạng thái CLOSED.")
                    self.state = "CLOSED"
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                # Nếu số lần lỗi vượt ngưỡng -> Chuyển sang trạng thái OPEN (Ngắt mạch)
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    print(f"\n[CẢNH BÁO] Ngưỡng lỗi đã đạt ({self.failure_count}). NGẮT MẠCH NGAY LẬP TỨC!")
                raise e
        return wrapper

# --- THỰC THI THỰC NGHIỆM ---
cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10)

@cb
@forensic_logger
def request_secure_resource(attempt_id):
    target_url = f"http://{SERVER_IP}:5000/api/data"
    
    # Các biến nội bộ sẽ được forensic_logger "chụp" lại nếu có crash
    session_token = f"AUTH_ID_{attempt_id * 1234}"
    priority_level = "HIGH"
    
    response = requests.get(target_url, timeout=2)
    response.raise_for_status() # Tự động ném Exception nếu nhận mã lỗi 4xx hoặc 5xx
    return response.json()

if __name__ == '__main__':
    print("--- BẮT ĐẦU THỰC NGHIỆM ĐỘ BỀN HỆ THỐNG ---")
    for i in range(1, 15):
        print(f"\n[Yêu cầu #{i}]", end=" ")
        try:
            data = request_secure_resource(i)
            print(f"Thành công: {data['payload']}")
        except Exception as err:
            print(f"Trạng thái: {err}")
        time.sleep(1) # Đợi 1 giây giữa các lần gọi để dễ quan sát
