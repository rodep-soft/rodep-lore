import os
import certifi

# Fix SSL certificate verification issue
os.environ['SSL_CERT_FILE'] = certifi.where()

import io
import datetime
import subprocess
import json

import discord
from discord.ext import tasks, commands
from discord.ui import View
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

# Intents configuration
intents = discord.Intents.default()
intents.message_content = True

# Bot initialization
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Storage for attendance data
# { user_id: { "name": "User Name", "status": "3限終わり" } }
ATTENDANCE_FILE = "attendance.json"
attendance_data = {}

EVENTS_FILE = "events.json"
events_data = {}

def load_data():
    global attendance_data, events_data
    if os.path.exists(ATTENDANCE_FILE):
        try:
            with open(ATTENDANCE_FILE, 'r', encoding='utf-8') as f:
                attendance_data = json.load(f)
        except Exception:
            attendance_data = {}
    else:
        attendance_data = {}

    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
        except Exception:
            events_data = {}
    else:
        events_data = {}

def save_attendance_data():
    with open(ATTENDANCE_FILE, 'w', encoding='utf-8') as f:
        json.dump(attendance_data, f, ensure_ascii=False, indent=2)

def save_events_data():
    with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(events_data, f, ensure_ascii=False, indent=2)

load_data()

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
    def __init__(self):
        # timeout=None allows the view to persist across bot restarts
        super().__init__(timeout=None)

    async def update_attendance(self, interaction: discord.Interaction, status: str):
        attendance_data[str(interaction.user.id)] = {
            "name": interaction.user.display_name,
            "status": status
        }
        save_attendance_data()
        await interaction.response.send_message(f"「{status}」で出欠を登録しました！", ephemeral=True)

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
time_12pm = datetime.time(hour=12, minute=0, tzinfo=JST)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    # Re-register the persistent view so buttons work after restart
    bot.add_view(AttendanceView())
    
    # Start tasks if not already running
    if not send_attendance_check.is_running():
        send_attendance_check.start()
    if not aggregate_attendance.is_running():
        aggregate_attendance.start()

def get_events_countdown_text():
    if not events_data:
        return ""
    
    today = datetime.datetime.now(JST).date()
    lines = []
    
    # Create a list of events with dates and remove past events
    events_to_keep = {}
    for event_name, date_str in events_data.items():
        try:
            event_date = datetime.datetime.strptime(date_str, "%Y/%m/%d").date()
            diff_days = (event_date - today).days
            if diff_days >= 0:
                events_to_keep[event_name] = date_str
                if diff_days == 0:
                    lines.append(f"🎉 **本日は「{event_name}」当日です！** 🎉")
                else:
                    lines.append(f"🏁 **{event_name}まで あと {diff_days}日**")
        except ValueError:
            pass # Ignore invalid dates
    
    # Save if any past events were removed
    if len(events_to_keep) != len(events_data):
        events_data.clear()
        events_data.update(events_to_keep)
        save_events_data()
        
    if lines:
        return "\n".join(lines) + "\n\n"
    return ""

async def send_attendance_message(channel, is_test=False):
    view = AttendanceView()
    prefix = "【テスト】\n" if is_test else ""
    countdown_text = get_events_countdown_text()
    
    await channel.send(
        f"{prefix}{countdown_text}今日の活動に参加しますか？",
        view=view
    )

async def send_attendance_summary(channel, is_test=False):
    # Categorize data
    categories = {
        "3限終わり": [],
        "4限終わり": [],
        "5限終わり": [],
        "欠席": []
    }
    
    for user_info in attendance_data.values():
        status = user_info["status"]
        if status in categories:
            categories[status].append(user_info["name"])

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
    total_joined = sum(len(categories[c]) for c in ["3限終わり", "4限終わり", "5限終わり"])
    draw.text((40, 90), f"日付: {today_str}   |   合計参加: {total_joined}人", fill=(224, 231, 255), font=small_font)

    # Colors for categories
    cat_colors = {
        "3限終わり": (16, 185, 129), # Emerald green
        "4限終わり": (59, 130, 246), # Blue
        "5限終わり": (245, 158, 11), # Amber
        "欠席": (239, 68, 68)        # Red
    }

    current_y = header_height + 40

    for col in ["3限終わり", "4限終わり", "5限終わり", "欠席"]:
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
        countdown_text = get_events_countdown_text()
        await channel.send(f"{prefix}{countdown_text}本日の出欠集計結果です！", file=file)

