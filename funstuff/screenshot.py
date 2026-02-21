import discord
from discord.ext import commands
import pyautogui
import os
import tempfile
import psutil
import asyncio

# --- FIXED: List of authorized IDs ---
AUTHORIZED_USERS = [1420837251524460594, 1228024408912953344]

class SystemAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="screenshot")
    async def screenshot(self, ctx):
        """Captures the HP-Note screen for authorized users only."""
        
        # 🛡️ SECURITY: Check if the user ID is in our list
        if ctx.author.id not in AUTHORIZED_USERS:
            return await ctx.send("🚫 **Access Denied**: You are not on the authorized list.")

        # 🛡️ RESOURCE GUARD: Respecting the 90% RAM rule
        ram_now = psutil.virtual_memory().percent
        if ram_now > 90.0:
            return await ctx.send(f"⚠️ **Memory Guard**: RAM is at {ram_now}%. System is too busy.")

        await ctx.send("📸 **Capturing screen...**")

        try:
            # Create a temporary environment
            with tempfile.TemporaryDirectory() as tmp_dir:
                shot_path = os.path.join(tmp_dir, "screenshot.png")
                
                # Take screenshot in a separate thread to keep bot alive
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: pyautogui.screenshot(shot_path))
                
                # Send the file
                await ctx.send(
                    content=f"🖥️ **Screen Capture**\n👤 Requested by: {ctx.author.name}\n📊 RAM: {ram_now}%",
                    file=discord.File(shot_path)
                )
                
        except Exception as e:
            await ctx.send(f"❌ **Failed to capture**: `{e}`")

async def setup(bot):
    await bot.add_cog(SystemAdmin(bot))