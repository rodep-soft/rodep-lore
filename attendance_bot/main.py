import os
import certifi

# Fix SSL certificate verification issue
os.environ['SSL_CERT_FILE'] = certifi.where()

import io
import datetime
import json
import asyncio

import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv

import db
from config import load_config, save_config, parse_time
from views import AttendanceView, MeetingPromptView, MeetingAnnouncementModal
from image_generator import create_summary_image

# Load environment variables & configuration
load_dotenv()
config = load_config()

TOKEN = os.getenv('DISCORD_TOKEN')

# Channel resolution (env takes priority if present, otherwise config.yaml)
CHANNEL_ID = int(os.getenv('CHANNEL_ID')) if os.getenv('CHANNEL_ID') else config.get("channels", {}).get("attendance_channel_id", 0)

late_channel_env = os.getenv('LATE_CHANNEL_ID')
if late_channel_env:
    LATE_CHANNEL_IDS = [int(late_channel_env)]
else:
    LATE_CHANNEL_IDS = config.get("channels", {}).get("late_channel_ids", [1238834537417412770])

# Intents configuration
intents = discord.Intents.default()
intents.message_content = True

# Bot initialization
command_prefix = config.get("bot", {}).get("command_prefix", "!")
bot = commands.Bot(command_prefix=command_prefix, intents=intents, help_command=None)

# Timezone setting (JST)
JST = datetime.timezone(datetime.timedelta(hours=9), 'JST')

# Scheduled times from config.yaml
schedule_cfg = config.get("schedule", {})
time_8am = parse_time(schedule_cfg.get("send_check_time", "08:00"), 8, 0)
time_12pm = parse_time(schedule_cfg.get("remind_unanswered_time", "12:00"), 12, 0)
time_1230pm = parse_time(schedule_cfg.get("aggregate_summary_time", "12:30"), 12, 30)

DAY_MAP = {
    "Monday": 0, "Mon": 0, "月曜日": 0, "月": 0,
    "Tuesday": 1, "Tue": 1, "火曜日": 1, "火": 1,
    "Wednesday": 2, "Wed": 2, "水曜日": 2, "水": 2,
    "Thursday": 3, "Thu": 3, "木曜日": 3, "木": 3,
    "Friday": 4, "Fri": 4, "金曜日": 4, "金": 4,
    "Saturday": 5, "Sat": 5, "土曜日": 5, "土": 5,
    "Sunday": 6, "Sun": 6, "日曜日": 6, "日": 6,
}

sent_meeting_reminders = set()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    
    # Initialize DB
    await db.init_db(JST)
    
    # Re-register the persistent view so buttons work after restart
    bot.add_view(AttendanceView())
    
    # Start tasks if not already running
    if not send_attendance_check.is_running():
        send_attendance_check.start()
    if not aggregate_attendance.is_running():
        aggregate_attendance.start()
    if not remind_unanswered.is_running():
        remind_unanswered.start()
    if not check_meeting_schedule.is_running():
        check_meeting_schedule.start()

@tasks.loop(seconds=30)
async def check_meeting_schedule():
    """Check every 30 seconds if any meeting announcement needs to be sent."""
    now = datetime.datetime.now(JST)
    weekday = now.weekday()
    current_time_str = now.strftime("%Y-%m-%d %H:%M")
    
    cfg = load_config()
    default_ch_id = CHANNEL_ID
    meetings = cfg.get("meetings", [])
    
    for meeting in meetings:
        if not meeting.get("enabled", True):
            continue

        target_channel_ids = meeting.get("channel_ids") or ([meeting.get("channel_id")] if meeting.get("channel_id") else [default_ch_id])
        target_channel_ids = [ch_id for ch_id in target_channel_ids if ch_id]
        if not target_channel_ids:
            continue

        target_day = meeting.get("day_of_week")
        if target_day not in DAY_MAP or DAY_MAP[target_day] != weekday:
            continue
            
        time_str = meeting.get("announcement_time", "08:30")
        try:
            parts = time_str.split(":")
            a_hour, a_minute = int(parts[0]), int(parts[1])
        except Exception:
            continue
            
        # Check automatic announcement time (e.g. 08:30 in morning)
        if now.hour == a_hour and now.minute == a_minute:
            key = (meeting.get("name"), "announcement", current_time_str)
            if key not in sent_meeting_reminders:
                sent_meeting_reminders.add(key)
                for ch_id in target_channel_ids:
                    await send_meeting_announcement(ch_id, meeting)

    # Clean up old keys from sent_meeting_reminders (keep only last 2 hours)
    cleanup_keys = [k for k in sent_meeting_reminders if (now - datetime.datetime.strptime(k[2], "%Y-%m-%d %H:%M").replace(tzinfo=JST)).total_seconds() > 7200]
    for k in cleanup_keys:
        sent_meeting_reminders.remove(k)

