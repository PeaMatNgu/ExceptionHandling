from flask import Flask, jsonify

app = Flask(__name__)
call_count = 0

@app.route('/api/data')
def get_resource():
    global call_count
    call_count += 1
    
    # Giả lập mô hình lỗi chu kỳ: 3 lần THÀNH CÔNG -> 3 lần THẤT BẠI
    # Logic: chu kỳ 0 (lần 1,2,3) -> OK | chu kỳ 1 (lần 4,5,6) -> LỖI
    cycle_index = (call_count - 1) // 3
    if cycle_index % 2 == 1:
        return jsonify({
            "status": "error", 
            "message": "Internal Server Error", 
            "code": 500
        }), 500
    
    return jsonify({
        "status": "success",
        "payload": "Secure_Data_Block_X99",
        "request_id": call_count
    }), 200

if __name__ == '__main__':
    # host='0.0.0.0' cho phép các máy ảo khác (như VM2) kết nối vào
    app.run(host='0.0.0.0', port=5000)
