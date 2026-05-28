import os
import certifi

# Fix SSL certificate verification issue
os.environ['SSL_CERT_FILE'] = certifi.where()

import io
import datetime
import subprocess
import json
import asyncio
import asyncpg

import discord
from discord.ext import tasks, commands
from discord.ui import View
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://bot_user:bot_password@localhost/attendance_bot')

# Database pool
pool = None

# Legacy files for migration
ATTENDANCE_FILE = "attendance.json"
EVENTS_FILE = "events.json"
MEMBERS_FILE = "members.json"

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    
    async with pool.acquire() as conn:
        # Create tables
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                name VARCHAR NOT NULL,
                is_main BOOLEAN DEFAULT FALSE,
                is_tracking BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Cleanup "Unknown" users who might have been added by error
        await conn.execute("UPDATE users SET is_tracking = FALSE WHERE name ILIKE 'unknown'")
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                target_date DATE NOT NULL,
                status VARCHAR NOT NULL,
                is_test BOOLEAN DEFAULT FALSE,
                recorded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, target_date)
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                name VARCHAR PRIMARY KEY,
                event_date DATE NOT NULL
            )
        ''')
        
    # Check for migration
    if any(os.path.exists(f) for f in [ATTENDANCE_FILE, EVENTS_FILE, MEMBERS_FILE]):
        await migrate_json_to_db()

async def migrate_json_to_db():
    print("Starting data migration from JSON to DB...")
    async with pool.acquire() as conn:
        # Migrate Members
        if os.path.exists(MEMBERS_FILE):
            try:
                with open(MEMBERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    main_members = data.get("main_members", {})
                    active_members = data.get("active_members", {})
                    
                    # Combine and insert
                    all_uids = set(main_members.keys()) | set(active_members.keys())
                    for uid in all_uids:
                        name = main_members.get(uid) or active_members.get(uid)
                        await conn.execute('''
                            INSERT INTO users (user_id, name, is_tracking)
                            VALUES ($1, $2, TRUE)
                            ON CONFLICT (user_id) DO UPDATE 
                            SET name = EXCLUDED.name
                        ''', int(uid), name)
                os.rename(MEMBERS_FILE, MEMBERS_FILE + ".bak")
            except Exception as e:
                print(f"Error migrating members: {e}")

        # Migrate Events
        if os.path.exists(EVENTS_FILE):
            try:
                with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, date_str in data.items():
                        try:
                            event_date = datetime.datetime.strptime(date_str, "%Y/%m/%d").date()
                            await conn.execute('''
                                INSERT INTO events (name, event_date)
                                VALUES ($1, $2)
                                ON CONFLICT (name) DO UPDATE SET event_date = EXCLUDED.event_date
                            ''', name, event_date)
                        except ValueError:
                            continue
                os.rename(EVENTS_FILE, EVENTS_FILE + ".bak")
            except Exception as e:
                print(f"Error migrating events: {e}")

        # Migrate Attendance (Only today's)
        if os.path.exists(ATTENDANCE_FILE):
            try:
                today = datetime.datetime.now(JST).date()
                with open(ATTENDANCE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for uid, info in data.items():
                        # Ensure user exists first (might not be in members.json)
                        await conn.execute('''
                            INSERT INTO users (user_id, name)
                            VALUES ($1, $2)
                            ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name
                        ''', int(uid), info["name"])
                        
                        await conn.execute('''
                            INSERT INTO attendance (user_id, target_date, status)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (user_id, target_date) DO UPDATE SET status = EXCLUDED.status
                        ''', int(uid), today, info["status"])
                os.rename(ATTENDANCE_FILE, ATTENDANCE_FILE + ".bak")
            except Exception as e:
                print(f"Error migrating attendance: {e}")
    print("Migration completed.")

# Intents configuration
intents = discord.Intents.default()
intents.message_content = True

# Bot initialization
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Timezone setting (JST)
JST = datetime.timezone(datetime.timedelta(hours=9), 'JST')

def get_japanese_font():
    """Dynamically find a Japanese font available on the system."""
    # List of common Japanese font paths on Linux
    fallbacks = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    ]
    
    try:
        result = subprocess.run(['fc-match', '-f', '%{file}', ':lang=ja'], capture_output=True, text=True)
        if result.stdout and os.path.exists(result.stdout.strip()):
            return result.stdout.strip()
    except Exception:
        pass
    
    for path in fallbacks:
        if os.path.exists(path):
            return path
            
    return None

class AttendanceView(View):
    def __init__(self, is_test=False, is_saturday=None):
        # timeout=None allows the view to persist across bot restarts
        super().__init__(timeout=None)
        self.is_test = is_test
        
        if is_saturday is True:
            self.remove_item(self.btn_3)
            self.remove_item(self.btn_4)
            self.remove_item(self.btn_5)
        elif is_saturday is False:
            self.remove_item(self.btn_sat)

    async def update_attendance(self, interaction: discord.Interaction, status: str):
        user_id = interaction.user.id
        user_name = interaction.user.display_name
        today = datetime.datetime.now(JST).date()
        
        async with pool.acquire() as conn:
            # Ensure user exists and update tracking/name
            await conn.execute('''
                INSERT INTO users (user_id, name, is_tracking)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name
            ''', user_id, user_name)
            
            # Insert or update attendance
            await conn.execute('''
                INSERT INTO attendance (user_id, target_date, status, is_test)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, target_date) DO UPDATE SET status = EXCLUDED.status, recorded_at = CURRENT_TIMESTAMP, is_test = EXCLUDED.is_test
            ''', user_id, today, status, self.is_test)
            
        await interaction.response.send_message(f"「{status}」で出欠を登録しました！", ephemeral=True)

    @discord.ui.button(label="出席", style=discord.ButtonStyle.primary, custom_id="attend_sat")
    async def btn_sat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_attendance(interaction, "出席")

    @discord.ui.button(label="3限終わり", style=discord.ButtonStyle.primary, custom_id="attend_3")
    async def btn_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_attendance(interaction, "3限終わり")

    @discord.ui.button(label="4限終わり", style=discord.ButtonStyle.primary, custom_id="attend_4")
    async def btn_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_attendance(interaction, "4限終わり")

    @discord.ui.button(label="5限終わり", style=discord.ButtonStyle.primary, custom_id="attend_5")
    async def btn_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_attendance(interaction, "5限終わり")

    @discord.ui.button(label="欠席", style=discord.ButtonStyle.danger, custom_id="attend_absent")
    async def btn_absent(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_attendance(interaction, "欠席")

# Scheduled times
time_8am = datetime.time(hour=8, minute=0, tzinfo=JST)
time_1230pm = datetime.time(hour=12, minute=30, tzinfo=JST)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    
    # Initialize DB
    await init_db()
    
    # Re-register the persistent view so buttons work after restart
    bot.add_view(AttendanceView())
    
    # Start tasks if not already running
    if not send_attendance_check.is_running():
        send_attendance_check.start()
    if not aggregate_attendance.is_running():
        aggregate_attendance.start()

async def get_events_countdown_text():
    today = datetime.datetime.now(JST).date()
    lines = []
    
    async with pool.acquire() as conn:
        # Delete past events
        await conn.execute('DELETE FROM events WHERE event_date < $1', today)
        
        # Fetch remaining events
        rows = await conn.fetch('SELECT name, event_date FROM events ORDER BY event_date ASC')
        
        for row in rows:
            name = row['name']
            event_date = row['event_date']
            diff_days = (event_date - today).days
            if diff_days == 0:
                lines.append(f"🎉 **本日は「{name}」当日です！** 🎉")
            else:
                lines.append(f"🏁 **{name}まで あと {diff_days}日**")
        
    if lines:
        return "\n".join(lines) + "\n\n"
    return ""

async def send_attendance_message(channel, is_test=False):
    today = datetime.datetime.now(JST).date()
    is_saturday = today.weekday() == 5
    
    view = AttendanceView(is_test=is_test, is_saturday=is_saturday)
    prefix = "【テスト】\n" if is_test else ""
    countdown_text = await get_events_countdown_text()
    
    question = "会議に参加しますか？" if is_saturday else "今日の活動に参加しますか？"
    note = "\n\n⚠️ **回答できない場合や「未回答」に残る場合は、このチャンネルで連絡してください！**"
    
    await channel.send(
        f"{prefix}{countdown_text}{question}{note}",
        view=view
    )

async def send_attendance_summary(channel, is_test=False):
    today = datetime.datetime.now(JST).date()
    is_saturday = today.weekday() == 5
    
    if is_saturday:
        display_order = ["出席", "欠席", "未回答者"]
    else:
        display_order = ["3限終わり", "4限終わり", "5限終わり", "欠席", "未回答者"]
    
    categories = {k: [] for k in display_order}
    
    async with pool.acquire() as conn:
        # Get all attendance for today
        # If it's a test run, we query records marked as is_test=TRUE
        # If it's a real run, we query records marked as is_test=FALSE
        rows = await conn.fetch('''
            SELECT u.name, u.is_main, a.status 
            FROM attendance a 
            JOIN users u ON a.user_id = u.user_id 
            WHERE a.target_date = $1 AND a.is_test = $2
        ''', today, is_test)
        
        for row in rows:
            name = row['name']
            if row['is_main']:
                name = "(M) " + name
            status = row['status']
            if status in categories:
                categories[status].append(name)
            elif is_saturday and status in ["3限終わり", "4限終わり", "5限終わり"]:
                # Handle edge case where someone used an old button on Saturday
                categories["出席"].append(name)
                
        # Calculate non-respondents
        missing_rows = await conn.fetch('''
            SELECT name, is_main 
            FROM users 
            WHERE is_tracking = TRUE AND is_hidden_if_unresponsive = FALSE AND name NOT ILIKE 'unknown'
            AND user_id NOT IN (SELECT user_id FROM attendance WHERE target_date = $1 AND is_test = $2)
            ORDER BY is_main DESC, name ASC
        ''', today, is_test)

        for row in missing_rows:
            name = row['name']
            if row['is_main']:
                name = "(M) " + name
            categories["未回答者"].append(name)

    # Image configuration - Vertical mobile-friendly layout
    width = 720
    header_height = 140
    line_height = 56
    category_padding = 40
    
    # Calculate required height
    total_users_lines = sum(len(users) if users else 1 for users in categories.values())
    # Base height: header + bottom padding + padding per category + title heights
    height = header_height + 60 + (len(categories) * (category_padding + 60)) + (total_users_lines * line_height)
    height = int(max(height, 800)) # Minimum height

    # Create image canvas
    bg_color = (244, 244, 249) # Light modern gray background
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    font_path = get_japanese_font()
    try:
        title_font = ImageFont.truetype(font_path, 42) if font_path else ImageFont.load_default()
        category_font = ImageFont.truetype(font_path, 32) if font_path else ImageFont.load_default()
        text_font = ImageFont.truetype(font_path, 28) if font_path else ImageFont.load_default()
        small_font = ImageFont.truetype(font_path, 22) if font_path else ImageFont.load_default()
    except Exception:
        title_font = ImageFont.load_default()
        category_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Draw Header (Modern Indigo)
    header_color = (79, 70, 229) 
    draw.rectangle([0, 0, width, header_height], fill=header_color)
    
    today_str = datetime.datetime.now(JST).strftime("%Y年%m月%d日")
    prefix = "【テスト】" if is_test else ""
    title_text = f"{prefix}出欠集計結果"
    
    draw.text((40, 30), title_text, fill=(255, 255, 255), font=title_font)
    if is_saturday:
        total_joined = len(categories.get("出席", []))
    else:
        total_joined = sum(len(categories.get(c, [])) for c in ["3限終わり", "4限終わり", "5限終わり"])
    draw.text((40, 90), f"日付: {today_str}   |   合計参加: {total_joined}人", fill=(224, 231, 255), font=small_font)

    # Colors for categories
    cat_colors = {
        "3限終わり": (16, 185, 129), # Emerald green
        "4限終わり": (59, 130, 246), # Blue
        "5限終わり": (245, 158, 11), # Amber
        "出席": (16, 185, 129),       # Emerald green
        "欠席": (239, 68, 68),        # Red
        "未回答者": (156, 163, 175)    # Gray
    }

    current_y = header_height + 40

    for col in display_order:
        users = categories[col]
        color = cat_colors.get(col, (100, 100, 100))
        
        card_margin_x = 40
        
        # Category Accent Line
        try:
            draw.rounded_rectangle([card_margin_x, current_y, card_margin_x + 8, current_y + 40], radius=4, fill=color)
        except AttributeError:
            # Fallback for very old PIL versions
            draw.rectangle([card_margin_x, current_y, card_margin_x + 8, current_y + 40], fill=color)
        
        # Category Title
        draw.text((card_margin_x + 28, current_y + 2), f"{col} ({len(users)}人)", fill=(31, 41, 55), font=category_font)
        
        current_y += 60
        
        # Draw users
        if not users:
            draw.text((card_margin_x + 28, current_y + 8), "なし", fill=(156, 163, 175), font=text_font)
            current_y += line_height
        else:
            for name in users:
                # User Card Background
                try:
                    draw.rounded_rectangle([card_margin_x + 20, current_y, width - card_margin_x, current_y + 48], radius=8, fill=(255, 255, 255))
                except AttributeError:
                    draw.rectangle([card_margin_x + 20, current_y, width - card_margin_x, current_y + 48], fill=(255, 255, 255))
                
                # User Name Text
                draw.text((card_margin_x + 40, current_y + 8), name, fill=(75, 85, 99), font=text_font)
                current_y += line_height
                
        current_y += category_padding

    # Save to binary stream and send to Discord
    with io.BytesIO() as image_binary:
        img.save(image_binary, 'PNG')
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename='attendance_summary.png')
        countdown_text = await get_events_countdown_text()
        
        await channel.send(f"{prefix}{countdown_text}本日の出欠集計結果です！", file=file)

@tasks.loop(time=time_8am)
async def send_attendance_check():
    """Wait for network and send the attendance check as soon as possible."""
    trigger_date = datetime.datetime.now(JST).date()
    
    while True:
        # Avoid sending yesterday's form if it's already the next day
        if datetime.datetime.now(JST).date() != trigger_date:
            print(f"Aborting attendance check for {trigger_date}: Day changed.")
            return

        try:
            # fetch_channel is more reliable than get_channel after reconnect
            channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
            if channel:
                await send_attendance_message(channel)
                print(f"Successfully sent attendance check for {trigger_date}")
                return
        except Exception as e:
            # Probably network error or Discord is down
            print(f"Attendance check: Waiting for network... ({e})")
            await asyncio.sleep(60)

@tasks.loop(time=time_1230pm)
async def aggregate_attendance():
    """Wait for network and send the attendance summary as soon as possible."""
    trigger_date = datetime.datetime.now(JST).date()
    
    while True:
        if datetime.datetime.now(JST).date() != trigger_date:
            print(f"Aborting aggregation for {trigger_date}: Day changed.")
            return

        try:
            channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
            if channel:
                await send_attendance_summary(channel)
                print(f"Successfully sent summary for {trigger_date}")
                return
        except Exception as e:
            print(f"Aggregation: Waiting for network... ({e})")
            await asyncio.sleep(60)

@bot.command(name="send_now")
async def send_now_command(ctx):
    """【本番用】今すぐ出欠確認フォームを送信します"""
    await send_attendance_message(ctx.channel, is_test=False)
    await ctx.send("✅ 本番用の出欠確認フォームを送信しました。")

@bot.command(name="test_send")
async def test_send_command(ctx):
    """出欠確認メッセージのテスト送信（テストデータをクリアします）"""
    today = datetime.datetime.now(JST).date()
    async with pool.acquire() as conn:
        # Clear only test data for today
        await conn.execute('DELETE FROM attendance WHERE target_date = $1 AND is_test = TRUE', today)
    await send_attendance_message(ctx.channel, is_test=True)

@bot.command(name="test_aggregate")
async def test_aggregate_command(ctx):
    """出欠集計結果のテスト送信（テストデータを使用します）"""
    await send_attendance_summary(ctx.channel, is_test=True)

@bot.command(name="aggregate_now")
async def aggregate_now_command(ctx):
    """【本番用】今すぐ出欠集計結果を送信します"""
    await send_attendance_summary(ctx.channel, is_test=False)
    await ctx.send("✅ 本番用の出欠集計結果を送信しました。")

@bot.command(name="clear_tests")
async def clear_tests_command(ctx):
    """DB内のすべてのテストデータを削除します"""
    async with pool.acquire() as conn:
        result = await conn.execute('DELETE FROM attendance WHERE is_test = TRUE')
        count = result.split(" ")[1]
    await ctx.send(f"🗑️ {count} 件のテストデータを削除しました。")

@bot.command(name="check")
async def check_command(ctx):
    """【確認用】本日の回答状況をテキストで表示します"""
    today = datetime.datetime.now(JST).date()
    
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT u.name, u.is_main, a.status 
            FROM attendance a 
            JOIN users u ON a.user_id = u.user_id 
            WHERE a.target_date = $1 AND a.is_test = FALSE
            ORDER BY a.recorded_at ASC
        ''', today)
    
    if not rows:
        await ctx.send("今日の回答者はまだいません。")
        return
    
    lines = [f"**📊 本日の回答状況 ({today.strftime('%m/%d')})**"]
    for row in rows:
        prefix = "(M) " if row['is_main'] else "・"
        lines.append(f"{prefix}{row['name']} : {row['status']}")
    
    await ctx.send("\n".join(lines))