async def send_meeting_announcement(channel_id: int, meeting: dict, agenda: str = None, notice: str = None, location: str = None, start_time: str = None):
    try:
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        if not channel:
            return

        name = meeting.get("name", "定例会")
        mention = meeting.get("role_mention", "@制御班")
        reactions = meeting.get("reactions", {"attend": "🫡", "absent": "🧐"})
        attend_emoji = reactions.get("attend", "🫡")
        absent_emoji = reactions.get("absent", "🧐")

        m_location = meeting.get("temp_location") or location or meeting.get("location", "研究棟")
        m_start_time = meeting.get("temp_start_time") or start_time or meeting.get("start_time", "18:00")
        m_agenda = meeting.get("temp_agenda") if meeting.get("temp_agenda") is not None else (agenda if agenda is not None else meeting.get("agenda", ""))
        m_notice = meeting.get("temp_notice") if meeting.get("temp_notice") is not None else (notice if notice is not None else meeting.get("notice", ""))

        guild = getattr(channel, "guild", None)
        if guild and mention:
            target_role = None
            clean_name = mention.lstrip("@").strip()
            # 1. Look for exact name match
            target_role = discord.utils.get(guild.roles, name=clean_name)
            # 2. Look for case-insensitive match
            if not target_role:
                for r in guild.roles:
                    if r.name.lower() == clean_name.lower():
                        target_role = r
                        break
            # 3. Look for role ID if mention is numeric string
            if not target_role and clean_name.isdigit():
                target_role = guild.get_role(int(clean_name))

            if target_role:
                mention = target_role.mention

        today_str = datetime.datetime.now(JST).strftime("%m/%d")
        lines = [
            f"{mention} 💻",
            f"{today_str}の{name}についてです．",
            f"予定通り{m_start_time}より{m_location}にて行います．"
        ]

        if m_agenda.strip():
            lines.append("＜議題＞")
            lines.append(m_agenda.strip())

        if m_notice.strip():
            lines.append("＜連絡＞")
            lines.append(m_notice.strip())

        minutes_url = meeting.get("minutes_url", "")
        if minutes_url:
            lines.append(f"📝 議題・議事録: {minutes_url}")

        lines.append(f"参加する人は{attend_emoji} ，参加しない人は{absent_emoji} のリアクションお願いします．")

        announcement_text = "\n".join(lines)
        msg = await channel.send(announcement_text)
        try:
            await msg.add_reaction(attend_emoji)
            await msg.add_reaction(absent_emoji)
        except Exception as e:
            print(f"Failed to add reactions: {e}")

        # Clear temporary one-time overrides after sending
        has_temp = False
        for k in ["temp_location", "temp_start_time", "temp_agenda", "temp_notice"]:
            if k in meeting:
                del meeting[k]
                has_temp = True
        if has_temp:
            save_config(load_config())

        print(f"Sent meeting announcement for '{name}' to channel {channel_id}")
    except Exception as e:
        print(f"Failed to send meeting announcement for '{meeting.get('name')}': {e}")

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages sent by bots
    if message.author.bot:
        return

    cfg = load_config()
    unanswered_role_name = cfg.get("roles", {}).get("unanswered_role_name", "未回答者")

    # Check if message is sent in target channel (CHANNEL_ID or LATE_CHANNEL_IDS)
    target_channels = set([CHANNEL_ID] + LATE_CHANNEL_IDS)
    if message.channel.id in target_channels and message.guild:
        role = discord.utils.get(message.guild.roles, name=unanswered_role_name)
        if role and role in message.author.roles:
            try:
                await message.author.remove_roles(role)
            except Exception as e:
                print(f"Failed to remove '{unanswered_role_name}' role from {message.author.display_name}: {e}")

    await bot.process_commands(message)

async def get_events_countdown_text():
    today = datetime.datetime.now(JST).date()
    lines = []
    
    async with db.pool.acquire() as conn:
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
    cfg = load_config()
    
    view = AttendanceView(is_test=is_test, is_saturday=is_saturday)
    prefix = "【テスト】\n" if is_test else ""
    countdown_text = await get_events_countdown_text()
    
    target_role_name = cfg.get("roles", {}).get("target_role_name", "ROX-2026")
    mention_text = ""
    if hasattr(channel, "guild") and channel.guild:
        role = discord.utils.get(channel.guild.roles, name=target_role_name)
        if role:
            if is_test:
                mention_text = f"`@{target_role_name}` (テスト用表示)\n"
            else:
                mention_text = f"{role.mention}\n"
        else:
            mention_text = f"@{target_role_name}\n"
    else:
        mention_text = f"@{target_role_name}\n"
        
    msg_cfg = cfg.get("messages", {})
    question = msg_cfg.get("saturday_question", "会議に参加しますか？") if is_saturday else msg_cfg.get("weekday_question", "今日の活動に参加しますか？")
    note = msg_cfg.get("note", "\n\n⚠️ **回答できない場合や「未回答」に残る場合は、このチャンネルで連絡してください！**")
    
    await channel.send(
        f"{prefix}{mention_text}{countdown_text}{question}{note}",
        view=view
    )

async def send_attendance_summary(channel, is_test=False):
    today = datetime.datetime.now(JST).date()
    is_saturday = today.weekday() == 5
    cfg = load_config()
    unanswered_role_name = cfg.get("roles", {}).get("unanswered_role_name", "未回答者")
    
    if is_saturday:
        display_order = ["出席", "欠席", unanswered_role_name]
    else:
        display_order = ["3限終わり", "4限終わり", "5限終わり", "欠席", unanswered_role_name]
    
    categories = {k: [] for k in display_order}
    
    async with db.pool.acquire() as conn:
        # Get all attendance for today
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
            categories[unanswered_role_name].append(name)

    # Generate image using utility function
    today_str = today.strftime("%Y年%m月%d日")
    image_binary = create_summary_image(categories, is_saturday, today_str, is_test, display_order)
    
    file = discord.File(fp=image_binary, filename='attendance_summary.png')
    countdown_text = await get_events_countdown_text()
    
    prefix = "【テスト】" if is_test else ""
    await channel.send(f"{prefix}{countdown_text}本日の出欠集計結果です！", file=file)

@tasks.loop(time=time_8am)
async def send_attendance_check():
    """Wait for network and send the attendance check as soon as possible."""
    trigger_date = datetime.datetime.now(JST).date()
    
    while True:
        if datetime.datetime.now(JST).date() != trigger_date:
            print(f"Aborting attendance check for {trigger_date}: Day changed.")
            return

        try:
            channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
            if channel:
                await send_attendance_message(channel)
                print(f"Successfully sent attendance check for {trigger_date}")
                return
        except Exception as e:
            print(f"Attendance check: Waiting for network... ({e})")
            await asyncio.sleep(60)

