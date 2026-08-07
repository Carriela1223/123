# keep_alive.py
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write("Bot is running!".encode('utf-8'))

    def log_message(self, format, *args):
        return  # 불필요한 서버 로그 생략

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), KeepAliveHandler)
    server.serve_forever()

def keep_alive():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
