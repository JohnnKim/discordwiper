import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction, ui
import asyncio
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
import os

# BOT SETUP
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

# Backup enable/disable flag
backup_enabled = True

# Create bot with prefix ! and required intents
bot = commands.Bot(command_prefix='!', intents=intents)
# Channel specific autowipe settings: channel_id -> seconds
autowipe_settings = defaultdict(int)
# Scheduled all clear time (datetime object)
scheduled_nuke_time = None

# PERMISSION CHECK 
def is_admin():
    """Custom command check to restrict to admins only."""
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

# EVENTS 
@bot.event
async def on_ready():
    """Called once the bot is ready and connected."""
    print(f'Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")  # Sync slash commands
    except Exception as e:
        print(f"Slash command sync failed: {e}")
    nuke_watcher.start()    # Start background task for scheduled server wipes

@bot.event
async def on_message(message):
    """Handles autowipe if enabled for the channel."""
    await bot.process_commands(message) # Ensure commands still work
    if message.author.bot:
        return
    delay = autowipe_settings.get(message.channel.id, 0)
    if delay > 0:
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except:
            pass    # Bot may lack permission or message is gone

# COMMANDS 
@bot.command()
@is_admin()
async def wipe(ctx, mode: str = None, arg=None):
    """Handles different wipe modes: recent, user, channel."""
    if mode == "recent":
        try:
            count = int(arg)
            deleted = await ctx.channel.purge(limit=count + 1)
            await ctx.send(f"Wiped {len(deleted)-1} messages.", delete_after=3)
        except:
            await ctx.send("Invalid usage. Try `!wipe recent <count>`", delete_after=5)

    elif mode == "user":
        if not ctx.message.mentions:
            await ctx.send("Tag a user. `!wipe user @user <count>`", delete_after=5)
            return
        try:
            count = int(arg if len(ctx.message.mentions) == 0 else ctx.message.content.split()[-1])
            target = ctx.message.mentions[0]
            deleted = await ctx.channel.purge(limit=1000, check=lambda m: m.author == target)
            await ctx.send(f"Wiped {len(deleted)} messages from {target.display_name}.", delete_after=5)
        except:
            await ctx.send("Could not wipe user messages.", delete_after=5)

    elif mode == "channel":
        await ctx.send("Wiping this entire channel in 3 seconds...", delete_after=3)
        await asyncio.sleep(3)
        await backup_channel(ctx.channel)
        deleted = await ctx.channel.purge(limit=1000)
        await ctx.send(f"Nuked {len(deleted)} messages.", delete_after=3)

    else:
        await ctx.send("Usage:\n- `!wipe recent <count>`\n- `!wipe user @user <count>`\n- `!wipe channel`", delete_after=7)

@bot.command()
@is_admin()
async def wipeallchannels(ctx):
    """Purges all text channels in the server."""
    await ctx.send("Wiping ALL channels in this server...", delete_after=5)
    for channel in ctx.guild.text_channels:
        try:
            await backup_channel(channel)
            deleted = await channel.purge(limit=1000)
            await ctx.send(f"✔️ {channel.name}: {len(deleted)} messages wiped.", delete_after=3)
        except Exception as e:
            print(f"Error wiping {channel.name}: {e}")

@bot.command()
@is_admin()
async def autowipe(ctx, seconds: int = 0):
    """Enables or disables auto-deletion of all new messages in a channel."""
    cid = ctx.channel.id
    autowipe_settings[cid] = seconds
    if seconds > 0:
        await ctx.send(f"Autowipe: All messages will delete after {seconds}s", delete_after=5)
    else:
        await ctx.send("Autowipe disabled.", delete_after=5)

@bot.command()
@is_admin()
async def nukeat(ctx, time_str):
    """Schedules a full server wipe at a specific time (24h format)."""
    global scheduled_nuke_time
    try:
        now = datetime.now()
        hour, minute = map(int, time_str.split(":"))
        scheduled_nuke_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if scheduled_nuke_time < now:
            scheduled_nuke_time = scheduled_nuke_time.replace(day=now.day + 1)
        await ctx.send(f"Scheduled nuke for {scheduled_nuke_time.strftime('%H:%M')}!", delete_after=5)
    except:
        await ctx.send("Use format `!nukeat HH:MM`", delete_after=5)

@bot.command()
@is_admin()
async def togglebackup(ctx):
    """Toggles message log backup before purging."""
    global backup_enabled
    backup_enabled = not backup_enabled
    state = "enabled" if backup_enabled else "disabled"
    await ctx.send(f"Backup before wipes is now **{state}**.", delete_after=5)

# NUKE TASK 
@tasks.loop(seconds=30)
async def nuke_watcher():
    """Background task that executes scheduled nukes."""
    global scheduled_nuke_time
    if scheduled_nuke_time and datetime.now() >= scheduled_nuke_time:
        print("Executing scheduled nuke!")
        for guild in bot.guilds:
            for channel in guild.text_channels:
                try:
                    await backup_channel(channel)
                    await channel.purge(limit=1000)
                    await channel.send("Channel wiped.", delete_after=5)
                except:
                    continue
        scheduled_nuke_time = None

# BACKUP 
async def backup_channel(channel):
    """Saves last 1000 messages in a channel to a .txt file before wiping if backup is enabled."""
    if not backup_enabled:
        return  # Skip backup if disabled

    logs = []
    async for msg in channel.history(limit=1000, oldest_first=True):
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        logs.append(f"[{timestamp}] {msg.author}: {msg.content}")
    filename = f"backup_{channel.guild.name}_{channel.name}.txt".replace(" ", "_")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(logs))