@tasks.loop(time=time_12pm)
async def remind_unanswered():
    """Mention and grant a temporary role to users who haven't responded by remind_unanswered_time."""
    trigger_date = datetime.datetime.now(JST).date()
    cfg = load_config()
    unanswered_role_name = cfg.get("roles", {}).get("unanswered_role_name", "未回答者")
    should_assign_role = cfg.get("roles", {}).get("assign_unanswered_role", False)
    
    while True:
        if datetime.datetime.now(JST).date() != trigger_date:
            return

        try:
            channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
            if not channel:
                await asyncio.sleep(60)
                continue

            guild = channel.guild
            role = None
            if should_assign_role:
                role = discord.utils.get(guild.roles, name=unanswered_role_name)
                if not role:
                    try:
                        role = await guild.create_role(name=unanswered_role_name, color=discord.Color.orange(), reason="リマインド用一時ロール", mentionable=True)
                    except Exception as e:
                        print(f"Failed to create role: {e}")
                        return
                else:
                    if not role.mentionable:
                        try:
                            await role.edit(mentionable=True)
                        except Exception as e:
                            print(f"Failed to make role mentionable: {e}")

            async with db.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT u.user_id FROM users u 
                    LEFT JOIN attendance a ON u.user_id = a.user_id AND a.target_date = $1 AND a.is_test = FALSE 
                    WHERE u.is_tracking = TRUE AND a.user_id IS NULL
                ''', trigger_date)
            
            if not rows:
                print("No unanswered users to remind.")
                return

            has_unanswered = False
            for row in rows:
                user_id = row['user_id']
                member = guild.get_member(user_id)
                if not member:
                    try:
                        member = await guild.fetch_member(user_id)
                    except discord.NotFound:
                        print(f"User {user_id} not found in guild.")
                        continue
                    except Exception as e:
                        print(f"Failed to fetch member {user_id}: {e}")
                        continue

                if member:
                    has_unanswered = True
                    if should_assign_role and role:
                        try:
                            await member.add_roles(role)
                        except Exception as e:
                            print(f"Failed to add role to {member.display_name}: {e}")

            if has_unanswered:
                msg_cfg = cfg.get("messages", {})
                remind_title = msg_cfg.get("remind_title", "🔔 **【リマインド】**")
                remind_body = msg_cfg.get("remind_body", "今日の出欠がまだ未回答です！回答をお願いします！")
                
                mention_str = role.mention if (should_assign_role and role) else ""
                content = f"{remind_title}\n"
                if mention_str:
                    content += f"{mention_str}\n"
                content += f"{remind_body}"
                
                await channel.send(content)
            return

        except Exception as e:
            print(f"Remind unanswered: Waiting for network... ({e})")
            await asyncio.sleep(60)

@tasks.loop(time=time_1230pm)
async def aggregate_attendance():
    """Wait for network and send the attendance summary as soon as possible."""
    trigger_date = datetime.datetime.now(JST).date()
    cfg = load_config()
    unanswered_role_name = cfg.get("roles", {}).get("unanswered_role_name", "未回答者")
    
    while True:
        if datetime.datetime.now(JST).date() != trigger_date:
            print(f"Aborting aggregation for {trigger_date}: Day changed.")
            return

        try:
            channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
            if channel:
                await send_attendance_summary(channel)
                
                role = discord.utils.get(channel.guild.roles, name=unanswered_role_name)
                if role:
                    for member in role.members:
                        try:
                            await member.remove_roles(role)
                        except Exception:
                            pass
                
                print(f"Successfully sent summary and cleaned up roles for {trigger_date}")
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
    async with db.pool.acquire() as conn:
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

@bot.command(name="remind_now")
@commands.has_permissions(manage_messages=True)
async def remind_now_command(ctx):
    """【管理者用】今すぐ未回答者へのリマインドを実行します（ロール付与とメンション送信）"""
    await ctx.send("⏳ 未回答者への即時リマインド処理を実行します...")
    
    guild = ctx.guild
    channel = ctx.channel
    today = datetime.datetime.now(JST).date()
    cfg = load_config()
    unanswered_role_name = cfg.get("roles", {}).get("unanswered_role_name", "未回答者")
    
    role = discord.utils.get(guild.roles, name=unanswered_role_name)
    if not role:
        try:
            role = await guild.create_role(name=unanswered_role_name, color=discord.Color.orange(), reason="リマインド用一時ロール", mentionable=True)
        except Exception as e:
            await ctx.send(f"❌ 「{unanswered_role_name}」ロールの作成に失敗しました: {e}")
            return
    else:
        if not role.mentionable:
            try:
                await role.edit(mentionable=True)
            except Exception as e:
                print(f"Failed to make role mentionable: {e}")

    async with db.pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT u.user_id FROM users u 
            LEFT JOIN attendance a ON u.user_id = a.user_id AND a.target_date = $1 AND a.is_test = FALSE 
            WHERE u.is_tracking = TRUE AND a.user_id IS NULL
        ''', today)
    
    if not rows:
        await ctx.send("✅ 本日の未回答者は一人もいません。")
        return

    has_unanswered = False
    fetched_members = []
    failed_members = []
    
    for row in rows:
        user_id = row['user_id']
        member = guild.get_member(user_id)
        if not member:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                failed_members.append(f"不明なユーザー(ID:{user_id})")
                continue
            except Exception as e:
                failed_members.append(f"フェッチ失敗(ID:{user_id}): {e}")
                continue

        if member:
            try:
                await member.add_roles(role)
                fetched_members.append(member.display_name)
                has_unanswered = True
            except Exception as e:
                failed_members.append(f"{member.display_name} (ロール付与失敗: {e})")

    status_msg = f"📊 **実行結果:**\n"
    if fetched_members:
        status_msg += f"┣ 役職を付与したメンバー: {', '.join(fetched_members)}\n"
    if failed_members:
        status_msg += f"┗ 失敗: {', '.join(failed_members)}\n"
        
    await ctx.send(status_msg)

    if has_unanswered:
        msg_cfg = cfg.get("messages", {})
        remind_title = msg_cfg.get("remind_title", "🔔 **【リマインド】**")
        remind_body = msg_cfg.get("remind_body", "今日の出欠がまだ未回答です！回答をお願いします！")
        await channel.send(
            f"{remind_title}\n"
            f"{role.mention}\n"
            f"{remind_body}"
        )

@bot.command(name="test_remind")
@commands.has_permissions(manage_messages=True)
async def test_remind_command(ctx):
    """【テスト用】自分自身に未回答者ロールを付与してリマインドをテストします"""
    cfg = load_config()
    unanswered_role_name = cfg.get("roles", {}).get("unanswered_role_name", "未回答者")
    await ctx.send(f"⏳ {ctx.author.display_name} さんを対象にリマインドのテストを実行します...")
    
    guild = ctx.guild
    role = discord.utils.get(guild.roles, name=unanswered_role_name)
    if not role:
        try:
            role = await guild.create_role(name=unanswered_role_name, color=discord.Color.orange(), reason="リマインドテスト用", mentionable=True)
            await ctx.send(f"✅ 「{unanswered_role_name}」ロールを作成しました。")
        except Exception as e:
            await ctx.send(f"❌ ロール作成に失敗しました: {e}")
            return

    try:
        await ctx.author.add_roles(role)
        await ctx.send(
            f"🔔 **【テスト・リマインド】**\n"
            f"{role.mention}\n"
            f"これはテスト通知です。ロールへのメンションが届いているか確認してください！"
        )
    except Exception as e:
        await ctx.send(f"❌ ロール付与に失敗しました（Botより高い権限の役職を持っている可能性があります）: {e}")

