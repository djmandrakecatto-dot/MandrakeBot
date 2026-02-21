import discord
from discord.ext import commands
from PIL import Image
import io
import os

class ImageFun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="fun_2")
    async def fun_2(self, ctx):
        if not ctx.message.attachments:
            return await ctx.send("🖼️ Please attach an image!")

        attachment = ctx.message.attachments[0]
        bg_path = "images/paper_on_fire.png"

        if not os.path.exists(bg_path):
            return await ctx.send(f"❌ Missing: `{bg_path}`")

        async with ctx.typing():
            try:
                # 1. Open Background
                bg = Image.open(bg_path).convert("RGBA")
                
                # 2. Process User Image
                user_img_bytes = await attachment.read()
                user_img = Image.open(io.BytesIO(user_img_bytes)).convert("RGBA")

                # Target dimensions (from 50,74 to 230,311)
                target_w = 180 
                target_h = 237

                # 3. Resize first
                user_resized = user_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

                # 4. Rotate by 3 degrees
                # expand=True ensures the corners aren't cut, but False keeps the size strict
                # We'll use expand=True then re-center it slightly for the best look
                user_rotated = user_resized.rotate(-2, resample=Image.Resampling.BICUBIC, expand=True)

                # 5. Paste onto background at (50, 74)
                # Note: Because expand=True makes the image slightly larger, 
                # we offset it by a few pixels so the center stays at 50, 74
                offset_x = (user_rotated.width - target_w) // 2
                offset_y = (user_rotated.height - target_h) // 2
                
                bg.paste(user_rotated, (50 - offset_x, 74 - offset_y), user_rotated)

                # 6. Output
                out_buffer = io.BytesIO()
                bg.save(out_buffer, format="PNG")
                out_buffer.seek(0)

                await ctx.send(file=discord.File(out_buffer, filename="fire_result.png"))

            except Exception as e:
                await ctx.send(f"⚠️ Error: {e}")

async def setup(bot):
    await bot.add_cog(ImageFun(bot))