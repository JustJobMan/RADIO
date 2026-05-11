import asyncio
import websockets
import json
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

TOON_WS_URL = "wss://ws.toon.at/eyJhdXRoIjoiM2Q3MTMzNDA0OGFhNmQ5MTM3YjAyMDIyN2Y3ZmFkNzgiLCJzZXJ2aWNlIjoiYWxlcnQiLCJ0eXBlIjowLCJsYW5ndWFnZSI6ImtvIn0"

async def connect_toonation():
    while True:
        try:
            async with websockets.connect(TOON_WS_URL) as ws:
                print("투네이션 연결 성공!")
                while True:
                    data = await ws.recv()
                    parsed = json.loads(data)
                    print("후원 데이터:", parsed)
                    socketio.emit('donation', parsed)
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