@bot.command(name="clear_remind")
@commands.has_permissions(manage_messages=True)
async def clear_remind_command(ctx):
    """【管理者用】全員から未回答者ロールを削除します"""
    cfg = load_config()
    unanswered_role_name = cfg.get("roles", {}).get("unanswered_role_name", "未回答者")
    role = discord.utils.get(ctx.guild.roles, name=unanswered_role_name)
    if not role:
        await ctx.send(f"「{unanswered_role_name}」ロールは存在しません。")
        return

    count = 0
    for member in role.members:
        try:
            await member.remove_roles(role)
            count += 1
        except Exception:
            pass
    
    await ctx.send(f"✅ {count} 名から「{unanswered_role_name}」ロールを削除しました。")

@bot.command(name="reload_config")
@commands.has_permissions(manage_messages=True)
async def reload_config_command(ctx):
    """【管理者用】config.yaml 設定ファイルを再読み込みします"""
    try:
        load_config()
        await ctx.send("✅ `config.yaml` を再読み込みしました。")
    except Exception as e:
        await ctx.send(f"❌ 設定ファイルの再読み込みに失敗しました: {e}")

@bot.command(name="forget_me")
async def forget_me_command(ctx):
    """自身の出欠トラッキング（未回答者リストへの表示）を停止します。"""
    user_id = ctx.author.id
    async with db.pool.acquire() as conn:
        await conn.execute('UPDATE users SET is_tracking = FALSE WHERE user_id = $1', user_id)
    await ctx.send(f"👋 {ctx.author.display_name} さんのトラッキングを停止しました。次回以降の集計対象から除外されます。")

@bot.command(name="check")
async def check_command(ctx):
    """本日の出欠回答状況をテキストで簡易確認します"""
    today = datetime.datetime.now(JST).date()
    async with db.pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT u.name, a.status 
            FROM attendance a 
            JOIN users u ON a.user_id = u.user_id 
            WHERE a.target_date = $1 AND a.is_test = FALSE
        ''', today)
        
        missing_rows = await conn.fetch('''
            SELECT name 
            FROM users 
            WHERE is_tracking = TRUE AND name NOT ILIKE 'unknown'
            AND user_id NOT IN (SELECT user_id FROM attendance WHERE target_date = $1 AND is_test = FALSE)
        ''', today)

    msg = f"📊 **本日 ({today}) の回答状況 (テキスト簡易表示)**\n\n"
    if rows:
        msg += "**【回答済み】**\n"
        for r in rows:
            msg += f"・{r['name']}: {r['status']}\n"
    else:
        msg += "まだ誰も回答していません。\n"
        
    if missing_rows:
        msg += "\n**【未回答】**\n"
        for r in missing_rows:
            msg += f"・{r['name']}\n"
            
    await ctx.send(msg)

@bot.command(name="list_events")
async def list_events_command(ctx):
    """登録されているイベント（大会など）の一覧を表示します"""
    today = datetime.datetime.now(JST).date()
    async with db.pool.acquire() as conn:
        await conn.execute('DELETE FROM events WHERE event_date < $1', today)
        rows = await conn.fetch('SELECT name, event_date FROM events ORDER BY event_date ASC')
        
    if not rows:
        await ctx.send("📅 登録されているイベントはありません。")
        return

    msg = "📅 **今後開催予定のイベント一覧**\n"
    for r in rows:
        diff = (r['event_date'] - today).days
        msg += f"・{r['event_date']} : **{r['name']}** (あと {diff} 日)\n"
    await ctx.send(msg)

@bot.command(name="set_event")
@commands.has_permissions(manage_messages=True)
async def set_event_command(ctx, date_str: str, *, event_name: str):
    """イベントを登録します（形式: !set_event YYYY/MM/DD イベント名）"""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y/%m/%d").date()
    except ValueError:
        await ctx.send("❌ 日付の形式が正しくありません。 `YYYY/MM/DD` で指定してください。（例: 2026/08/15 カンファレンス）")
        return
        
    today = datetime.datetime.now(JST).date()
    if dt < today:
        await ctx.send("❌ 過去の日付は登録できません。")
        return

    async with db.pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO events (name, event_date) 
            VALUES ($1, $2)
            ON CONFLICT (name) DO UPDATE SET event_date = EXCLUDED.event_date
        ''', event_name, dt)

    await ctx.send(f"✅ イベント「**{event_name}**」を **{dt}** に登録しました！")

@bot.command(name="delete_event")
@commands.has_permissions(manage_messages=True)
async def delete_event_command(ctx, *, event_name: str):
    """登録済みのイベントを削除します"""
    async with db.pool.acquire() as conn:
        res = await conn.execute('DELETE FROM events WHERE name = $1', event_name)
        
    if res == "DELETE 0":
        await ctx.send(f"❌ イベント「{event_name}」は見つかりませんでした。")
    else:
        await ctx.send(f"🗑️ イベント「**{event_name}**」を削除しました。")

