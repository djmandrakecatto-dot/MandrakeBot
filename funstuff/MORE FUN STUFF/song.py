import discord
from discord.ext import commands
import asyncio
import os
import glob

class SongPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_files = {} # Track files per guild to delete on kick

    def clean_temp_files(self):
        """Finds and deletes any leftover temp files on startup/load"""
        for f in glob.glob("temp_*"):
            try:
                os.remove(f)
                print(f"🗑️ Startup Cleanup: Removed {f}")
            except:
                pass

    @commands.command(name="play")
    async def play(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("❌ You need to be in a voice channel!")

        if not ctx.message.attachments:
            return await ctx.send("❓ Attach an audio file!")
        
        attachment = ctx.message.attachments[0]
        vc = ctx.voice_client
        if not vc:
            vc = await ctx.author.voice.channel.connect()

        if vc.is_playing():
            vc.stop()

        # Unique filename using guild ID to prevent overlap
        file_path = f"temp/temp_{ctx.guild.id}_{attachment.filename}"
        await attachment.save(file_path)
        self.current_files[ctx.guild.id] = file_path

        def after_playing(error):
            # Attempt immediate delete
            self.delete_guild_temp(ctx.guild.id)
            self.bot.loop.create_task(self.auto_quit_check(ctx))

        source = discord.FFmpegPCMAudio(file_path)
        vc.play(source, after=after_playing)
        await ctx.send(f"🎶 Playing: **{attachment.filename}**")

    def delete_guild_temp(self, guild_id):
        """Helper to safely delete a specific guild's temp file"""
        path = self.current_files.get(guild_id)
        if path and os.path.exists(path):
            try:
                os.remove(path)
                del self.current_files[guild_id]
            except Exception as e:
                print(f"⚠️ Delete failed: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handles Auto-Delete even if the bot is kicked or leaves"""
        # If the bot itself is the one who changed state
        if member.id == self.bot.user.id:
            # If 'after.channel' is None, the bot was kicked or disconnected
            if after.channel is None:
                print(f"⚠️ Bot left/kicked from {member.guild.name}. Cleaning up...")
                self.delete_guild_temp(member.guild.id)
                return

        # Regular Auto-quit if bot is alone
        vc = member.guild.voice_client
        if vc and len(vc.channel.members) == 1:
            await vc.disconnect()
            self.delete_guild_temp(member.guild.id)

    async def auto_quit_check(self, ctx):
        await asyncio.sleep(60) # Reduced to 60s for safety
        vc = ctx.voice_client
        if vc and not vc.is_playing():
            await vc.disconnect()
            self.delete_guild_temp(ctx.guild.id)

    @commands.command(name="stop")
    async def stop(self, ctx):
        vc = ctx.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
            self.delete_guild_temp(ctx.guild.id)
            await ctx.send("🛑 Stopped and file cleared.")

async def setup(bot):
    cog = SongPlayer(bot)
    cog.clean_temp_files() # Run cleanup when cog loads
    await bot.add_cog(cog)