# HELP MENU 
class HelpDropdown(ui.Select):
    """Dropdown menu to choose between help topics."""
    def __init__(self):
        options = [
            discord.SelectOption(label="Wipe Commands", description="Wipe recent, user, channel, all"),
            discord.SelectOption(label="Autowipe", description="Auto-delete messages after X seconds"),
            discord.SelectOption(label="Scheduled Nukes", description="Schedule a full wipe"),
        ]
        super().__init__(placeholder="Choose a command category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        label = self.values[0]
        embed = discord.Embed(title=f"📘 {label}", color=discord.Color.orange())

        if label == "Wipe Commands":
            embed.description = """
`!wipe recent <count>` – Delete last N messages  
`!wipe user @user <count>` – Delete messages from user  
`!wipe channel` – Delete this channel  
`!wipeallchannels` – Wipe all text channels
"""
        elif label == "Autowipe":
            embed.description = """
`!autowipe <seconds>` – Auto-delete new messages after X seconds  
`!autowipe 0` – Disable autowipe
"""
        elif label == "Scheduled Nukes":
            embed.description = """
`!nukeat HH:MM` – Schedule server wipe (e.g. `!nukeat 23:59`)
"""

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpToggleButton(ui.Button):
    """Toggle button to show advanced bot features."""
    def __init__(self):
        super().__init__(label="Show Advanced", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: Interaction):
        embed = discord.Embed(
            title="Advanced Features",
            description=f"""
        - Scheduled nukes auto-wipe all channels  
        - Backup logs are saved as `.txt` before each purge (**Currently {'ENABLED' if backup_enabled else 'DISABLED'}**)  
        - Autowipe runs per channel in background  
        - Admin-only command protection
        """,
            color=discord.Color.dark_red()
        )
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(ui.View):
    """Combined dropdown + toggle button view."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpDropdown())
        self.add_item(HelpToggleButton())

@bot.tree.command(name="help", description="View bot command help.")
async def slash_help(interaction: discord.Interaction):
    """Slash version of help command with UI."""
    embed = discord.Embed(
        title="Wiper Help",
        description="Select a category to view available commands.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)

if __name__ == "__main__":
    load_dotenv()
    bot.run(os.getenv("DISCORD_TOKEN"))