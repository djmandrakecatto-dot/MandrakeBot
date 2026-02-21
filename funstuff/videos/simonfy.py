import discord
from discord.ext import commands
import asyncio
import math
import os
import functools
import shutil
import tempfile
import psutil
from moviepy import ImageClip, AudioFileClip, CompositeAudioClip
DELAY = 110
FUNSTUFF_DIR = "./funstuff"
FPS = 30
MEMORY_THRESHOLD = 90.0

class RealmSimonfy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_sync_seconds(self, DELAY):
        """
        Calculates the sync offset in SECONDS based on your Scratch block.
        Matches: floor((60 / DELAY * 16 * 20) / 20)
        """
        # This calculates the total 'units' from your block
        raw_value = (60 / DELAY) * 16 * 20 / 20
        # Returning this as the direct start time in seconds
        return math.floor(raw_value)

    def bake_from_attachment(self, input_image, output_video):
        simon1_path = os.path.join(FUNSTUFF_DIR, "SIMON1.wav")
        simon2_path = os.path.join(FUNSTUFF_DIR, "SIMON2.wav")

        audio_tracks = []
        
        # ⏱️ Calculating the direct SECONDS offset
        simon2_start_time = self.get_sync_seconds(107) 

        total_duration = 8.0 # Fallback

        try:
            if os.path.exists(simon1_path):
                s1 = AudioFileClip(simon1_path)
                audio_tracks.append(s1)
                total_duration = max(total_duration, s1.duration)

            if os.path.exists(simon2_path):
                # Simon 2 triggers at the exact SECOND calculated
                s2 = AudioFileClip(simon2_path).with_start(simon2_start_time)
                audio_tracks.append(s2)
                # Adjust video length so the delayed audio finishes
                total_duration = max(total_duration, simon2_start_time + s2.duration)

            # Create the video from the image
            with ImageClip(input_image).with_duration(total_duration) as clip:
                clip = clip.with_fps(FPS)

                if audio_tracks:
                    final_audio = CompositeAudioClip(audio_tracks)
                    clip = clip.with_audio(final_audio)

                # Write file (Optimized for HP-Note)
                clip.write_videofile(
                    output_video,
                    codec="libx264",
                    audio_codec="aac",
                    preset="ultrafast",
                    threads=2,
                    logger=None
                )
        finally:
            # 🛡️ FORCE STOP: Release audio handles to prevent index crash
            for track in audio_tracks:
                try: track.close()
                except: pass
            print(f"✅ Second-based Sync Finished: {simon2_start_time}s offset.")

    @commands.command(name="realmsimonfy")
    async def realmsimonfy(self, ctx):
        if psutil.virtual_memory().percent > MEMORY_THRESHOLD:
            return await ctx.send("⚠️ RAM too high. Bake paused.")

        if not ctx.message.attachments:
            return await ctx.send("🖼️ Attach an image to bake.")

        attachment = ctx.message.attachments[0]
        
        # Immediate feedback on the sync time
        sync_time = self.get_sync_seconds(110)
        await ctx.send(f"🎬 **Syncing...** (Simon 2 starts at: {sync_time} seconds)")

        tmp = tempfile.mkdtemp()
        input_path = os.path.join(tmp, attachment.filename)
        output_path = os.path.join(tmp, "realmsimonfy_baked.mp4")

        try:
            await attachment.save(input_path)

            loop = asyncio.get_event_loop()
            task = functools.partial(self.bake_from_attachment, input_path, output_path)
            
            await asyncio.wait_for(loop.run_in_executor(None, task), timeout=90.0)

            await ctx.send(
                content=f"✅ **Bake Complete!** {ctx.author.mention}",
                file=discord.File(output_path)
            )

        except Exception as e:
            await ctx.send(f"⚠️ **Bake Error**: `{e}`")
        finally:
            await asyncio.sleep(2)
            shutil.rmtree(tmp, ignore_errors=True)

async def setup(bot):
    await bot.add_cog(RealmSimonfy(bot))