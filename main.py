import discord
from discord.ext import commands
import os
import asyncio
# never gonna work on pypy for me import psutil
import psutil

def get_token():
    try:
        with open("secrets.txt", "r") as f:
            for line in f:
                if line.startswith("DISCORD_TOKEN="):
                    return line.strip().split("=", 1)[1]
    except FileNotFoundError:
        print("❌ Error: secrets.txt not found!")
        return None
async def console_listener():
    await bot.wait_until_ready()
    print("💻 Console ready. Type commands below.")

    while not bot.is_closed():
        try:
            cmd = await asyncio.to_thread(input, "CMD> ")

            if cmd.startswith("sendmessageser "):
                parts = cmd.split(" ", 2)
                if len(parts) < 3:
                    print("Usage: sendmessageser [channel_id] [text]")
                    continue

                try:
                    channel_id = int(parts[1])
                except ValueError:
                    print("❌ Channel ID must be a number.")
                    continue

                message = parts[2]

                channel = bot.get_channel(channel_id)
                if channel is None:
                    try:
                        channel = await bot.fetch_channel(channel_id)
                    except Exception:
                        print("❌ Invalid channel or no access.")
                        continue

                try:
                    await channel.send(message)
                    print(f"✅ Message sent to {channel_id}")
                except Exception as e:
                    print(f"❌ Failed to send message: {e}")

            elif cmd == "reload":
                print("🔄 Reloading cogs...")
                await load_cogs()

            elif cmd == "exit":
                print("🛑 Shutting down...")
                await bot.close()

            else:
                print("Unknown command.")

        except Exception as e:
            print(f"Console error: {e}")
# --- RESOURCE GUARD LOGIC ---
MEMORY_THRESHOLD = 95.5 # Percent

def is_system_safe():
    """Checks if RAM usage is below the threshold."""
    return psutil.virtual_memory().percent < MEMORY_THRESHOLD
    pass
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class MandrakeBot(commands.Bot):
    def __init__(self):
        # We define the command_prefix but also prepare the app_commands tree
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.process_queue = asyncio.Semaphore(5)

    async def setup_hook(self):
        """This runs before the bot starts connecting to Discord."""
        # 1. Load Cogs
        await load_cogs()
        
        # 2. Sync Slash Commands
        # This is the "App Compatible" part. It copies ! commands to / commands.
        print("🔄 Syncing Slash Commands...")
        try:
            # Syncing globally takes about 1-10 mins to appear.
            # To sync instantly to one server for testing, use: 
            # self.tree.copy_global_to(guild=discord.Object(id=YOUR_GUILD_ID))
            synced = await self.tree.sync()
            print(f"✅ App Compatible: {len(synced)} slash commands synced.")
        except Exception as e:
            print(f"❌ Slash Sync Error: {e}")

bot = MandrakeBot()

# --- GLOBAL COMMAND CHECK ---
@bot.check
async def resource_gatekeeper(ctx):
    if not is_system_safe():
        await ctx.send(f"⚠️ **SYSTEM OVERLOAD**: RAM is at {psutil.virtual_memory().percent}%. "
                       "Commands are paused to prevent a crash.")
        return False
    return True

# --- GLOBAL ERROR HANDLER ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"🚫 **STOP SPAMMING**: Locked for {error.retry_after:.1f}s.")
    elif isinstance(error, commands.MaxConcurrencyReached):
        await ctx.send("🚦 **QUEUE FULL**: Please wait for the current tasks to finish.")
    elif isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        pass 
    else:
        print(f"Ignored error: {error}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not is_system_safe():
        return 
    await bot.process_commands(message)
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"🛡️ Resource Guard: {MEMORY_THRESHOLD}% | Queue: Active")

    bot.loop.create_task(console_listener())
# --- HYBRID HELP COMMAND ---
@bot.hybrid_command(name="help", description="List all available commands")
async def help(ctx):
    """Works for both !help and /help"""

    embeds = []
    embed = discord.Embed(
        title="🤖 Mandrake Bot - Hybrid Help",
        color=discord.Color.from_rgb(255, 69, 0),
        description="I support both `!` prefix and `/` Slash Commands!"
    )

    field_count = 0

    for cog_name, cog in bot.cogs.items():
        cmd_list = [f"`{c.name}`" for c in cog.get_commands()]
        if not cmd_list:
            continue

        # If we reach 25 fields, create a new embed
        if field_count >= 25:
            embeds.append(embed)
            embed = discord.Embed(
                title="🤖 Mandrake Bot - Hybrid Help (Continued)",
                color=discord.Color.from_rgb(255, 69, 0)
            )
            field_count = 0

        embed.add_field(
            name=f"📦 {cog_name}",
            value=", ".join(cmd_list),
            inline=False
        )
        field_count += 1

    embeds.append(embed)

    # Send first embed normally
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        for e in embeds:
            await ctx.send(embed=e)

# --- COG LOADER ---
async def load_cogs():
    dirs = ["./funstuff", "./funstuff/MORE FUN STUFF", "funstuff/videos", "funstuff/stats"]
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            continue
        for filename in os.listdir(directory):
            if filename.endswith(".py") and filename != "__init__.py":
                # Convert path to module format
                clean_dir = directory.replace("./", "").replace("/", ".")
                module = f"{clean_dir}.{filename[:-3]}"
                try:
                    if module in bot.extensions:
                        await bot.unload_extension(module)
                    await bot.load_extension(module)
                    print(f"Successfully loaded: {module}")
                except Exception as e:
                    print(f"⚠️ Failed to load {module}: {e}")

async def start_bot():
    token = get_token()
    if token:
        async with bot:
            await bot.start(token)
async def main():
    """Bridges the gap to run the async bot."""
    token = get_token()
    if token:
        # We use 'async with' inside an 'async def' function (main)
        async with bot:
            await bot.start(token)
    else:
        print("❌ Token not found. Check secrets.txt")

if __name__ == "__main__":
    try:
        # This is the standard way to run the top-level async function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot shutting down...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")