@bot.command(name="set_status")
@commands.has_permissions(manage_messages=True)
async def set_status_command(ctx, member: discord.Member = None, status: str = None):
    """指定したメンバーの本日の出欠を手動で更新します"""
    if member is None or status is None:
        await ctx.send("❌ 形式が正しくありません。 `!set_status @ユーザー 状態` で指定してください。\n(状態例: `3限終わり`, `4限終わり`, `5限終わり`, `出席`, `欠席`)")
        return

    valid_statuses = ["3限終わり", "4限終わり", "5限終わり", "出席", "欠席"]
    if status not in valid_statuses:
        await ctx.send(f"❌ 無効な状態です。選択可能: {', '.join(valid_statuses)}")
        return

    today = datetime.datetime.now(JST).date()
    async with db.pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, name, is_tracking)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name
        ''', member.id, member.display_name)
        
        await conn.execute('''
            INSERT INTO attendance (user_id, target_date, status, is_test)
            VALUES ($1, $2, $3, FALSE)
            ON CONFLICT (user_id, target_date) DO UPDATE SET status = EXCLUDED.status, recorded_at = CURRENT_TIMESTAMP, is_test = FALSE
        ''', member.id, today, status)
        
    await ctx.send(f"✅ {member.display_name} さんの出欠を「**{status}**」に更新しました。")

@bot.group(name="meeting", invoke_without_command=True)
async def meeting_group(ctx):
    """【定例会管理】サブコマンドが指定されない場合、現在の定例会設定一覧を表示します"""
    cfg = load_config()
    meetings = cfg.get("meetings", [])
    if not meetings:
        await ctx.send("📅 登録されている定例会はありません。`config.yaml` に追加してください。")
        return

    msg = "📅 **登録済み定例会設定一覧**\n\n"
    for idx, m in enumerate(meetings, 1):
        status = "🟢 有効" if m.get("enabled", True) else "🔴 無効"
        
        # Format channel info
        ch_ids = m.get("channel_ids") or ([m.get("channel_id")] if m.get("channel_id") else [])
        ch_ids = [c for c in ch_ids if c]
        if ch_ids:
            ch_info = ", ".join(f"<#{c}>" for c in ch_ids)
        else:
            ch_info = "デフォルトチャンネル"

        msg += (
            f"**{m.get('name')}** ({status})\n"
            f"　┣ 通知チャンネル: {ch_info}\n"
            f"　┣ 曜日・時刻: 毎週{m.get('day_of_week')} {m.get('start_time')} (案内投稿: {m.get('announcement_time')})\n"
            f"　┣ 開催場所: {m.get('location')}\n"
            f"　┣ 議題: {m.get('agenda') or 'なし'}\n"
            f"　┗ 連絡事項: {m.get('notice') or 'なし'}\n\n"
        )
    await ctx.send(msg)

@meeting_group.command(name="list")
async def meeting_list_subcommand(ctx):
    """登録されている定例会設定を表示します"""
    await meeting_group(ctx)

@meeting_group.command(name="add")
@commands.has_permissions(manage_messages=True)
async def meeting_add_subcommand(ctx, name: str, day_str: str, start_time_str: str = "18:00", *, location_str: str = "研究棟"):
    """新しい定例会を追加登録します (例: !meeting add 回路班定例会 Thursday 19:00 部室)"""
    day_str_cap = day_str.capitalize()
    if day_str_cap not in DAY_MAP and day_str not in DAY_MAP:
        await ctx.send("❌ 曜日名が正しくありません。(例: Monday, Thursday, 金曜日)")
        return

    target_day = day_str_cap if day_str_cap in DAY_MAP else day_str

    try:
        parts = start_time_str.split(":")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        formatted_start_time = f"{hour:02d}:{minute:02d}"
    except Exception:
        await ctx.send("❌ 時刻の形式が正しくありません。 `HH:MM` で指定してください。(例: 18:00)")
        return

    cfg = load_config()
    meetings = cfg.get("meetings", [])

    # Check duplicate name
    for m in meetings:
        if m.get("name") == name:
            await ctx.send(f"❌ 定例会「{name}」は既に存在します。")
            return

    new_meeting = {
        "name": name,
        "enabled": True,
        "day_of_week": target_day,
        "announcement_time": "08:30",
        "start_time": formatted_start_time,
        "location": location_str,
        "channel_id": ctx.channel.id,
        "role_mention": f"@{name.replace('定例会', '')}",
        "agenda": "進捗確認",
        "notice": "",
        "reactions": {"attend": "🫡", "absent": "🧐"}
    }

    meetings.append(new_meeting)
    cfg["meetings"] = meetings

    if save_config(cfg):
        await ctx.send(f"✅ 定例会「**{name}**」を追加保存しました！\n・毎週{target_day} {formatted_start_time}〜 場所: {location_str}\n・通知チャンネル: <#{ctx.channel.id}>")
    else:
        await ctx.send("❌ 設定の保存に失敗しました。")

@meeting_group.command(name="remove")
@commands.has_permissions(manage_messages=True)
async def meeting_remove_subcommand(ctx, *, name: str):
    """登録されている定例会を削除します (例: !meeting remove 回路班定例会)"""
    cfg = load_config()
    meetings = cfg.get("meetings", [])
    if not meetings:
        await ctx.send("❌ 登録されている定例会はありません。")
        return

    new_meetings = [m for m in meetings if m.get("name") != name]
    if len(new_meetings) == len(meetings):
        await ctx.send(f"❌ 定例会「{name}」は見つかりませんでした。`!meeting list` で登録名を確認してください。")
        return

    cfg["meetings"] = new_meetings
    if save_config(cfg):
        await ctx.send(f"🗑️ 定例会「**{name}**」を削除しました。")
    else:
        await ctx.send("❌ 設定の保存に失敗しました。")

@meeting_group.command(name="send")
@commands.has_permissions(manage_messages=True)
async def meeting_send_subcommand(ctx, *, args: str = ""):
    """今すぐ定例会の案内メッセージ（出欠スタンプ付き）を送信します (末尾に --here または -h で実行チャンネルへテスト送信)"""
    is_here = "--here" in args or "-h" in args
    clean_args = args.replace("--here", "").replace("-h", "").strip()

    cfg = load_config()
    meetings = cfg.get("meetings", [])
    if not meetings:
        await ctx.send("❌ 定例会が設定されていません。")
        return

    meeting = get_target_meeting(meetings, ctx.channel.id, clean_args)
    target_channel_ids = meeting.get("channel_ids") or ([meeting.get("channel_id")] if meeting.get("channel_id") else [])
    target_channel_ids = [c for c in target_channel_ids if c]

    if is_here or not target_channel_ids:
        # Send to current channel for testing
        await send_meeting_announcement(ctx.channel.id, meeting)
    else:
        for ch_id in target_channel_ids:
            await send_meeting_announcement(ch_id, meeting)

def get_target_meeting(meetings, channel_id, args_text=""):
    """Helper to select target meeting by channel_id, explicit index/name in args, or first meeting."""
    # 1. Match by channel_id if configured
    for m in meetings:
        if m.get("channel_id") and m.get("channel_id") == channel_id:
            return m
    # 2. Check if first word of args matches a meeting name
    tokens = args_text.split()
    if tokens:
        for m in meetings:
            if m.get("name") == tokens[0]:
                return m
    # 3. Default to first meeting
    return meetings[0] if meetings else None

@meeting_group.command(name="location")
@commands.has_permissions(manage_messages=True)
async def meeting_location_subcommand(ctx, *, args: str):
    """開催場所を変更します (通常は次回のみ一時変更、末尾に --save または -s を付けると恒久保存)"""
    is_save = "--save" in args or "-s" in args
    clean_args = args.replace("--save", "").replace("-s", "").strip()

    cfg = load_config()
    meetings = cfg.get("meetings", [])
    if not meetings:
        await ctx.send("❌ 定例会が設定されていません。")
        return

    meeting = get_target_meeting(meetings, ctx.channel.id, clean_args)
    # Remove meeting name token if supplied
    tokens = clean_args.split()
    if tokens and tokens[0] == meeting.get("name"):
        location_str = " ".join(tokens[1:]).strip()
    else:
        location_str = clean_args

    if not location_str:
        await ctx.send("❌ 開催場所を指定してください。(例: `!meeting location 部室`)")
        return

    name = meeting.get("name", "定例会")
    if is_save:
        meeting["location"] = location_str
        if "temp_location" in meeting:
            del meeting["temp_location"]
        if save_config(cfg):
            await ctx.send(f"💾 「**{name}**」の開催場所を 「**{location_str}**」 に**永続保存**しました！")
        else:
            await ctx.send("❌ 設定の保存に失敗しました。")
    else:
        meeting["temp_location"] = location_str
        if save_config(cfg):
            await ctx.send(f"⏱️ 「**{name}**」の次回開催場所を 「**{location_str}**」 に**一時変更**しました！（次回送信後に自動リセット）")
        else:
            await ctx.send("❌ 設定の保存に失敗しました。")

@meeting_group.command(name="agenda")
@commands.has_permissions(manage_messages=True)
async def meeting_agenda_subcommand(ctx, *, args: str):
    """議題を変更します (通常は次回のみ一時変更、末尾に --save または -s を付けると恒久保存)"""
    is_save = "--save" in args or "-s" in args
    clean_args = args.replace("--save", "").replace("-s", "").strip()

    cfg = load_config()
    meetings = cfg.get("meetings", [])
    if not meetings:
        await ctx.send("❌ 定例会が設定されていません。")
        return

    meeting = get_target_meeting(meetings, ctx.channel.id, clean_args)
    tokens = clean_args.split()
    if tokens and tokens[0] == meeting.get("name"):
        agenda_str = " ".join(tokens[1:]).strip()
    else:
        agenda_str = clean_args

    formatted_agenda = agenda_str.replace("、", "\n").replace(",", "\n")
    name = meeting.get("name", "定例会")
    if is_save:
        meeting["agenda"] = formatted_agenda
        if "temp_agenda" in meeting:
            del meeting["temp_agenda"]
        if save_config(cfg):
            await ctx.send(f"💾 「**{name}**」の次回以降の議題を以下のように**永続保存**しました:\n```\n{formatted_agenda}\n```")
        else:
            await ctx.send("❌ 設定の保存に失敗しました。")
    else:
        meeting["temp_agenda"] = formatted_agenda
        if save_config(cfg):
            await ctx.send(f"⏱️ 「**{name}**」の次回議題を以下のように**一時変更**しました！（次回送信後に自動リセット）:\n```\n{formatted_agenda}\n```")
        else:
            await ctx.send("❌ 設定の保存に失敗しました。")

@meeting_group.command(name="notice")
@commands.has_permissions(manage_messages=True)
async def meeting_notice_subcommand(ctx, *, args: str):
    """連絡事項を変更します (通常は次回のみ一時変更、末尾に --save または -s を付けると恒久保存)"""
    is_save = "--save" in args or "-s" in args
    clean_args = args.replace("--save", "").replace("-s", "").strip()

    cfg = load_config()
    meetings = cfg.get("meetings", [])
    if not meetings:
        await ctx.send("❌ 定例会が設定されていません。")
        return

    meeting = get_target_meeting(meetings, ctx.channel.id, clean_args)
    tokens = clean_args.split()
    if tokens and tokens[0] == meeting.get("name"):
        notice_str = " ".join(tokens[1:]).strip()
    else:
        notice_str = clean_args

    name = meeting.get("name", "定例会")
    if is_save:
        meeting["notice"] = notice_str
        if "temp_notice" in meeting:
            del meeting["temp_notice"]
        if save_config(cfg):
            await ctx.send(f"💾 「**{name}**」の次回以降の連絡事項を以下のように**永続保存**しました:\n```\n{notice_str}\n```")
        else:
            await ctx.send("❌ 設定の保存に失敗しました。")
    else:
        meeting["temp_notice"] = notice_str
        if save_config(cfg):
            await ctx.send(f"⏱️ 「**{name}**」の次回連絡事項を以下のように**一時変更**しました！（次回送信後に自動リセット）:\n```\n{notice_str}\n```")
        else:
            await ctx.send("❌ 設定の保存に失敗しました。")

@meeting_group.command(name="day")
@commands.has_permissions(manage_messages=True)
async def meeting_day_subcommand(ctx, *, args: str):
    """開催曜日を変更します (例: !meeting day Friday, 末尾に --save または -s で恒久保存)"""
    is_save = "--save" in args or "-s" in args
    clean_args = args.replace("--save", "").replace("-s", "").strip()
    
    cfg = load_config()
    meetings = cfg.get("meetings", [])
    if not meetings:
        await ctx.send("❌ 定例会が設定されていません。")
        return

    meeting = get_target_meeting(meetings, ctx.channel.id, clean_args)
    tokens = clean_args.split()
    if len(tokens) >= 2 and tokens[0] == meeting.get("name"):
        day_str = tokens[1]
    else:
        day_str = tokens[0] if tokens else ""

    day_str_cap = day_str.capitalize()
    if day_str_cap not in DAY_MAP and day_str not in DAY_MAP:
        await ctx.send("❌ 曜日名が正しくありません。(例: Friday, 金曜日)")
        return

    target_day = day_str_cap if day_str_cap in DAY_MAP else day_str
    name = meeting.get("name", "定例会")

    if is_save:
        meeting["day_of_week"] = target_day
        if save_config(cfg):
            await ctx.send(f"💾 「**{name}**」の開催曜日を **{target_day}** に**永続保存**しました！")
        else:
            await ctx.send("❌ 設定の保存に失敗しました。")
    else:
        meeting["day_of_week"] = target_day
        if save_config(cfg):
            await ctx.send(f"⏱️ 「**{name}**」の次回開催曜日を **{target_day}** に変更しました！")
        else:
            await ctx.send("❌ 設定の保存に失敗しました。")

@meeting_group.command(name="time")
@commands.has_permissions(manage_messages=True)
async def meeting_time_subcommand(ctx, *, args: str):
    """開始時刻を変更します (例: !meeting time 18:00, 末尾に --save または -s で恒久保存)"""
    is_save = "--save" in args or "-s" in args
    clean_args = args.replace("--save", "").replace("-s", "").strip()

    cfg = load_config()
    meetings = cfg.get("meetings", [])
    if not meetings:
        await ctx.send("❌ 定例会が設定されていません。")
        return

    meeting = get_target_meeting(meetings, ctx.channel.id, clean_args)
    tokens = clean_args.split()
    if len(tokens) >= 2 and tokens[0] == meeting.get("name"):
        time_str = tokens[1]
    else:
        time_str = tokens[0] if tokens else ""

    try:
        parts = time_str.split(":")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        formatted_time = f"{hour:02d}:{minute:02d}"
    except Exception:
        await ctx.send("❌ 時刻の形式が正しくありません。 `HH:MM` で指定してください。(例: 18:00)")
        return

    name = meeting.get("name", "定例会")
    if is_save:
        meeting["start_time"] = formatted_time
        if "temp_start_time" in meeting:
            del meeting["temp_start_time"]
        if save_config(cfg):
            await ctx.send(f"💾 「**{name}**」の開始時間を **{formatted_time}** に**永続保存**しました！")
        else:
            await ctx.send("❌ 設定の保存に失敗しました。")
    else:
        meeting["temp_start_time"] = formatted_time
        if save_config(cfg):
            await ctx.send(f"⏱️ 「**{name}**」の次回開始時間を **{formatted_time}** に**一時変更**しました！（次回送信後に自動リセット）")
        else:
            await ctx.send("❌ 設定の保存に失敗しました。")

@meeting_group.command(name="channel")
@commands.has_permissions(manage_messages=True)
async def meeting_channel_subcommand(ctx, *, args: str = ""):
    """定例会の通知チャンネルを変更します (例: !meeting channel #制御班チャンネル または コマンドを実行したチャンネルに設定)"""
    cfg = load_config()
    meetings = cfg.get("meetings", [])
    if not meetings:
        await ctx.send("❌ 定例会が設定されていません。")
        return

    meeting = get_target_meeting(meetings, ctx.channel.id, args)
    
    # Check if a channel mention (#channel) or ID is provided
    target_channels = []
    if ctx.message.channel_mentions:
        target_channels = ctx.message.channel_mentions
    else:
        tokens = args.split()
        for tok in tokens:
            if tok.isdigit():
                ch = ctx.guild.get_channel(int(tok))
                if ch:
                    target_channels.append(ch)

    if not target_channels:
        target_channels = [ctx.channel]

    if len(target_channels) == 1:
        meeting["channel_id"] = target_channels[0].id
        if "channel_ids" in meeting:
            del meeting["channel_ids"]
        ch_text = f"<#{target_channels[0].id}>"
    else:
        meeting["channel_ids"] = [ch.id for ch in target_channels]
        meeting["channel_id"] = target_channels[0].id
        ch_text = ", ".join(f"<#{ch.id}>" for ch in target_channels)

    name = meeting.get("name", "定例会")

    if save_config(cfg):
        await ctx.send(f"✅ 「**{name}**」の通知チャンネルを {ch_text} に変更・保存しました！")
    else:
        await ctx.send("❌ 設定の保存に失敗しました。")

@bot.command(name="status")
async def status_command(ctx):
    """自動配信タスクの稼働状況を確認します"""
    send_status = "🟢 稼働中" if send_attendance_check.is_running() else "🔴 停止中"
    remind_status = "🟢 稼働中" if remind_unanswered.is_running() else "🔴 停止中"
    agg_status = "🟢 稼働中" if aggregate_attendance.is_running() else "🔴 停止中"
    mtg_status = "🟢 稼働中" if check_meeting_schedule.is_running() else "🔴 停止中"
    
    await ctx.send(
        f"⚙️ **自動配信タスクの稼働状況**\n"
        f"・08:00 出欠確認フォーム送信 : {send_status}\n"
        f"・12:00 未回答者リマインド : {remind_status}\n"
        f"・12:30 集計結果送信 : {agg_status}\n"
        f"・定例会リマインダー : {mtg_status}"
    )

@bot.command(name="ping")
async def ping_command(ctx):
    """Botの応答速度を確認します"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! (応答時間: {latency}ms)")

@bot.command(name="db_info")
@commands.has_permissions(manage_messages=True)
async def db_info_command(ctx):
    """DBの各種統計情報を表示します"""
    async with db.pool.acquire() as conn:
        users_count = await conn.fetchval('SELECT COUNT(*) FROM users')
        tracking_count = await conn.fetchval('SELECT COUNT(*) FROM users WHERE is_tracking = TRUE')
        attendance_count = await conn.fetchval('SELECT COUNT(*) FROM attendance')
        events_count = await conn.fetchval('SELECT COUNT(*) FROM events')

    await ctx.send(
        f"📊 **データベース統計情報**\n"
        f"・総登録ユーザー数 : {users_count} 名\n"
        f"・アクティブ追跡対象 : {tracking_count} 名\n"
        f"・累計出欠記録数 : {attendance_count} 件\n"
        f"・登録済みイベント数 : {events_count} 件"
    )

@bot.command(name="clear_tests")
@commands.has_permissions(manage_messages=True)
async def clear_tests_command(ctx):
    """【管理者用】DB内のすべてのテストデータを削除します"""
    async with db.pool.acquire() as conn:
        res = await conn.execute('DELETE FROM attendance WHERE is_test = TRUE')
        
    await ctx.send(f"🧹 テスト用出欠レコードを削除しました ({res})。")

@bot.command(name="list_members")
async def list_members_command(ctx):
    """登録されているメンバー一覧を表示します"""
    async with db.pool.acquire() as conn:
        rows = await conn.fetch('SELECT user_id, name, is_main, is_tracking FROM users ORDER BY is_main DESC, name ASC')

    if not rows:
        await ctx.send("👥 登録されているメンバーはいません。")
        return

    msg = "👥 **登録メンバー一覧**\n"
    for r in rows:
        main_tag = "⭐ (M)" if r['is_main'] else "　"
        status_tag = "🟢 追跡中" if r['is_tracking'] else "⚪ 停止中"
        msg += f"・{main_tag} **{r['name']}** (ID: `{r['user_id']}`) - {status_tag}\n"
    await ctx.send(msg)

@bot.command(name="add_member")
@commands.has_permissions(manage_messages=True)
async def add_member_command(ctx, member: discord.Member = None):
    """指定したメンバーをリストに追加（追跡再開）します。"""
    if member is None:
        await ctx.send("❌ 追加したいメンバーをメンションしてください。")
        return

    async with db.pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, name, is_tracking)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (user_id) DO UPDATE SET is_tracking = TRUE, name = EXCLUDED.name
        ''', member.id, member.display_name)
        
    await ctx.send(f"✅ {member.display_name} さんをトラッキング対象に追加しました！")

