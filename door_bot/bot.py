import os
import serial
import time
import datetime
import discord
import logging
import random
import requests
import subprocess
import asyncio
import json
from discord.ext import commands, tasks
from dotenv import load_dotenv

# --- ログ設定 ---
logging.basicConfig(level=logging.INFO)

# --- 環境変数読み込み ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

try:
    # 互換性のため CHANNEL_ID にも対応しつつ、複数指定可能な CHANNEL_IDS を優先
    channel_ids_str = os.getenv("CHANNEL_IDS", os.getenv("CHANNEL_ID", ""))
    CHANNEL_IDS = [int(cid.strip()) for cid in channel_ids_str.split(",") if cid.strip()]
    if not CHANNEL_IDS:
        print("警告: .env に CHANNEL_IDS (または CHANNEL_ID) が設定されていません。")
except ValueError:
    print("エラー: .env の CHANNEL_IDS の形式が不正です。カンマ区切りの数字を指定してください。")
    CHANNEL_IDS = []

# --- シリアルポート設定 ---
SERIAL_PORT = "/dev/doorduino"
BAUD_RATE = 9600
THRESHOLD = 18.0  # これ以上離れたら「ドアが開いた」と判定

# --- キャラクター・声色・セリフの完全連動設定 ---
SPEECH_PATTERNS = [
    # ==========================
    # 1. ずんだもん (語尾: ～のだ)
    # ==========================
    {
        "name": "ずんだもん",
        "patterns": [
            # ノーマル(3): 普通
            {"id": 3, "text": "部室が開いたのだ。ようこそなのだ。"},
            {"id": 3, "text": "侵入者を検知したのだ。"},
            # あまあま(1): 甘える
            {"id": 1, "text": "おかえりなさいなのだ。待ってたのだ。"},
            {"id": 1, "text": "もっと部室に来てほしいのだ。"},
            # ツンツン(7): ツンデレ
            {"id": 7, "text": "べ、別にあんたを待ってたわけじゃないのだ！"},
            {"id": 7, "text": "やっと来たのだ？ 遅いのだ！"},
            # ささやき(22): こっそり
            {"id": 22, "text": "……誰か入ってきたのだ……（ヒソヒソ）"},
            # ヘロヘロ(75): 疲労
            {"id": 75, "text": "もう疲れたのだ……誰か来たの……？"},
            # なみだめ(76): 怯え
            {"id": 76, "text": "誰も来ないと思って、怖かったのだ……！"}
        ]
    },
    # ==========================
    # 2. 四国めたん (語尾: ～わよ、～ですわ)
    # ==========================
    {
        "name": "四国めたん",
        "patterns": [
            # ノーマル(2): 上品
            {"id": 2, "text": "あら、いらっしゃい。部室が開いたわよ。"},
            {"id": 2, "text": "センサー反応あり。特定完了よ。"},
            # あまあま(0): 甘やかす
            {"id": 0, "text": "うふふ、おかえりなさい。ゆっくりしていってね。"},
            # ツンツン(6): 高飛車
            {"id": 6, "text": "ちょっと、ノックくらいしなさいよ。"},
            {"id": 6, "text": "気安く入ってこないでくれる？ ……嘘よ、入りなさい。"},
            # セクシー(4): 色っぽい
            {"id": 4, "text": "あら……、素敵な来客ね……？"},
            # ささやき(36): 秘密の話
            {"id": 36, "text": "静かに……。誰か来たみたいよ……。"}
        ]
    },
    # ==========================
    # 3. 春日部つむぎ (語尾: ～だよ、～だね)
    # ==========================
    {
        "name": "春日部つむぎ",
        "patterns": [
            # 元気系 (ノーマルID: 8)
            {"id": 8, "text": "やっほー！ 誰か来たみたいだね！"},
            {"id": 8, "text": "埼玉から見てるよ！ いらっしゃーい！"},
            {"id": 8, "text": "お疲れ様ー！ 部室、空いたよ！"},
            # ちょっと生意気系
            {"id": 8, "text": "お、やっと来たの？"},
            {"id": 8, "text": "センサーが反応してるよー、誰かなー？"},
            # まったり系
            {"id": 8, "text": "んー、誰か来たかも。ゆっくりしてきなー。"}
        ]
    }
]

# --- Bot設定 ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- シリアル初期化 ---
try:
    if os.path.exists(SERIAL_PORT):
        print(f"Connecting to: {os.path.realpath(SERIAL_PORT)}")
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
except serial.SerialException as e:
    print(f"シリアル接続エラー: {e}")
    ser = None

