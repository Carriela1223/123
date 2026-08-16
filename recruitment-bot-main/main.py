from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

class KeepAliveHandler(BaseHTTPRequestHandler):
    def handle_all_requests(self):
        """UptimeRobot이 어떤 방식(GET, HEAD 등)으로 신호를 보내든 전부 200 OK로 무조건 통과시킵니다."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write("Bot is alive!".encode('utf-8'))

    def do_GET(self):
        self.handle_all_requests()

    def do_HEAD(self):
        self.handle_all_requests()

    def do_POST(self):
        self.handle_all_requests()

    def log_message(self, format, *args):
        return  # 서버 로그 생략

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), KeepAliveHandler)
    server.serve_forever()

# 백그라운드 스레드로 간이 웹 서버 기동
threading.Thread(target=run_server, daemon=True).start()

# ---- 이 아래부터 기존 유저님의 discord 봇 구동 코드를 그대로 두시면 됩니다 ----
import discord
import os
from dotenv import load_dotenv
from discord.ext import interaction
from config.log_config import log

load_dotenv()

if __name__ == "__main__":
    directory = os.path.dirname(os.path.abspath(__file__))
    log.info("구인구직 봇을 불러오는 중입니다.")

    intent = discord.Intents().all()
    
    client = interaction.Client(
        intents=intent,
        global_sync_command=True,
        guild_ids=[1530880128769593384],
        sync_commands_on_cog_unload=True,
        enable_debug_events=True
    )
    client.load_extensions("cogs", directory=directory)
    
    client.run(os.getenv("DISCORD_TOKEN"))