@bot.command(name="db_info")
async def db_info_command(ctx):
    """【管理者用】DBの統計情報を表示します"""
    async with pool.acquire() as conn:
        user_count = await conn.fetchval('SELECT count(*) FROM users')
        tracking_count = await conn.fetchval('SELECT count(*) FROM users WHERE is_tracking = TRUE')
        main_count = await conn.fetchval('SELECT count(*) FROM users WHERE is_main = TRUE')
        event_count = await conn.fetchval('SELECT count(*) FROM events')
        today = datetime.datetime.now(JST).date()
        today_attendance = await conn.fetchval('SELECT count(*) FROM attendance WHERE target_date = $1', today)

    msg = (
        "**🗄️ データベース統計情報**\n"
        f"┣ 総ユーザー数: {user_count}名\n"
        f"┣ 追跡対象ユーザー: {tracking_count}名\n"
        f"┣ メインメンバー: {main_count}名\n"
        f"┣ 登録イベント数: {event_count}件\n"
        f"┗ 本日の回答数: {today_attendance}件"
    )
    await ctx.send(msg)

@bot.command(name="sql")
async def sql_command(ctx, *, query: str):
    """【管理者専用】SQLを直接実行します"""
    # 特定のユーザーID（管理者）のみ実行可能にする
    if ctx.author.id != 1082889857052983366:
        await ctx.send("❌ このコマンドを実行する権限がありません。")
        return

    async with pool.acquire() as conn:
        try:
            if query.strip().lower().startswith("select"):
                rows = await conn.fetch(query)
                if not rows:
                    await ctx.send("結果は0件でした。")
                    return
                
                # 結果を整形して送信
                headers = rows[0].keys()
                header_line = " | ".join(headers)
                lines = [header_line, "-" * len(header_line)]
                for row in rows[:10]: # 最大10件
                    lines.append(" | ".join(str(v) for v in row.values()))
                
                result_text = "\n".join(lines)
                if len(rows) > 10:
                    result_text += f"\n... (残り {len(rows)-10} 件)"
                
                await ctx.send(f"```\n{result_text}\n```")
            else:
                result = await conn.execute(query)
                await ctx.send(f"✅ 実行完了: `{result}`")
        except Exception as e:
            await ctx.send(f"❌ SQLエラー: `{e}`")

