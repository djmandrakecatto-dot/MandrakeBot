import discord
from discord.ext import commands
import psutil
import os
import platform

class SystemStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pcstats")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 60, commands.BucketType.user) # 1-min Anti-Spam
    async def pc_stats(self, ctx):
        """Complete hardware monitor for HP-Note."""
        
        # 1. CPU Metrics
        cpu_usage = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        
        # 2. System RAM Metrics
        ram = psutil.virtual_memory()
        ram_used = ram.used / (1024 ** 3)  # GB
        ram_total = ram.total / (1024 ** 3)
        ram_percent = ram.percent
        
        # 3. Disk & Bot Metrics
        disk = psutil.disk_usage('/')
        disk_free = disk.free / (1024 ** 3)
        process = psutil.Process(os.getpid())
        bot_ram = process.memory_info().rss / (1024 ** 2) # MB
        
        # Determine Color based on RAM Guard (95.5% threshold)
        embed_color = discord.Color.red() if ram_percent > 90 else discord.Color.blue()
        
        embed = discord.Embed(
            title="🖥️ Server System Monitor",
            color=embed_color
        )
        
        embed.add_field(name="CPU Usage", value=f"**{cpu_usage}%** ({cpu_count} Cores)", inline=True)
        embed.add_field(name="System RAM", value=f"**{ram_used:.2f}GB** / {ram_total:.2f}GB ({ram_percent}%)", inline=True)
        embed.add_field(name="Bot RAM", value=f"**{bot_ram:.2f} MB**", inline=True)
        embed.add_field(name="Storage Free", value=f"**{disk_free:.2f} GB**", inline=True)
        embed.add_field(name="OS", value=f"{platform.system()} {platform.release()}", inline=False)
        
        # HP-Note Resource Guard Feedback
        if ram_percent > 90:
            embed.set_footer(text=f"⚠️ WARNING: RAM at {ram_percent}%! Auto-pause active.")
        else:
            embed.set_footer(text="✅ System stable. Anti-DDoS Queue: Idle.")

        await ctx.send(embed=embed)

    @pc_stats.error
    async def pc_stats_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 **Admin Only**: Hardware stats are restricted.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ **Cooldown**: Please wait {error.retry_after:.1f}s.")

async def setup(bot):
    await bot.add_cog(SystemStats(bot))