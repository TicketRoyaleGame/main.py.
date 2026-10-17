import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import asyncio
from flask import Flask
import threading

# שרת רקע קטן ל-Render (משתמש בפורט ברירת מחדל 10000 או משתנה סביבה)
app = Flask(__name__)
@app.route('/')
def home(): return "Ticket Bot is alive!", 200
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================================================
# הגדרות הבוט
# =========================================================
TOKEN = os.getenv("TOKEN")
ALLOWED_USER_ID = 961945951780630541       # רק המשתמש הזה יכול לזמן את הפאנל
LOG_CHANNEL_ID = 1560756016604512376       # חדר לוגי הטיקטים

# רשימת כל 24 הרולים של הצוות שיכולים לראות את הטיקטים ולתפוס אותם
STAFF_ROLES_IDS = [
    1560613411421818930, 1560613411421818931, 1560613411421818933, 1560613411421818934,
    1560613411421818935, 1560613411421818937, 1560613411421818938, 1560613411421818939,
    1560613411522347190, 1560613411522347191, 1560613411522347192, 1560613411522347193,
    1560613411522347194, 1560613411522347195, 1560613411522347197, 1560613411522347198,
    1560613411522347199, 1560613411564552342, 1560613411564552343, 1560613411564552344,
    1560613411564552345, 1560613411564552346, 1560613411564552347, 1560613411564552348
]
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def send_ticket_log(title, description, color):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title=title, description=description, color=color)
        await log_channel.send(embed=embed)

