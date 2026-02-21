import discord
from discord.ext import commands
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps

class ImageTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.font_path = "./font/1.ttf"

    @commands.command(name="caption")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def caption(self, ctx, *, text: str = None):
        """Usage: !caption <text> (attach an image)"""
        if not ctx.message.attachments:
            return await ctx.send("🖼️ Please attach an image to caption!")
        
        if not text:
            return await ctx.send("✍️ Please provide the text for the caption.")

        async with ctx.typing():
            try:
                # 1. Load Image
                attachment = ctx.message.attachments[0]
                img_bytes = await attachment.read()
                img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

                # 2. HP-Note Guard: Resize if too big (max 800px)
                if max(img.size) > 800:
                    img.thumbnail((800, 800))

                draw = ImageDraw.Draw(img)
                w, h = img.size

                # 3. Font Scaling (approx 1/10th of image height)
                font_size = int(h / 10)
                try:
                    font = ImageFont.truetype(self.font_path, font_size)
                except:
                    font = ImageFont.load_default()

                # 4. Text Wrapping & Centering
                # We split text by '|' if the user wants top and bottom
                parts = text.split("|")
                
                def draw_text_with_outline(content, y_pos):
                    # Calculate text size using textbbox (Pillow 9.2.0+)
                    bbox = draw.textbbox((0, 0), content, font=font)
                    tw = bbox[2] - bbox[0]
                    tx = (w - tw) / 2
                    
                    # Draw Black Outline (Stroke)
                    stroke = 2
                    for ox in range(-stroke, stroke + 1):
                        for oy in range(-stroke, stroke + 1):
                            draw.text((tx + ox, y_pos + oy), content, font=font, fill="black")
                    
                    # Draw White Text
                    draw.text((tx, y_pos), content, font=font, fill="white")

                # If user used "Top | Bottom", split them
                if len(parts) > 1:
                    draw_text_with_outline(parts[0].strip().upper(), 10) # Top
                    draw_text_with_outline(parts[1].strip().upper(), h - font_size - 20) # Bottom
                else:
                    # Default to bottom
                    draw_text_with_outline(text.upper(), h - font_size - 20)

                # 5. Save and Send
                out = io.BytesIO()
                img.convert("RGB").save(out, format="JPEG", quality=85)
                out.seek(0)

                await ctx.send(file=discord.File(out, filename="caption.jpg"))

            except Exception as e:
                await ctx.send(f"⚠️ Caption Error: {e}")

async def setup(bot):
    await bot.add_cog(ImageTools(bot))