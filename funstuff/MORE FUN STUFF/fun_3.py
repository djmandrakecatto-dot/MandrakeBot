import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import os

class TextGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Path to Windows Fonts - Standard on Windows 11
        self.font_path = "C:\\Windows\\Fonts\\"

    @commands.command(name="text")
    async def text_cmd(self, ctx, font_name: str, size: int, *, message: str):
        """Usage: !text arial 40 Hello World"""
        async with ctx.typing():
            try:
                # 1. Locate the font
                # We add .ttf if the user forgot it
                if not font_name.lower().endswith(".ttf"):
                    font_name += ".ttf"
                
                full_font_path = os.path.join(self.font_path, font_name)
                
                if not os.path.exists(full_font_path):
                    return await ctx.send(f"❌ Font `{font_name}` not found in system fonts!")

                # 2. Setup Font and Calculate Canvas Size
                font = ImageFont.truetype(full_font_path, size)
                
                # Use a dummy image to calculate text dimensions
                dummy = Image.new("RGBA", (1, 1))
                draw = ImageDraw.Draw(dummy)
                # getbbox returns (left, top, right, bottom)
                bbox = draw.textbbox((0, 0), message, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

                # 3. Create the Image (Transparent background)
                # Adding a small padding so text isn't cut off
                img = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # Draw the text in White
                draw.text((10, 5), message, font=font, fill="white")

                # 4. Save to buffer (Memory only to prevent disk crashes)
                out_buffer = io.BytesIO()
                img.save(out_buffer, format="PNG")
                out_buffer.seek(0)

                await ctx.send(file=discord.File(out_buffer, filename="text.png"))

            except Exception as e:
                await ctx.send(f"⚠️ Error: {e}")

async def setup(bot):
    await bot.add_cog(TextGenerator(bot))