import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import asyncio

class MonochromeImage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.font_path = "./font/1.ttf"

    @commands.command(name="imgtext")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def img_text(self, ctx, center_text: str, *, left_text: str):
        if not ctx.message.attachments:
            return await ctx.send("❌ Please attach an image!")

        # 80+ user protection: Queue the task
        async with self.bot.process_queue:
            await ctx.send("🎞️ Processing monochrome image... please wait.")
            
            # Download Attachment and Avatar
            img_bytes = await ctx.message.attachments[0].read()
            avatar_bytes = await ctx.author.display_avatar.with_format("png").read()
            
            loop = asyncio.get_event_loop()
            result_buffer = await loop.run_in_executor(
                None, self.process_monochrome, img_bytes, avatar_bytes, center_text, left_text
            )
            
            file = discord.File(fp=result_buffer, filename="monochrome_result.png")
            await ctx.send(file=file)

    def process_monochrome(self, img_bytes, av_bytes, center_txt, left_txt):
        # 1. Open Base Image and convert to Black & White ("L" mode)
        img = Image.open(io.BytesIO(img_bytes)).convert("L")
        # Convert back to RGB so we can add colored text if we wanted, 
        # but since we want monochrome, it stays gray.
        img = img.convert("RGB") 
        W, H = img.size
        
        # 2. Open and Resize Avatar, then convert to Black & White
        avatar = Image.open(io.BytesIO(av_bytes)).convert("L")
        av_size = int(H / 6)
        avatar = avatar.resize((av_size, av_size), Image.Resampling.LANCZOS)
        avatar = avatar.convert("RGB") # Matches base image mode

        draw = ImageDraw.Draw(img)

        # Load Font 1.ttf
        try:
            font_center = ImageFont.truetype(self.font_path, int(H/10))
            font_left = ImageFont.truetype(self.font_path, int(H/20))
        except:
            font_center = font_left = ImageFont.load_default()

        # 3. Draw Center Text (White with Black Outline for contrast)
        bbox = draw.textbbox((0, 0), center_txt, font=font_center)
        w_c, h_c = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((W - w_c) / 2, (H - h_c) / 2), center_txt, font=font_center, fill="white", stroke_width=2, stroke_fill="black")

        # 4. Paste Monochrome Avatar
        img.paste(avatar, (20, 20))

        # 5. Draw Left Text
        text_x = 20 + av_size + 10
        draw.text((text_x, 20), left_txt, font=font_left, fill="white", stroke_width=1, stroke_fill="black")

        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

async def setup(bot):
    await bot.add_cog(MonochromeImage(bot))