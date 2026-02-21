import discord
from discord.ext import commands
from gtts import gTTS
import asyncio
import os
import uuid

class EnglishTTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def generate_speech(self, text, file_path):
        """Generate speech using Google TTS"""
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(file_path)
        return file_path

    @commands.command(name="tts")
    async def tts(self, ctx, *, message: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Join a voice channel first!")

        # Ensure temp folder exists
        os.makedirs("temp", exist_ok=True)

        # gTTS outputs mp3
        file_path = f"temp/gtts_{uuid.uuid4().hex}.mp3"

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.generate_speech,
                message,
                file_path
            )

            vc = ctx.voice_client
            if not vc:
                vc = await ctx.author.voice.channel.connect()

            # Stop current audio if playing
            if vc.is_playing():
                vc.stop()

            def cleanup(error):
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass

            source = discord.FFmpegPCMAudio(file_path)
            vc.play(source, after=cleanup)

            await ctx.message.add_reaction("🎙️")

        except Exception as e:
            await ctx.send(f"⚠️ gTTS Error: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)

async def setup(bot):
    await bot.add_cog(EnglishTTS(bot))