@bot.command(name="ping")
async def ping_command(ctx):
    """動作確認用コマンド"""
    await ctx.send("Botは正常に稼働しています！")

@bot.command(name="pause")
async def pause_command(ctx):
    """毎日の自動出欠確認と集計を一時停止します"""
    send_attendance_check.cancel()
    aggregate_attendance.cancel()
    await ctx.send("自動出欠確認と集計のスケジュールを一時停止しました。再開するには `!resume` と送信してください。")

@bot.command(name="resume")
async def resume_command(ctx):
    """毎日の自動出欠確認と集計を再開します"""
    if not send_attendance_check.is_running():
        send_attendance_check.start()
    if not aggregate_attendance.is_running():
        aggregate_attendance.start()
    await ctx.send("自動出欠確認と集計のスケジュールを再開しました。")

@bot.command(name="status")
async def status_command(ctx):
    """現在の自動スケジュールの稼働状況を確認します"""
    send_status = "稼働中" if send_attendance_check.is_running() else "停止中"
    aggregate_status = "稼働中" if aggregate_attendance.is_running() else "停止中"
    
    status_msg = (
        "【現在の稼働状況】\n"
        f"・自動出欠確認 (毎朝8時): {send_status}\n"
        f"・自動集計送信 (毎日12時): {aggregate_status}"
    )
    await ctx.send(status_msg)