@tasks.loop(time=time_8am)
async def send_attendance_check():
    """Sends the attendance check message every day at 8:00 AM JST."""
    global attendance_data
    # Reset attendance data for the new day
    attendance_data.clear()
    save_attendance_data()
    
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await send_attendance_message(channel)

@tasks.loop(time=time_12pm)
async def aggregate_attendance():
    """Aggregates attendance data and sends a summary image every day at 12:00 PM JST."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await send_attendance_summary(channel)

@bot.command(name="test_send")
async def test_send_command(ctx):
    """出欠確認メッセージのテスト送信（データをクリアします）"""
    global attendance_data
    attendance_data.clear()
    save_attendance_data()
    await send_attendance_message(ctx.channel, is_test=True)

@bot.command(name="test_aggregate")
async def test_aggregate_command(ctx):
    """出欠集計結果のテスト送信"""
    await send_attendance_summary(ctx.channel, is_test=True)

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

        events_data[event_name] = date_str
        save_events_data()
        await ctx.send(f"📅 「{event_name}」を {date_str} に登録しました！毎朝カウントダウンをお知らせします。")
    except ValueError:
        await ctx.send("❌ 日付の形式が間違っています。`YYYY/MM/DD` の形式で入力してください。(例: 2026/08/10)")

@bot.command(name="delete_event")
async def delete_event_command(ctx, *, event_name: str):
    """登録したイベントを削除します。例: !delete_event 夏のロボコン"""
    if event_name in events_data:
        del events_data[event_name]
        save_events_data()
        await ctx.send(f"🗑️ イベント「{event_name}」を削除しました。")
    else:
        await ctx.send(f"❌ イベント「{event_name}」は見つかりませんでした。")

@bot.command(name="list_events")
async def list_events_command(ctx):
    """登録されているイベントの一覧を表示します"""
    if not events_data:
        await ctx.send("現在登録されているイベントはありません。")
        return
    
    lines = ["【登録済みのイベント一覧】"]
    for event_name, date_str in events_data.items():
        lines.append(f"・{date_str} : {event_name}")
    
    await ctx.send("\n".join(lines))

@bot.command(name="help")
async def help_command(ctx):
    """コマンド一覧を表示します"""
    help_text = (
        "【Attendance Bot コマンド一覧】\n\n"
        "**■ 基本機能**\n"
        "`!ping` : Botの稼働状況を確認します\n"
        "`!status` : 自動スケジュールの稼働状況を確認します\n\n"
        "**■ 自動送信の制御**\n"
        "`!pause` : 毎朝・毎昼の自動送信を停止します\n"
        "`!resume` : 自動送信を再開します\n\n"
        "**■ イベント管理**\n"
        "`!set_event [日付] [名]` : カウントダウン対象のイベントを登録します\n"
        "  (例: `!set_event 2026/08/10 大会`)\n"
        "`!list_events` : 登録中のイベント一覧を表示します\n"
        "`!delete_event [名]` : 登録したイベントを削除します\n\n"
        "**■ テスト用**\n"
        "`!test_send` : 出欠確認を今すぐ送信します (データはクリアされます)\n"
        "`!test_aggregate` : 現時点の集計結果を今すぐ送信します\n"
    )
    await ctx.send(help_text)

if __name__ == '__main__':
    if TOKEN is None or CHANNEL_ID is None:
        print("Error: DISCORD_TOKEN or CHANNEL_ID is not set in the .env file.")
    else:
        bot.run(TOKEN)
