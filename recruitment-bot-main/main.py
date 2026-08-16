from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write("Bot is alive!".encode('utf-8'))
    def log_message(self, format, *args):
        return

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), KeepAliveHandler)
    server.serve_forever()

# 백그라운드 스레드로 간이 웹 서버 기동
threading.Thread(target=run_server, daemon=True).start()

import discord
import os
from dotenv import load_dotenv
from discord.ext import interaction
from config.log_config import log

# .env 파일에 적어둔 디스코드 토큰값을 컴퓨터 메모리에 로드합니다.
load_dotenv()

if __name__ == "__main__":
    directory = os.path.dirname(os.path.abspath(__file__))
    log.info("구인구직 봇을 불러오는 중입니다.")

    intent = discord.Intents().all()
    
    # 💡 guild_ids 대괄호 안에 알려주신 서버 ID 숫자를 정상 주입했습니다.
    client = interaction.Client(
        intents=intent,
        global_sync_command=True,
        guild_ids=[1530880128769593384],
        sync_commands_on_cog_unload=True,
        enable_debug_events=True
    )
    client.load_extensions("cogs", directory=directory)
    
    client.run(os.getenv("DISCORD_TOKEN"))
