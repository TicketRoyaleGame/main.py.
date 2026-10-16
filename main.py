import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio

# =========================================================
# הגדרות הבוט והשרת שלך - שים כאן את המספרים והטוקן ישירות!
# =========================================================
TOKEN = "שים_כאן_את_הטוקן_הסודי_של_הבוט_שלך"
GUILD_ID = 1560666081574526977          # ה-ID של שרת האימות שלך
TICKET_CATEGORY_ID = 1560666081574526977 # ה-ID של הקטגוריה שבה ייפתחו הטיקטים
STAFF_ROLE_ID = 15606134111157581949     # ה-ID של רול הצוות (מי שיכול לתפוס טיקט)
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- מערכת כפתורי הניהול בתוך הטיקט הפרטי ---
class TicketControlsView(View):
    def __init__(self, creator_id, claimer_id=None):
        super().__init__(timeout=None)
        self.creator_id = creator_id
        self.claimer_id = claimer_id

    # 1. כפתור תפיסת טיקט (Claim)
    @discord.ui.button(label="✋ תפוס טיקט", style=discord.ButtonStyle.primary, custom_id="claim_ticket_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        staff_role = guild.get_role(STAFF_ROLE_ID)
        
        if staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ רק צוות השרת יכול לתפוס טיקטים!", ephemeral=True)
            return
            
        if self.claimer_id:
            await interaction.response.send_message(f"❌ הטיקט הזה כבר תפוס על ידי <@{self.claimer_id}>!", ephemeral=True)
            return

        self.claimer_id = interaction.user.id
        creator = guild.get_member(self.creator_id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if creator:
            overwrites[creator] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)

        await interaction.channel.edit(name=f"✋-{interaction.user.name}", overwrites=overwrites)
        await interaction.response.send_message(f"✋ הטיקט נתפס על ידי {interaction.user.mention}. שאר אנשי הצוות הועברו למצב צפייה בלבד.", ephemeral=False)

    # 2. כפתור שחרור טיקט (Unclaim)
    @discord.ui.button(label="🔓 שחרר טיקט", style=discord.ButtonStyle.secondary, custom_id="unclaim_ticket_btn")
    async def unclaim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        staff_role = guild.get_role(STAFF_ROLE_ID)

        if interaction.user.id != self.claimer_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ רק איש הצוות שתפס את הטיקט יכול לשחרר אותו!", ephemeral=True)
            return

        if not self.claimer_id:
            await interaction.response.send_message("❌ הטיקט הזה לא תפוס על ידי אף אחד.", ephemeral=True)
            return

        self.claimer_id = None
        creator = guild.get_member(self.creator_id)
        creator_name = creator.name if creator else "user"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if creator:
            overwrites[creator] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)

        await interaction.channel.edit(name=f"ticket-{creator_name}", overwrites=overwrites)
        await interaction.response.send_message("🔓 הטיקט שוחרר והוחזר לכלל צוות התמיכה.", ephemeral=False)

    # 3. כפתור סגירת טיקט (Close)
    @discord.ui.button(label="🔒 סגור טיקט", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 הטיקט נסגר. החדר יימחק אוטומטית בעוד 5 שניות...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- פאנל הטיקטים המרכזי ---
class TicketCreateView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 פתח טיקט תמיכה", style=discord.ButtonStyle.success, custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        category = guild.get_channel(TICKET_CATEGORY_ID)
        staff_role = guild.get_role(STAFF_ROLE_ID)

        if not category:
            await interaction.response.send_message("שגיאה: קטגוריית הטיקטים לא נמצאה בקוד.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{member.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="תודה שפנית לתמיכה! 👋",
            description=f"היי {member.mention}, נא לפרט כאן את סיבת הפנייה.\nנציג מצוות השרת יתפוס את הפנייה שלך בקרוב וייענה לך.",
            color=discord.Color.green()
        )
        
        await ticket_channel.send(embed=embed, view=TicketControlsView(creator_id=member.id))
        await interaction.response.send_message(f"✅ הטיקט שלך נפתח בהצלחה! כנס לכאן: {ticket_channel.mention}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"🎫 {bot.user.name} מחובר ומוכן לנהל טיקטים מתקדמים!")
    bot.add_view(TicketCreateView())

# פקודה להצבת פאנל הטיקטים הראשי
@bot.command(name="setup-tickets")
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    embed = discord.Embed(
        title="פתיחת פנייה לצוות השרת 📩",
        description="צריך עזרה או מענה אישי? \nלחץ על הכפתור למטה כדי לפתוח חדר תמיכה פרטי.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketCreateView())

# פקודה להוספת אנשים לטיקט (פקודה: add @תיוג)
@bot.command(name="add")
async def add_user(ctx, member: discord.Member):
    if not ctx.channel.name.startswith("ticket-") and not ctx.channel.name.startswith("✋-"):
        await ctx.send("❌ ניתן להשתמש בפקודה זו רק בתוך חדר טיקט פתוח!")
        return
        
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles and not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ רק צוות השרת יכול להוסיף אנשים לטיקט!")
        return

    await ctx.channel.set_permissions(member, read_messages=True, send_messages=True, attach_files=True)
    await ctx.send(f"✅ המשתמש {member.mention} התווסף לטיקט בהצלחה וקיבל גישה לחדר.")

bot.run(TOKEN)
