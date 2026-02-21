import random
import os
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageOps
import discord
import io

DICT_PATH = "./what/dict.txt"
IMAGE_SIZE = (800, 500)
MAX_WORDS = 12
MAX_ATTEMPTS = 50


def boxes_overlap(a, b):
    return not (
        a[2] <= b[0] or
        a[0] >= b[2] or
        a[3] <= b[1] or
        a[1] >= b[3]
    )


def load_font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()


class RandomWords(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="whatever1")
    async def whatever1(self, ctx):
        await ctx.send("🛠 generating image…")

        if not os.path.exists(DICT_PATH):
            await ctx.send("❌ ./what/dict.txt not found")
            return

        with open(DICT_PATH, "r", encoding="utf-8") as f:
            words = [w.strip() for w in f if w.strip()]

        if not words:
            await ctx.send("❌ dict.txt is empty")
            return

        img = Image.new("RGBA", IMAGE_SIZE, (20, 20, 20, 255))
        placed_boxes = []

        for _ in range(MAX_WORDS):
            word = random.choice(words)

            for _ in range(MAX_ATTEMPTS):
                font_size = random.randint(20, 60)
                font = load_font(font_size)

                temp = Image.new("RGBA", (1, 1))
                d = ImageDraw.Draw(temp)
                bbox = d.textbbox((0, 0), word, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]

                text_img = Image.new("RGBA", (w + 10, h + 10), (0, 0, 0, 0))
                d = ImageDraw.Draw(text_img)
                d.text((5, 5), word, fill="white", font=font)

                if random.choice((True, False)):
                    text_img = ImageOps.mirror(text_img)
                if random.choice((True, False)):
                    text_img = ImageOps.flip(text_img)

                text_img = text_img.rotate(random.randint(0, 360), expand=True)

                tw, th = text_img.size
                if tw >= IMAGE_SIZE[0] or th >= IMAGE_SIZE[1]:
                    continue

                x = random.randint(0, IMAGE_SIZE[0] - tw)
                y = random.randint(0, IMAGE_SIZE[1] - th)

                box = (x, y, x + tw, y + th)

                if any(boxes_overlap(box, b) for b in placed_boxes):
                    continue

                img.alpha_composite(text_img, (x, y))
                placed_boxes.append(box)
                break

        buf = io.BytesIO()
        img.save(buf, "PNG")
        buf.seek(0)

        await ctx.send(file=discord.File(buf, "random_words.png"))


async def setup(bot):
    await bot.add_cog(RandomWords(bot))