@bot.command(name="set_event")
async def set_event_command(ctx, date_str: str, *, event_name: str):
    """大会などのイベント日を登録します。例: !set_event 2026/08/10 夏のロボコン"""
    try:
        # Validate date format
        event_date = datetime.datetime.strptime(date_str, "%Y/%m/%d").date()
        today = datetime.datetime.now(JST).date()
        
        if event_date < today:
            await ctx.send("❌ 過去の日付は登録できません。今日以降の日付を指定してください。")
            return

        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO events (name, event_date)
                VALUES ($1, $2)
                ON CONFLICT (name) DO UPDATE SET event_date = EXCLUDED.event_date
            ''', event_name, event_date)
            
        await ctx.send(f"📅 「{event_name}」を {date_str} に登録しました！毎朝カウントダウンをお知らせします。")
    except ValueError:
        await ctx.send("❌ 日付の形式が間違っています。`YYYY/MM/DD` の形式で入力してください。(例: 2026/08/10)")

@bot.command(name="delete_event")
async def delete_event_command(ctx, *, event_name: str):
    """登録したイベントを削除します。例: !delete_event 夏のロボコン"""
    async with pool.acquire() as conn:
        result = await conn.execute('DELETE FROM events WHERE name = $1', event_name)
        
    if result == "DELETE 1":
        await ctx.send(f"🗑️ イベント「{event_name}」を削除しました。")
    else:
        await ctx.send(f"❌ イベント「{event_name}」は見つかりませんでした。")

@bot.command(name="list_events")
async def list_events_command(ctx):
    """登録されているイベントの一覧を表示します"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT name, event_date FROM events ORDER BY event_date ASC')
        
    if not rows:
        await ctx.send("現在登録されているイベントはありません。")
        return
    
    lines = ["【登録済みのイベント一覧】"]
    for row in rows:
        lines.append(f"・{row['event_date'].strftime('%Y/%m/%d')} : {row['name']}")
    
    await ctx.send("\n".join(lines))

@bot.command(name="forget_me")
async def forget_me_command(ctx):
    """自身の出欠トラッキング（未回答者リストへの表示）を停止します。"""
    user_id = ctx.author.id
    async with pool.acquire() as conn:
        result = await conn.execute('UPDATE users SET is_tracking = FALSE WHERE user_id = $1', user_id)
        
    if result == "UPDATE 1":
        await ctx.send(f"👋 {ctx.author.display_name} さんのトラッキングを停止しました。")
    else:
        await ctx.send("あなたは現在トラッキングされていません。")

@bot.command(name="list_members")
async def list_members_command(ctx):
    """登録されているメンバーの一覧を表示します"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT name FROM users WHERE is_tracking = TRUE ORDER BY name ASC')
    
    member_list = [f"・{r['name']}" for r in rows]
    
    msg = "**【登録されているメンバー一覧】**\n" + ("\n".join(member_list) if member_list else "なし")
    
    await ctx.send(msg)

@bot.command(name="add_member")
async def add_member_command(ctx, member: discord.Member = None):
    """指定したメンバーを登録し、出欠トラッキングの対象にします。"""
    if member is None:
        await ctx.send("❌ 登録したいメンバーをメンションしてください。例: `!add_member @ユーザー名`")
        return

    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, name, is_tracking)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (user_id) DO UPDATE 
            SET name = EXCLUDED.name, is_tracking = TRUE
        ''', member.id, member.display_name)
        
    await ctx.send(f"✅ {member.display_name} さんをメンバーリストに登録しました！")

