import asyncio
import websockets
import json
import requests
from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

TOON_WS_URL = "wss://ws.toon.at/eyJhdXRoIjoiM2Q3MTMzNDA0OGFhNmQ5MTM3YjAyMDIyN2Y3ZmFkNzgiLCJzZXJ2aWNlIjoiYWxlcnQiLCJ0eXBlIjowLCJsYW5ndWFnZSI6ImtvIn0"
FIREBASE_URL = "https://notan-cb053-default-rtdb.firebaseio.com"

def get_funding():
    res = requests.get(f"{FIREBASE_URL}/funding.json")
    return res.json() or {"currentAmount": 0, "targetAmount": 50000, "name": "펀딩"}

def update_funding(amount, name, message):
    data = get_funding()
    data["currentAmount"] = (data.get("currentAmount") or 0) + amount
    while data["currentAmount"] >= data.get("targetAmount", 50000):
        data["targetAmount"] = (data.get("targetAmount") or 50000) + 50000
    requests.patch(f"{FIREBASE_URL}/funding.json", json=data)

    # 후원 내역 저장
    donation_data = {
        "name": name,
        "amount": amount,
        "message": message,
        "time": int(time.time() * 1000)
    }
    requests.post(f"{FIREBASE_URL}/donations.json", json=donation_data)
    print(f"Firebase 업데이트: {name}님 {amount}원 후원")

def run_toonation():
    async def connect():
        while True:
            try:
                print("투네이션 연결 시도 중...")
                async with websockets.connect(TOON_WS_URL) as ws:
                    print("투네이션 연결 성공!")
                    while True:
                        data = await ws.recv()
                        parsed = json.loads(data)
                        if parsed.get("code") == 101:
                            content = parsed.get("content", {})
                            amount = content.get("amount", 0)
                            name = content.get("name", "익명")
                            message = content.get("message", "")
                            print(f"후원 감지: {name}님 {amount}원 - {message}")
                            update_funding(amount, name, message)
                            socketio.emit('donation', {
                                "amount": amount,
                                "name": name,
                                "message": message
                            })
            except Exception as e:
                print(f"에러: {type(e).__name__}: {e}")
                await asyncio.sleep(5)

    asyncio.run(connect())

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():
    print("클라이언트 연결됨!")

if __name__ == '__main__':
    t = threading.Thread(target=run_toonation, daemon=True)
    t.start()
    print("스레드 시작됨!")
    socketio.run(app, host='0.0.0.0', port=10000, use_reloader=False, allow_unsafe_werkzeug=True)