# --- グローバル状態 ---
last_sent_date = datetime.date.today()
last_triggered_time = None
was_below_threshold = False 
volume_scale = 1.0  # 音量倍率 (0.0 ~ 1.0)

# --- Voicevox関数 ---
def speak_zunda(text, speaker_id=3, host="127.0.0.1", port=50021):
    """
    指定されたIDとテキストでVoicevoxに喋らせる
    """
    try:
        # 1. 音声クエリの作成
        params = {'text': text, 'speaker': speaker_id}
        query_res = requests.post(
            f"http://{host}:{port}/audio_query", 
            params=params, 
            timeout=3
        )

        if query_res.status_code != 200:
            print(f"Voicevox Query Error: {query_res.status_code}")
            return

        query_data = query_res.json()
        
        # 音量調整の適用
        query_data['volumeScale'] = volume_scale

        # 2. 音声合成
        synthesis_res = requests.post(
            f"http://{host}:{port}/synthesis",
            params={'speaker': speaker_id},
            json=query_data,
            timeout=5
        )

        if synthesis_res.status_code != 200:
            print(f"Voicevox Synthesis Error: {synthesis_res.status_code}")
            return

        # 3. 再生 (paplay使用)
        process = subprocess.Popen(['paplay'], stdin=subprocess.PIPE)
        process.communicate(input=synthesis_res.content)
        
    except Exception as e:
        print(f"読み上げ失敗: {e}")

# --- Botイベント ---
@bot.event
async def on_ready():
    print(f"--- Logged in as {bot.user} ---")
    if not serial_task.is_running():
        serial_task.start()

# --- コマンド一覧 ---

@bot.command()
async def say(ctx, *, text: str):
    """部室のスピーカーで喋ります (ランダムキャラ)"""
    character = random.choice(SPEECH_PATTERNS)
    pattern = random.choice(character["patterns"])
    speak_zunda(text, speaker_id=pattern["id"])

@bot.command()
async def zunda(ctx, *, text: str):
    """ずんだもんの声で喋ります"""
    speak_zunda(text, speaker_id=3)

@bot.command()
async def metan(ctx, *, text: str):
    """四国めたんの声で喋ります"""
    speak_zunda(text, speaker_id=2)

@bot.command()
async def tsumugi(ctx, *, text: str):
    """春日部つむぎの声で喋ります"""
    speak_zunda(text, speaker_id=8)

@bot.command()
async def status(ctx):
    """現在のセンサーとBotの状態を確認します"""
    sensor_status = "準備完了(閉)" if was_below_threshold else "検知中(開)"
    trigger_text = last_triggered_time.strftime('%Y-%m-%d %H:%M:%S') if last_triggered_time else "なし"
    
    msg = (
        "**🚪 部室ドアBot ステータス**\n"
        f"┣ センサー状態: `{sensor_status}`\n"
        f"┣ 現在の音量設定: `{int(volume_scale * 100)}%` (0.0-1.0)\n"
        f"┣ 本日の初通知: `{'完了' if last_sent_date == datetime.date.today() else '未送信'}`\n"
        f"┗ 最終検知時刻: `{trigger_text}`"
    )
    await ctx.send(msg)

@bot.command()
async def volume(ctx, value: float):
    """音量を調整します (0.0 ~ 1.0)"""
    global volume_scale
    if 0.0 <= value <= 1.0:
        volume_scale = value
        await ctx.send(f"🔊 音量を `{int(volume_scale * 100)}%` に設定しました。")
    else:
        await ctx.send("❌ 0.0 から 1.0 の範囲で指定してください。")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")

async def get_connection_info():
    """現在の接続方式（Ethernet/Wi-Fi）を取得します (Docker内部用)"""
    try:
        # デフォルトルートのインターフェースを取得
        cmd = "ip route show default"
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        output = stdout.decode().strip()
        
        if not output:
            return "不明"
            
        # 出力例: default via 192.168.1.1 dev enp0s31f6 proto dhcp src 192.168.1.100 metric 100 
        parts = output.split()
        if "dev" in parts:
            dev_idx = parts.index("dev")
            dev_name = parts[dev_idx + 1]
            
            # インターフェース名から種類を推測
            if dev_name.startswith("wl") or dev_name.startswith("wpan"):
                return f"Wi-Fi ({dev_name})"
            elif dev_name.startswith("en") or dev_name.startswith("eth"):
                return f"Ethernet ({dev_name})"
            else:
                return f"その他 ({dev_name})"
                
        return "不明"
    except Exception as e:
        return f"取得失敗 ({e})"