class TicketControlsView(View):
    def __init__(self, creator_id, claimer_id=None):
        super().__init__(timeout=None)
        self.creator_id = creator_id
        self.claimer_id = claimer_id

    @discord.ui.button(label="✋ תפוס טיקט", style=discord.ButtonStyle.primary, custom_id="claim_ticket_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_staff_role = any(role.id in STAFF_ROLES_IDS for role in interaction.user.roles)
        if not has_staff_role and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ רק צוות המורשה יכול לתפוס טיקטים!", ephemeral=True)
            return
        if self.claimer_id:
            await interaction.response.send_message(f"❌ תפוס על ידי <@{self.claimer_id}>!", ephemeral=True)
            return

        self.claimer_id = interaction.user.id
        guild = interaction.guild
        creator = guild.get_member(self.creator_id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if creator: overwrites[creator] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
        for role_id in STAFF_ROLES_IDS:
            role = guild.get_role(role_id)
            if role and role not in interaction.user.roles: overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)

        await interaction.channel.edit(name=f"✋-{interaction.user.name}", overwrites=overwrites)
        await interaction.response.send_message(f"✋ הטיקט נתפס על ידי {interaction.user.mention}.", ephemeral=False)
        await send_ticket_log("✋ טיקט נתפס", f"**חדר:** {interaction.channel.mention}\n**על ידי:** {interaction.user.mention}", discord.Color.orange())

    @discord.ui.button(label="🔓 שחרר טיקט", style=discord.ButtonStyle.secondary, custom_id="unclaim_ticket_btn")
    async def unclaim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.claimer_id:
            await interaction.response.send_message("❌ הטיקט לא תפוס.", ephemeral=True)
            return
        if interaction.user.id != self.claimer_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ רק מי שתפס יכול לשחרר!", ephemeral=True)
            return

        self.claimer_id = None
        guild = interaction.guild
        creator = guild.get_member(self.creator_id)
        creator_name = creator.name if creator else "user"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if creator: overwrites[creator] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
        for role_id in STAFF_ROLES_IDS:
            role = guild.get_role(role_id)
            if role: overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)

        await interaction.channel.edit(name=f"ticket-{creator_name}", overwrites=overwrites)
        await interaction.response.send_message("🔓 הטיקט שוחרר והוחזר לצוות.", ephemeral=False)

    @discord.ui.button(label="🔒 סגור טיקט", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 יימחק בעוד 5 שניות...")
        await send_ticket_log("🔒 טיקט נסגר", f"**שם החדר:** `{interaction.channel.name}`\n**על ידי:** {interaction.user.mention}", discord.Color.red())
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketCreateView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="📩 פתח טיקט תמיכה", style=discord.ButtonStyle.success, custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for role_id in STAFF_ROLES_IDS:
            role = guild.get_role(role_id)
            if role: overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)

        ticket_channel = await guild.create_text_channel(name=f"ticket-{member.name}", overwrites=overwrites)
        embed = discord.Embed(title="תודה שפנית לתמיכה! 👋", description="נא לפרט כאן את סיבת הפנייה.", color=discord.Color.green())
        await ticket_channel.send(embed=embed, view=TicketControlsView(creator_id=member.id))
        await interaction.response.send_message(f"✅ הטיקט נפתח: {ticket_channel.mention}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"🎫 {bot.user.name} מחובר!")
    bot.add_view(TicketCreateView())
    try:
        await bot.tree.sync()
    except Exception as e: print(e)

@bot.tree.command(name="setup-tickets", description="מציב את פאנל הטיקטים בשרת")
async def setup_tickets(interaction: discord.Interaction):
    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("❌ אין הרשאה!", ephemeral=True)
        return
    embed = discord.Embed(title="פתיחת פנייה לצוות 📩", description="לחץ למטה לפתיחת חדר תמיכה.", color=discord.Color.blue())
    await interaction.response.send_message("✅ שוגר!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=TicketCreateView())

@bot.command(name="add")
async def add_user(ctx, member: discord.Member):
    if not ctx.channel.name.startswith("ticket-") and not ctx.channel.name.startswith("✋-"): return
    await ctx.channel.set_permissions(member, read_messages=True, send_messages=True, attach_files=True)
    await ctx.send(f"✅ {member.mention} התווסף.")

threading.Thread(target=run_flask, daemon=True).start()
bot.run(TOKEN)
import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
from flask import Flask
import threading

# שרת רקע קטן ל-Render (משתמש בפורט אחר כדי למנוע התנגשויות - פורט 10001)
app = Flask(__name__)
@app.route('/')
def home(): return "Verify Bot is alive!", 200
def run_flask():
    port = int(os.environ.get("PORT", 10001))
    app.run(host="0.0.0.0", port=port)

# =========================================================
# הגדרות הבוט
# =========================================================
TOKEN = os.getenv("TOKEN")
ALLOWED_USER_ID = 961945951780630541       # רק המשתמש הזה יכול לזמן את הפאנל
VERIFIED_ROLE_ID = 1560666081574526977     # ה-ID של רול האימות (חבר שרת)
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents)

class VerifyView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="✅ לחץ כאן לאימות חשבון", style=discord.ButtonStyle.success, custom_id="verify_button_main")
    async def verify_click(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        role = guild.get_role(VERIFIED_ROLE_ID)
        
        if not role:
            await interaction.response.send_message("❌ רול האימות לא מוגדר תקין בקוד.", ephemeral=True)
            return
        if role in member.roles:
            await interaction.response.send_message("אתה כבר מאומת! 🎉", ephemeral=True)
            return

        try:
            await member.add_roles(role)
            await interaction.response.send_message("אומתת בהצלחה וקיבלת גישה! 🎉", ephemeral=True)
        except Exception:
            await interaction.response.send_message("שגיאה. ודא שהרול של הבוט גבוה יותר ברשימה.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"🛡️ {bot.user.name} מחובר!")
    bot.add_view(VerifyView())
    try:
        await bot.tree.sync()
    except Exception as e: print(e)

@bot.tree.command(name="setup-verify", description="מציב את פאנל האימות בשרת")
async def setup_verify(interaction: discord.Interaction):
    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("❌ אין הרשאה!", ephemeral=True)
        return
    embed = discord.Embed(title="מערכת אימות חשבון 🛡️", description="לחץ למטה לקבלת רול חבר שרת וגישה.", color=discord.Color.green())
    await interaction.response.send_message("✅ פאנל האימות שוגר!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=VerifyView())

threading.Thread(target=run_flask, daemon=True).start()
bot.run(TOKEN)
