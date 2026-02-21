import discord
from discord.ext import commands
from PIL import Image, ImageOps, ImageEnhance, ImageFilter # Added missing imports
import io
import aiohttp

MAX_SIZE = 5_000_000  # 5MB

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- helpers ----------

    async def load_image(self, ctx, image_url):
        # Check attachments first
        if ctx.message.attachments:
            att = ctx.message.attachments[0]
            if att.size > MAX_SIZE:
                return None
            return await att.read()

        # Check URL
        if image_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url, timeout=10) as resp:
                        if resp.status != 200:
                            return None
                        if resp.content_length and resp.content_length > MAX_SIZE:
                            return None
                        return await resp.read()
            except Exception:
                return None

        return None

    async def send_image(self, ctx, img, name):
        with io.BytesIO() as buf: # Using context manager for safety
            img.save(buf, format="PNG")
            buf.seek(0)
            await ctx.send(file=discord.File(buf, name))

    # ---------- commands ----------

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def fun_1(self, ctx, image_url: str = None):
        data = await self.load_image(ctx, image_url)
        if not data:
            await ctx.send("❌ Send an image or link (max 5MB).")
            return

        base = Image.open(io.BytesIO(data)).convert("RGBA")
        top = base.resize((512, 512))
        bl = base.resize((256, 256))
        br = base.resize((256, 256))

        canvas = Image.new("RGBA", (512, 768))
        canvas.paste(top, (0, 0))
        canvas.paste(bl, (0, 512))
        canvas.paste(br, (256, 512))

        await self.send_image(ctx, canvas, "fun_1.png")

    @commands.command()
    async def mirror(self, ctx, image_url: str = None):
        data = await self.load_image(ctx, image_url)
        if not data: return await ctx.send("❌ No image.")

        img = Image.open(io.BytesIO(data))
        img = ImageOps.mirror(img)
        await self.send_image(ctx, img, "mirror.png")

    @commands.command()
    async def invert(self, ctx, image_url: str = None):
        data = await self.load_image(ctx, image_url)
        if not data: return await ctx.send("❌ No image.")

        img = Image.open(io.BytesIO(data)).convert("RGB")
        img = ImageOps.invert(img)
        await self.send_image(ctx, img, "invert.png")

    @commands.command()
    async def pixel(self, ctx, image_url: str = None):
        data = await self.load_image(ctx, image_url)
        if not data: return await ctx.send("❌ No image.")

        img = Image.open(io.BytesIO(data))
        small = img.resize((64, 64), Image.NEAREST)
        pixelated = small.resize(img.size, Image.NEAREST)
        await self.send_image(ctx, pixelated, "pixel.png")

    @commands.command()
    async def stack(self, ctx, image_url: str = None):
        data = await self.load_image(ctx, image_url)
        if not data: return await ctx.send("❌ No image.")

        img = Image.open(io.BytesIO(data)).resize((512, 512)).convert("RGBA")
        canvas = Image.new("RGBA", (512, 1536))
        canvas.paste(img, (0, 0))
        canvas.paste(img, (0, 512))
        canvas.paste(img, (0, 1024))

        await self.send_image(ctx, canvas, "stack.png")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def deepfry(self, ctx, image_url: str = None):
        data = await self.load_image(ctx, image_url)
        if not data:
            await ctx.send("❌ Send an image or link (max 5MB).")
            return

        img = Image.open(io.BytesIO(data)).convert("RGB")

        # Now these work because of the new imports:
        img = ImageEnhance.Contrast(img).enhance(2.5)
        img = ImageEnhance.Color(img).enhance(3.0)
        img = img.filter(ImageFilter.SHARPEN)
        img = ImageEnhance.Sharpness(img).enhance(2.0)

        await self.send_image(ctx, img, "deepfry.png")

    @commands.command()
    async def zoom(self, ctx, image_url: str = None):
        data = await self.load_image(ctx, image_url)
        if not data: return await ctx.send("❌ No image.")

        img = Image.open(io.BytesIO(data))
        w, h = img.size
        crop = img.crop((w//4, h//4, w*3//4, h*3//4))
        crop = crop.resize(img.size)
        await self.send_image(ctx, crop, "zoom.png")

async def setup(bot):
    await bot.add_cog(Fun(bot))