@bot.command(name="set_main")
@commands.has_permissions(manage_messages=True)
async def set_main_command(ctx, member: discord.Member = None):
    """指定したメンバーをメインメンバー (M) に設定します。"""
    if member is None:
        await ctx.send("❌ 設定したいメンバーをメンションしてください。")
        return

    async with db.pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, name, is_main, is_tracking)
            VALUES ($1, $2, TRUE, TRUE)
            ON CONFLICT (user_id) DO UPDATE SET is_main = TRUE, is_tracking = TRUE, name = EXCLUDED.name
        ''', member.id, member.display_name)
        
    await ctx.send(f"⭐ {member.display_name} さんをメインメンバーに設定しました！")

@bot.command(name="remove_member")
@commands.has_permissions(manage_messages=True)
async def remove_member_command(ctx, member: discord.Member = None):
    """指定したメンバーをリストから削除（トラッキング停止）します。"""
    if member is None:
        await ctx.send("❌ 削除したいメンバーをメンションしてください。")
        return

    async with db.pool.acquire() as conn:
        await conn.execute('UPDATE users SET is_tracking = FALSE WHERE user_id = $1', member.id)
        
    await ctx.send(f"🗑️ {member.display_name} さんのトラッキングを停止しました。")

@bot.command(name="help")
async def help_command(ctx):
    """コマンド一覧を表示します"""
    cfg = load_config()
    prefix = cfg.get("bot", {}).get("command_prefix", "!")
    help_text = (
        "**📋 出欠確認Bot コマンド一覧**\n\n"
        "👤 **メンバー管理**\n"
        f"┣ `{prefix}list_members` : 登録されているメンバー一覧を表示\n"
        f"┣ `{prefix}add_member @ユーザー` : 指定した人をトラッキング対象に追加\n"
        f"┣ `{prefix}remove_member @ユーザー` : トラッキングを停止\n"
        f"┣ `{prefix}set_main @ユーザー` : メインメンバー(M)に設定\n"
        f"┗ `{prefix}forget_me` : 自分のデータをすべて削除して脱退\n\n"
        "🗓️ **出欠・イベント・定例会**\n"
        f"┣ `{prefix}check` : 本日の回答状況をテキストで確認\n"
        f"┣ `{prefix}list_events` : 登録されているイベント（大会など）を表示\n"
        f"┣ `{prefix}set_event YYYY/MM/DD 名前` : イベントを登録\n"
        f"┣ `{prefix}delete_event 名前` : イベントを削除\n"
        f"┗ `{prefix}meeting` : 定例会設定管理コマンドグループ\n"
        f"　 ┣ `{prefix}meeting list` : 設定一覧を表示\n"
        f"　 ┣ `{prefix}meeting add <名前> <曜日> [時間] [場所]` : 新しい定例会を追加登録\n"
        f"　 ┣ `{prefix}meeting remove <名前>` : 定例会を削除\n"
        f"　 ┣ `{prefix}meeting channel [名前] [#チャンネル]` : 通知先チャンネルを変更\n"
        f"　 ┣ `{prefix}meeting location [名前] <場所> [--save]` : 場所変更 (通常:次回のみ一時変更 / `--save`:永続保存)\n"
        f"　 ┣ `{prefix}meeting agenda [名前] <議題> [--save]` : 議題変更 (通常:次回のみ一時変更 / `--save`:永続保存)\n"
        f"　 ┣ `{prefix}meeting notice [名前] <連絡事項> [--save]` : 連絡事項変更 (通常:次回のみ一時変更 / `--save`:永続保存)\n"
        f"　 ┣ `{prefix}meeting day [名前] <曜日> [--save]` : 曜日変更 (通常:次回のみ一時変更 / `--save`:永続保存)\n"
        f"　 ┣ `{prefix}meeting time [名前] <時間> [--save]` : 時間変更 (通常:次回のみ一時変更 / `--save`:永続保存)\n"
        f"　 ┗ `{prefix}meeting send [番号]` : 定例会案内を今すぐ手動投稿\n\n"
        "⚙️ **管理者・デバッグ用**\n"
        f"┣ `{prefix}set_status @ユーザー 状態` : 指定した人の出欠を手動で修正\n"
        "┃　 ※状態: `3限終わり`, `4限終わり`, `5限終わり`, `出席`, `欠席` \n"
        f"┣ `{prefix}send_now` : 今すぐ本番用の出欠フォームを送信\n"
        f"┣ `{prefix}aggregate_now` : 今すぐ本番用の集計結果を送信\n"
        f"┣ `{prefix}remind_now` : 今すぐ本番用の未回答者リマインドを実行\n"
        f"┣ `{prefix}reload_config` : config.yaml設定ファイルを即時再読み込み\n"
        f"┣ `{prefix}status` : 自動配信の稼働状況を確認\n"
        f"┣ `{prefix}ping` : 応答確認\n"
        f"┣ `{prefix}db_info` : DB統計情報の表示\n"
        f"┣ `{prefix}test_send` : テスト用フォーム送信\n"
        f"┣ `{prefix}test_aggregate` : テスト用集計結果送信\n"
        f"┣ `{prefix}test_remind` : 未回答者リマインドのテスト実行\n"
        f"┣ `{prefix}clear_remind` : 未回答者ロールを全員から削除\n"
        f"┗ `{prefix}clear_tests` : DB内のテストデータを一括削除\n\n"

        "💡 **自動配信スケジュール**\n"
        f"・{schedule_cfg.get('send_check_time', '08:00')} : 出欠確認フォーム送信\n"
        f"・{schedule_cfg.get('remind_unanswered_time', '12:00')} : 未回答者へのメンションと一時ロール付与\n"
        f"・{schedule_cfg.get('aggregate_summary_time', '12:30')} : 本日の出欠集計結果を送信 (一時ロールを自動削除)\n\n"
        "⚠️ *ボタンで回答できない場合は、このチャンネルで直接連絡してください。*"
    )
    await ctx.send(help_text)

if __name__ == '__main__':
    if TOKEN is None or CHANNEL_ID is None:
        print("Error: DISCORD_TOKEN or CHANNEL_ID is not set.")
    else:
        bot.run(TOKEN)
