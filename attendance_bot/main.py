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
from views import AttendanceView
from image_generator import create_summary_image

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

# Intents configuration
intents = discord.Intents.default()
intents.message_content = True

# Bot initialization
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Timezone setting (JST)
JST = datetime.timezone(datetime.timedelta(hours=9), 'JST')

# Scheduled times
time_8am = datetime.time(hour=8, minute=0, tzinfo=JST)
time_12pm = datetime.time(hour=12, minute=0, tzinfo=JST)
time_1230pm = datetime.time(hour=12, minute=30, tzinfo=JST)

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
    
    view = AttendanceView(is_test=is_test, is_saturday=is_saturday)
    prefix = "【テスト】\n" if is_test else ""
    countdown_text = await get_events_countdown_text()
    
    mention_text = ""
    if hasattr(channel, "guild") and channel.guild:
        role = discord.utils.get(channel.guild.roles, name="ROX-2026")
        if role:
            if is_test:
                mention_text = "`@ROX-2026` (テスト用表示)\n"
            else:
                mention_text = f"{role.mention}\n"
        else:
            mention_text = "@ROX-2026\n"
    else:
        mention_text = "@ROX-2026\n"
        
    question = "会議に参加しますか？" if is_saturday else "今日の活動に参加しますか？"
    note = "\n\n⚠️ **回答できない場合や「未回答」に残る場合は、このチャンネルで連絡してください！**"
    
    await channel.send(
        f"{prefix}{mention_text}{countdown_text}{question}{note}",
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
            categories["未回答者"].append(name)

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
    """Mention and grant a temporary role to users who haven't responded by 12:00 PM."""
    trigger_date = datetime.datetime.now(JST).date()
    
    while True:
        if datetime.datetime.now(JST).date() != trigger_date:
            return

        try:
            channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
            if not channel:
                await asyncio.sleep(60)
                continue

            guild = channel.guild
            role = discord.utils.get(guild.roles, name="未回答者")
            if not role:
                try:
                    role = await guild.create_role(name="未回答者", color=discord.Color.orange(), reason="リマインド用一時ロール", mentionable=True)
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
                    try:
                        await member.add_roles(role)
                        has_unanswered = True
                    except Exception as e:
                        print(f"Failed to add role to {member.display_name}: {e}")

            if has_unanswered:
                await channel.send(
                    f"🔔 **【リマインド】**\n"
                    f"{role.mention}\n"
                    f"今日の出欠がまだ未回答です！回答をお願いします！"
                )
            return

        except Exception as e:
            print(f"Remind unanswered: Waiting for network... ({e})")
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
                
                role = discord.utils.get(channel.guild.roles, name="未回答者")
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
    
    role = discord.utils.get(guild.roles, name="未回答者")
    if not role:
        try:
            role = await guild.create_role(name="未回答者", color=discord.Color.orange(), reason="リマインド用一時ロール", mentionable=True)
        except Exception as e:
            await ctx.send(f"❌ 「未回答者」ロールの作成に失敗しました: {e}")
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
        await channel.send(
            f"🔔 **【リマインド】**\n"
            f"{role.mention}\n"
            f"今日の出欠がまだ未回答です！回答をお願いします！"
        )

@bot.command(name="test_remind")
@commands.has_permissions(manage_messages=True)
async def test_remind_command(ctx):
    """【テスト用】自分自身に「未回答者」ロールを付与してリマインドをテストします"""
    await ctx.send(f"⏳ {ctx.author.display_name} さんを対象にリマインドのテストを実行します...")
    
    guild = ctx.guild
    role = discord.utils.get(guild.roles, name="未回答者")
    if not role:
        try:
            role = await guild.create_role(name="未回答者", color=discord.Color.orange(), reason="リマインドテスト用", mentionable=True)
            await ctx.send("✅ 「未回答者」ロールを作成しました。")
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
    """【管理者用】全員から「未回答者」ロールを削除します"""
    role = discord.utils.get(ctx.guild.roles, name="未回答者")
    if not role:
        await ctx.send("「未回答者」ロールは存在しません。")
        return

    count = 0
    for member in role.members:
        try:
            await member.remove_roles(role)
            count += 1
        except Exception:
            pass
    
    await ctx.send(f"✅ {count} 名から「未回答者」ロールを削除しました。")

@bot.command(name="clear_tests")
async def clear_tests_command(ctx):
    """DB内のすべてのテストデータを削除します"""
    async with db.pool.acquire() as conn:
        result = await conn.execute('DELETE FROM attendance WHERE is_test = TRUE')
        count = result.split(" ")[1]
    await ctx.send(f"🗑️ {count} 件のテストデータを削除しました。")

@bot.command(name="check")
async def check_command(ctx):
    """【確認用】本日の回答状況をテキストで表示します"""
    today = datetime.datetime.now(JST).date()
    
    async with db.pool.acquire() as conn:
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

@bot.command(name="set_status")
@commands.has_permissions(manage_messages=True)
async def set_status_command(ctx, member: discord.Member, status: str):
    """【管理者用】指定したユーザーの本日の出欠ステータスを手動で設定します
    例: !set_status @ユーザー 欠席
    """
    allowed_statuses = ["3限終わり", "4限終わり", "5限終わり", "出席", "欠席"]
    if status not in allowed_statuses:
        await ctx.send(f"❌ 無効なステータスです。以下から選択してください:\n`{', '.join(allowed_statuses)}`")
        return

    today = datetime.datetime.now(JST).date()
    async with db.pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, name) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name
        ''', member.id, member.display_name)
        
        await conn.execute('''
            INSERT INTO attendance (user_id, target_date, status, is_test)
            VALUES ($1, $2, $3, FALSE)
            ON CONFLICT (user_id, target_date) DO UPDATE SET status = EXCLUDED.status
        ''', member.id, today, status)
        
    await ctx.send(f"✅ {member.display_name} さんの本日のステータスを **{status}** に設定しました。")

@bot.command(name="db_info")
async def db_info_command(ctx):
    """【管理者用】DBの統計情報を表示します"""
    async with db.pool.acquire() as conn:
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
    if ctx.author.id != 1082889857052983366:
        await ctx.send("❌ このコマンドを実行する権限がありません。")
        return

    async with db.pool.acquire() as conn:
        try:
            if query.strip().lower().startswith("select"):
                rows = await conn.fetch(query)
                if not rows:
                    await ctx.send("結果は0件でした。")
                    return
                
                headers = rows[0].keys()
                header_line = " | ".join(headers)
                lines = [header_line, "-" * len(header_line)]
                for row in rows[:10]:
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
    if not remind_unanswered.is_running():
        remind_unanswered.start()
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
        event_date = datetime.datetime.strptime(date_str, "%Y/%m/%d").date()
        today = datetime.datetime.now(JST).date()
        
        if event_date < today:
            await ctx.send("❌ 過去の日付は登録できません。今日以降の日付を指定してください。")
            return

        async with db.pool.acquire() as conn:
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
    async with db.pool.acquire() as conn:
        result = await conn.execute('DELETE FROM events WHERE name = $1', event_name)
        
    if result == "DELETE 1":
        await ctx.send(f"🗑️ イベント「{event_name}」を削除しました。")
    else:
        await ctx.send(f"❌ イベント「{event_name}」は見つかりませんでした。")

@bot.command(name="list_events")
async def list_events_command(ctx):
    """登録されているイベントの一覧を表示します"""
    async with db.pool.acquire() as conn:
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
    async with db.pool.acquire() as conn:
        result = await conn.execute('UPDATE users SET is_tracking = FALSE WHERE user_id = $1', user_id)
        
    if result == "UPDATE 1":
        await ctx.send(f"👋 {ctx.author.display_name} さんのトラッキングを停止しました。")
    else:
        await ctx.send("あなたは現在トラッキングされていません。")

@bot.command(name="list_members")
async def list_members_command(ctx):
    """登録されているメンバーの一覧を表示します"""
    async with db.pool.acquire() as conn:
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

    async with db.pool.acquire() as conn:
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

    async with db.pool.acquire() as conn:
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

    async with db.pool.acquire() as conn:
        await conn.execute('UPDATE users SET is_tracking = FALSE WHERE user_id = $1', member.id)
        
    await ctx.send(f"🗑️ {member.display_name} さんのトラッキングを停止しました。")

@bot.command(name="help")
async def help_command(ctx):
    """コマンド一覧を表示します"""
    help_text = (
        "**📋 出欠確認Bot コマンド一覧**\n\n"
        "👤 **メンバー管理**\n"
        "┣ `!list_members` : 登録されているメンバー一覧を表示\n"
        "┣ `!add_member @ユーザー` : 指定した人をトラッキング対象に追加\n"
        "┣ `!remove_member @ユーザー` : トラッキングを停止\n"
        "┣ `!set_main @ユーザー` : メインメンバー(M)に設定\n"
        "┗ `!forget_me` : 自分のデータをすべて削除して脱退\n\n"
        "🗓️ **出欠・イベント**\n"
        "┣ `!check` : 本日の回答状況をテキストで確認\n"
        "┣ `!list_events` : 登録されているイベント（大会など）を表示\n"
        "┣ `!set_event YYYY/MM/DD 名前` : イベントを登録\n"
        "┗ `!delete_event 名前` : イベントを削除\n\n"
        "⚙️ **管理者・デバッグ用**\n"
        "┣ `!set_status @ユーザー 状態` : 指定した人の出欠を手動で修正\n"
        "┃　 ※状態: `3限終わり`, `4限終わり`, `5限終わり`, `出席`, `欠席` \n"
        "┣ `!send_now` : 今すぐ本番用の出欠フォームを送信\n"
        "┣ `!aggregate_now` : 今すぐ本番用の集計結果を送信\n"
        "┣ `!remind_now` : 今すぐ本番用の未回答者リマインドを実行\n"
        "┣ `!status` : 自動配信の稼働状況を確認\n"
        "┣ `!ping` : 応答確認\n"
        "┣ `!db_info` : DB統計情報の表示\n"
        "┣ `!test_send` : テスト用フォーム送信\n"
        "┣ `!test_aggregate` : テスト用集計結果送信\n"
        "┣ `!test_remind` : 未回答者リマインドのテスト実行\n"
        "┣ `!clear_remind` : 未回答者ロールを全員から削除\n"
        "┗ `!clear_tests` : DB内のテストデータを一括削除\n\n"

        "💡 **自動配信スケジュール**\n"
        "・08:00 : 出欠確認フォーム送信 (ネット未接続時は回復まで待機)\n"
        "・12:00 : 未回答者へのメンションと一時ロール付与\n"
        "・12:30 : 本日の出欠集計結果を送信 (一時ロールを自動削除)\n\n"
        "⚠️ *ボタンで回答できない場合は、このチャンネルで直接連絡してください。*"
    )
    await ctx.send(help_text)

if __name__ == '__main__':
    if TOKEN is None or CHANNEL_ID is None:
        print("Error: DISCORD_TOKEN or CHANNEL_ID is not set in the .env file.")
    else:
        bot.run(TOKEN)
