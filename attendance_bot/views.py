import datetime
import discord
from discord.ui import View, Modal, TextInput, Select
import db
from config import load_config

JST = datetime.timezone(datetime.timedelta(hours=9), 'JST')

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
        config = load_config()
        unanswered_role_name = config.get("roles", {}).get("unanswered_role_name", "未回答者")
        
        async with db.pool.acquire() as conn:
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
            
        # Try to remove unanswered role if it exists
        if not self.is_test and interaction.guild:
            role = discord.utils.get(interaction.guild.roles, name=unanswered_role_name)
            if role and role in interaction.user.roles:
                try:
                    await interaction.user.remove_roles(role)
                except Exception:
                    pass

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


class MeetingAnnouncementModal(Modal):
    def __init__(self, meeting_info: dict, target_channel_id: int, selected_location: str):
        title = f"{meeting_info.get('name', '定例会')} 告知内容入力"
        super().__init__(title=title[:45])
        self.meeting_info = meeting_info
        self.target_channel_id = target_channel_id
        self.selected_location = selected_location

        default_time = meeting_info.get("time", "18:00")

        self.time_input = TextInput(
            label="開始時間",
            style=discord.TextStyle.short,
            default=f"18時",
            required=True,
            max_length=20
        )
        self.agenda_input = TextInput(
            label="＜議題＞ (改行区切りで入力)",
            style=discord.TextStyle.paragraph,
            placeholder="進捗確認\nROXへの見学参加希望",
            required=False,
            max_length=1000
        )
        self.notice_input = TextInput(
            label="＜連絡・連絡事項＞ (任意)",
            style=discord.TextStyle.paragraph,
            placeholder="Dockerfileとdocker-compose.ymlの変更をmainより取り込んでほしい",
            required=False,
            max_length=1000
        )

        self.add_item(self.time_input)
        self.add_item(self.agenda_input)
        self.add_item(self.notice_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        name = self.meeting_info.get("name", "定例会")
        mention = self.meeting_info.get("role_mention", "@制御班")
        reactions = self.meeting_info.get("reactions", {"attend": "🫡", "absent": "🧐"})
        attend_emoji = reactions.get("attend", "🫡")
        absent_emoji = reactions.get("absent", "🧐")

        if interaction.guild and mention.startswith("@"):
            role = discord.utils.get(interaction.guild.roles, name=mention[1:])
            if role:
                mention = role.mention

        # Build message string
        today_str = datetime.datetime.now(JST).strftime("%m/%d")
        lines = [
            f"{mention} 💻",
            f"{today_str}の{name}についてです．",
            f"予定通り{self.time_input.value}より{self.selected_location}にて行います．"
        ]

        if self.agenda_input.value.strip():
            lines.append("＜議題＞")
            lines.append(self.agenda_input.value.strip())

        if self.notice_input.value.strip():
            lines.append("＜連絡＞")
            lines.append(self.notice_input.value.strip())

        lines.append(f"参加する人は{attend_emoji} ，参加しない人は{absent_emoji} のリアクションお願いします．")

        announcement_text = "\n".join(lines)

        channel = interaction.client.get_channel(self.target_channel_id) or await interaction.client.fetch_channel(self.target_channel_id)
        if channel:
            msg = await channel.send(announcement_text)
            try:
                await msg.add_reaction(attend_emoji)
                await msg.add_reaction(absent_emoji)
            except Exception as e:
                print(f"Failed to add reactions: {e}")
            await interaction.followup.send("✅ 定例会の告知メッセージを送信しました！", ephemeral=True)
        else:
            await interaction.followup.send("❌ 告知先のチャンネルが見つかりませんでした。", ephemeral=True)


class LocationSelectView(View):
    def __init__(self, meeting_info: dict, target_channel_id: int):
        super().__init__(timeout=60)
        self.meeting_info = meeting_info
        self.target_channel_id = target_channel_id

    @discord.ui.button(label="🏫 部室", style=discord.ButtonStyle.primary, custom_id="btn_loc_bushitsu")
    async def btn_bushitsu(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = MeetingAnnouncementModal(self.meeting_info, self.target_channel_id, selected_location="部室")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🏢 研究棟", style=discord.ButtonStyle.success, custom_id="btn_loc_kenkyuto")
    async def btn_kenkyuto(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = MeetingAnnouncementModal(self.meeting_info, self.target_channel_id, selected_location="研究棟")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="✏️ その他・入力する", style=discord.ButtonStyle.secondary, custom_id="btn_loc_other")
    async def btn_other(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = MeetingAnnouncementModal(self.meeting_info, self.target_channel_id, selected_location="指定の場所")
        await interaction.response.send_modal(modal)


class MeetingPromptView(View):
    def __init__(self, meeting_info: dict, target_channel_id: int):
        super().__init__(timeout=None)
        self.meeting_info = meeting_info
        self.target_channel_id = target_channel_id

    @discord.ui.button(label="📝 定例会告知を作成・送信する", style=discord.ButtonStyle.success, custom_id="btn_create_meeting_announcement")
    async def btn_create(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LocationSelectView(self.meeting_info, self.target_channel_id)
        await interaction.response.send_message("📍 **開催場所を選択してください:**", view=view, ephemeral=True)
