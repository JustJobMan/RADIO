import asyncio
import websockets
import json
import threading
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

TOON_WS_URL = "wss://ws.toon.at/eyJhdXRoIjoiM2Q3MTMzNDA0OGFhNmQ5MTM3YjAyMDIyN2Y3ZmFkNzgiLCJzZXJ2aWNlIjoiYWxlcnQiLCJ0eXBlIjowLCJsYW5ndWFnZSI6ImtvIn0"

# Firebase Admin 초기화
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://notan-cb053-default-rtdb.firebaseio.com'
})

def update_funding(amount, name):
    funding_ref = db.reference("funding")
    
    def transaction_fn(current_data):
        if current_data is None:
            current_data = {"currentAmount": 0, "targetAmount": 50000, "name": "펀딩"}
        
        current_data["currentAmount"] = (current_data.get("currentAmount") or 0) + amount
        
        # 목표 달성시 자동으로 +5만원
        while current_data["currentAmount"] >= current_data.get("targetAmount", 50000):
            current_data["targetAmount"] = (current_data.get("targetAmount") or 50000) + 50000
        
        return current_data
    
    funding_ref.transaction(transaction_fn)
    print(f"Firebase 업데이트: {name}님 {amount}원 후원")

async def connect_toonation():
    while True:
        try:
            async with websockets.connect(TOON_WS_URL) as ws:
                print("투네이션 연결 성공!")
                while True:
                    data = await ws.recv()
                    parsed = json.loads(data)
                    
                    # code 101 = 후원 이벤트
                    if parsed.get("code") == 101:
                        content = parsed.get("content", {})
                        amount = content.get("amount", 0)
                        name = content.get("name", "익명")
                        message = content.get("message", "")
                        
                        print(f"후원 감지: {name}님 {amount}원 - {message}")
                        
                        # Firebase 업데이트
                        update_funding(amount, name)
                        
                        # 시청자 페이지에 실시간 알림
                        socketio.emit('donation', {
                            "amount": amount,
                            "name": name,
                            "message": message
                        })
                        
        except Exception as e:
            print(f"연결 끊김: {e}, 5초 후 재연결...")
            await asyncio.sleep(5)

def start_toonation():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connect_toonation())

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    t = threading.Thread(target=start_toonation)
    t.daemon = True
    t.start()
    socketio.run(app, host='0.0.0.0', port=10000)
