import discord
from discord.ext import commands
import io, os, random
from PIL import Image, ImageDraw, ImageFont
import asyncio

class BSODSim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qr_path = "./images/bsodqr.png"
        self.font_path = "./font/2.ttf"

    @commands.command(name="slowbsod")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def slowbsod(self, ctx):
        async with ctx.typing():
            try:
                # 1. Setup Canvas
                width, height = 400, 225 
                blue = (0, 120, 215)
                white = (255, 255, 255)
                
                # Fonts (Segoe UI style)
                try:
                    big_font = ImageFont.truetype(self.font_path, 50)
                    reg_font = ImageFont.truetype(self.font_path, 15)
                except:
                    big_font = None
                    reg_font = None

                canvas = Image.new("RGB", (width, height), (0, 0, 0))
                draw = ImageDraw.Draw(canvas)
                
                frames = []
                durations = []

                # --- LAYER 1: Scanning Blue Blocks (0.01 - 0.03 speed) ---
                block_w, block_h = 40, 20
                for y in range(0, height, block_h):
                    for x in range(0, width, block_w):
                        draw.rectangle([x, y, x + block_w, y + block_h], fill=blue)
                        frames.append(canvas.copy())
                        # Randomize speed between 10ms (0.01) and 30ms (0.03)
                        durations.append(random.randint(10, 30))

                # --- LAYER 2: Sad Face ---
                draw.text((30, 20), ":(", fill=white, font=big_font)
                frames.append(canvas.copy())
                durations.append(600) # Long pause for the impact

                # --- LAYER 3: Text Lines ---
                lines = [
                    "Your PC ran into a problem and needs to restart.",
                    "We're just collecting some error info, and then",
                    "we'll restart for you.",
                    "", 
                    "100% complete"
                ]
                for i, line in enumerate(lines):
                    if line:
                        draw.text((30, 85 + (i * 18)), line, fill=white, font=reg_font)
                    frames.append(canvas.copy())
                    # Random delay for text "stutter"
                    durations.append(random.randint(100, 300))

                # --- LAYER 4: QR Code ---
                if os.path.exists(self.qr_path):
                    try:
                        qr = Image.open(self.qr_path).convert("RGBA").resize((50, 50))
                        canvas.paste(qr, (30, 165), qr)
                    except:
                        draw.rectangle([30, 165, 80, 215], outline=white)
                else:
                    draw.rectangle([30, 165, 80, 215], outline=white)
                
                frames.append(canvas.copy())
                durations.append(3000) # Final frame stays for 3 seconds

                # --- Compilation (HP-Note Safe) ---
                out = io.BytesIO()
                frames[0].save(
                    out, 
                    format="GIF", 
                    save_all=True, 
                    append_images=frames[1:], 
                    duration=durations, 
                    loop=0
                )
                out.seek(0)

                await ctx.send(file=discord.File(out, filename="bsod_crash.gif"))

            except Exception as e:
                await ctx.send(f"⚠️ Simulation Error: {e}")

async def setup(bot):
    await bot.add_cog(BSODSim(bot))