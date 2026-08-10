import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yaml

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# 設定ファイルの読み込み
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

config = load_config()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id}) - utils_bot")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # 画像転送機能の判定
    current_config = load_config()
    forwarding_cfg = current_config.get("image_forwarding", {})
    
    if forwarding_cfg.get("enabled", False):
        rules = forwarding_cfg.get("rules", [])
        for rule in rules:
            target_id = rule.get("target_channel_id")
            if not target_id:
                continue

            # source_channel_ids (リスト) または source_channel_id (単一ID/互換用) の両方に対応
            sources = rule.get("source_channel_ids") or []
            if isinstance(sources, (int, str)):
                sources = [sources]
            if "source_channel_id" in rule and rule["source_channel_id"]:
                sources.append(rule["source_channel_id"])
            
            source_ids = [int(s) for s in sources if s]

            if message.channel.id in source_ids:
                target_channel = bot.get_channel(int(target_id)) or await bot.fetch_channel(int(target_id))
                if target_channel:
                    # 添付メディア（画像・動画）ファイルチェック
                    for attachment in message.attachments:
                        is_media = False
                        if attachment.content_type:
                            is_media = attachment.content_type.startswith(("image/", "video/"))
                        else:
                            ext = os.path.splitext(attachment.filename)[1].lower()
                            is_media = ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".avi", ".webm", ".mkv"]

                        if is_media:
                            file = await attachment.to_file()
                            await target_channel.send(file=file)

    await bot.process_commands(message)

@bot.command(name="ping")
async def ping_command(ctx):
    """Botの生存確認用コマンド"""
    await ctx.send("pong! 🏓 utils_bot is active.")

if __name__ == "__main__":
    if not TOKEN:
        print("エラー: .env に DISCORD_TOKEN が設定されていません。")
    else:
        bot.run(TOKEN)
