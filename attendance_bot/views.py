import datetime
import discord
from discord.ui import View
import db

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
            
        # Try to remove "未回答者" role if it exists
        if not self.is_test and interaction.guild:
            role = discord.utils.get(interaction.guild.roles, name="未回答者")
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