@bot.command()
async def network(ctx):
    """回線速度と接続経路を計測します"""
    await ctx.send("🌐 ネットワーク状況を確認中です。約30秒ほどお待ちください...")
    
    conn_info = await get_connection_info()
    
    try:
        import speedtest
        
        # 非同期実行のためにスレッドで実行
        loop = asyncio.get_event_loop()
        def run_speedtest():
            s = speedtest.Speedtest()
            s.get_best_server()
            s.download()
            s.upload()
            return s.results.dict()
            
        data = await loop.run_in_executor(None, run_speedtest)
        
        download = data['download'] / 1_000_000  # Mbps
        upload = data['upload'] / 1_000_000      # Mbps
        ping = data['ping']
        server = data['server']['sponsor']
        location = data['server']['name']
        
        msg = (
            "**📶 回線状況レポート**\n"
            f"┣ 接続経路: `{conn_info}`\n"
            f"┣ ダウンロード: `{download:.2f} Mbps`\n"
            f"┣ アップロード: `{upload:.2f} Mbps`\n"
            f"┣ ピング: `{ping:.2f} ms`\n"
            f"┗ 測定サーバー: `{server} ({location})`"
        )
        await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"❌ エラーが発生しました: {e}\n(接続経路: {conn_info})")

@bot.remove_command("help")
@bot.command()
async def help(ctx):
    """ヘルプを表示します"""
    help_text = (
        "**📋 部室ドアBot コマンド一覧**\n\n"
        "📢 **読み上げコマンド**\n"
        "┣ `!say [文章]` : ランダムなキャラが部室で喋ります\n"
        "┣ `!zunda [文章]` : ずんだもんが喋ります\n"
        "┣ `!metan [文章]` : 四国めたんが喋ります\n"
        "┗ `!tsumugi [文章]` : 春日部つむぎが喋ります\n\n"
        "⚙️ **設定・確認**\n"
        "┣ `!status` : ドアの状態や音量設定を表示\n"
        "┣ `!network` : 部室の回線速度を計測\n"
        "┣ `!volume [0.0-1.0]` : 音量を調整します\n"
        "┗ `!ping` : Botの生存確認\n\n"
        "💡 *センサーがドアの開閉を検知すると、自動で挨拶します。*"
    )
    await ctx.send(help_text)

# --- メインループ ---
@tasks.loop(seconds=0.5)
async def serial_task():
    global last_sent_date, was_below_threshold, last_triggered_time

    if ser is None or not ser.is_open:
        return

    # バッファの読み飛ばし（ラグ解消）
    latest_data = None
    try:
        while ser.in_waiting > 0:
            latest_data = ser.readline()
    except OSError:
        return
    
    if not latest_data:
        return

    try:
        text = latest_data.decode("utf-8", errors="ignore").strip()
        distance = float(text)
    except ValueError:
        return

    today_date = datetime.date.today()

    # --- 判定ロジック ---
    if distance > THRESHOLD:
        # 前回は閉じていて、今回開いた（立ち上がりエッジ）
        if was_below_threshold:
            print("--- Sensor Triggered ---")
            last_triggered_time = datetime.datetime.now()

            # 1. キャラクターをランダム選出
            character = random.choice(SPEECH_PATTERNS)
            # 2. パターン（IDとセリフ）をランダム選出
            pattern = random.choice(character["patterns"])
            
            voice_id = pattern["id"]
            voice_text = pattern["text"]
            
            print(f"Character: {character['name']} (ID:{voice_id})")
            print(f"Text: {voice_text}")

            # 喋らせる
            speak_zunda(voice_text, speaker_id=voice_id)

            # Discord通知（クールダウンあり）
            # ここでは今日最初の一回だけ通知する仕様
            # was_below_threshold がチェックされているので、開きっぱなしでの連投はない
            if today_date > last_sent_date or last_sent_date is None:
                success_count = 0
                for cid in CHANNEL_IDS:
                    try:
                        channel = bot.get_channel(cid) or await bot.fetch_channel(cid)
                        if channel:
                            await channel.send("部室空きました")
                            success_count += 1
                    except Exception as e:
                        print(f"Failed to send message to channel {cid}: {e}")
                
                if success_count > 0:
                    last_sent_date = today_date
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Notification sent to {success_count} channels!")
        
        was_below_threshold = False
    else:
        # 閾値以下（ドアが閉まっている）
        was_below_threshold = True

# シリアル再接続用
@serial_task.before_loop
async def before_serial():
    await bot.wait_until_ready()
    if ser is not None and not ser.is_open:
        try:
            ser.open()
        except Exception:
            pass

# Bot起動
bot.run(TOKEN)