@bot.command(name="set_main")
async def set_main_command(ctx, member: discord.Member = None):
    """指定したメンバーを「メインメンバー」として設定します。"""
    if member is None:
        await ctx.send("❌ 指定したいメンバーをメンションしてください。")
        return

    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE users SET is_main = TRUE, is_tracking = TRUE WHERE user_id = $1
        ''', member.id)
        
    await ctx.send(f"⭐ {member.display_name} さんをメインメンバーに設定しました！")

@bot.command(name="remove_member")
async def remove_member_command(ctx, member: discord.Member = None):
    """指定したメンバーをリストから削除（トラッキング停止）します。"""
    if member is None:
        await ctx.send("❌ 削除したいメンバーをメンションしてください。")
        return

    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET is_tracking = FALSE WHERE user_id = $1', member.id)
        
    await ctx.send(f"🗑️ {member.display_name} さんのトラッキングを停止しました。")

@bot.command(name="help")
async def help_command(ctx):
    """コマンド一覧を表示します"""
    help_text = (
        "**📋 出欠Bot コマンド一覧**\n\n"
        "👤 **メンバー管理**\n"
        "┣ `!add_member @名` : 指定メンバーを対象に追加\n"
        "┣ `!remove_member @名` : 指定メンバーを対象から外す\n"
        "┣ `!list_members` : 現在の対象メンバー一覧\n"
        "┗ `!forget_me` : 自分自身を対象から外す\n\n"
        "📅 **イベント・カウントダウン**\n"
        "┣ `!set_event YYYY/MM/DD 名前` : イベント追加\n"
        "┣ `!list_events` : 登録済みのイベント一覧\n"
        "┗ `!delete_event 名前` : イベント削除\n\n"
        "🔍 **状況確認・テスト**\n"
        "┣ `!check` : 本日の回答状況をテキストで表示\n"
        "┣ `!test_send` : 出欠確認を今すぐ送信 (本番データリセット)\n"
        "┣ `!test_aggregate` : 現時点の集計画像を送信\n"
        "┗ `!ping` : Botの生存確認\n\n"
        "⚙️ **管理者・DB操作**\n"
        "┣ `!db_info` : データベースの統計情報を表示\n"
        "┣ `!sql [クエリ]` : SQLを直接実行 (管理者のみ)\n"
        "┣ `!status` : 自動送信の稼働状況を確認\n"
        "┗ `!pause` / `!resume` : 自動送信の 停止 / 再開\n\n"
        "💡 *Tip: 朝8時のボタンを1度でも押すと自動的にメンバー登録されます。*\n"
        "⚠️ *ボタンで回答できない場合は、このチャンネルで直接連絡してください。*"
    )
    await ctx.send(help_text)

if __name__ == '__main__':
    if TOKEN is None or CHANNEL_ID is None:
        print("Error: DISCORD_TOKEN or CHANNEL_ID is not set in the .env file.")
    else:
        bot.run(TOKEN)
