import discord
from discord.ext import commands
from PIL import Image
import io
import asyncio
from functools import partial

class Squish(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def process_squish(self, data, frame_count):
        # 1. Load the base image
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        width, height = img.size
        
        frames = []
        for i in range(frame_count):
            # Calculate the new height (shrinks then grows back)
            # This uses a simple multiplier based on the frame index
            scale = 1.0 - (i / frame_count)
            if scale <= 0: scale = 0.05 # Prevent 0 height errors
            
            new_height = int(height * scale)
            
            # Create a transparent canvas so the image "squishes" toward the bottom
            canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            resized_img = img.resize((width, new_height), Image.LANCZOS)
            
            # Paste resized image at the bottom of the canvas
            canvas.paste(resized_img, (0, height - new_height))
            frames.append(canvas)

        # 2. Save to a Byte stream as a GIF
        out = io.BytesIO()
        frames[0].save(
            out,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=40, # 40ms per frame
            loop=0,
            disposal=2 # Clears previous frame to prevent ghosting
        )
        out.seek(0)
        return out

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def squish(self, ctx, frames: int = 20, image_url: str = None):
        # Limit frames to prevent your PC from exploding
        if frames < 2 or frames > 500:
            return await ctx.send("❌ Please choose between 2 and 500 frames.")

        # Reusing your existing helper to get image data
        # (Assuming you have this in the same class or globally)
        data = await self.bot.get_cog("Fun").load_image(ctx, image_url)
        
        if not data:
            return await ctx.send("❌ No image found!")

        msg = await ctx.send(f"⏳ Squishing into {frames} frames... this might take a second.")

        # Run the heavy processing in a separate thread so the bot doesn't freeze
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None, 
                partial(self.process_squish, data, frames)
            )
            
            await ctx.send(file=discord.File(result, filename="squished.gif"))
            await msg.delete()
        except Exception as e:
            await ctx.send(f"⚠️ Error: {e}")

async def setup(bot):
    await bot.add_cog(Squish(bot))