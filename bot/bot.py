import os
import serial
import time
import discord
import logging
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ログを出力するように設定（エラー時に何が起きたか見やすくするため）
logging.basicConfig(level=logging.INFO)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 9600
THRESHOLD = 18.0
NOTIFICATION_COOLDOWN = 12 * 60 * 60  # 12時間

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# シリアルのタイムアウトを短く設定
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

last_sent_time = 0
# 最初から「開いている」判定にならないよう、起動時は一旦False（不明）から始める
was_below_threshold = False 

@bot.event
async def on_ready():
    print(f"--- Logged in as {bot.user} ---")
    if not serial_task.is_running():
        serial_task.start()

@tasks.loop(seconds=0.5) # Arduino(1.0)に合わせる
async def serial_task():
    global last_sent_time, was_below_threshold

    # --- 最強ポイント1: バッファの読み飛ばし ---
    # 溜まっているデータを全て読み切り、最新の1行だけを取得する（ラグ解消）
    latest_data = None
    while ser.in_waiting > 0:
        latest_data = ser.readline()
    
    if not latest_data:
        return

    try:
        text = latest_data.decode("utf-8", errors="ignore").strip()
        # "Out of range"などは無視
        distance = float(text)
    except ValueError:
        return

    now = int(time.time())

    # distance > THRESHOLD でかつ「前回は閉まっていた」場合に通知
    if distance > THRESHOLD:
        if was_below_threshold:
            # 12時間経過チェック
            if (now - last_sent_time) >= NOTIFICATION_COOLDOWN:
                # fetch_channel を使うことで、キャッシュがなくても取得しにいく
                try:
                    channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
                    if channel:
                        await channel.send(f"部室空きました: 現在の距離 **{distance:.1f} cm**")
                        last_sent_time = now
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Notification sent!")
                except Exception as e:
                    print(f"Failed to send message: {e}")
        
        # 通知したかに関わらず、しきい値を超えている間は False
        was_below_threshold = False
    else:
        # 17cm以下のデータが来たら、次に「開いた」と言える準備ができる
        was_below_threshold = True

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! (Distance logic is {'Ready' if was_below_threshold else 'Monitoring'})")

# シリアルポートが閉じていたら開く処理を追加（エラー対策）
@serial_task.before_loop
async def before_serial():
    await bot.wait_until_ready()
    if not ser.is_open:
        ser.open()

bot.run(TOKEN)
