import discord
from discord.ext import commands
import http.client
import uuid
import os
import asyncio

JAVA_SERVER_IP = "26.199.50.19"
JAVA_SERVER_PORT = 8081
MAX_UPLOAD = 20 * 1024 * 1024  # 20 MB (images)

class Render(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="render")
    async def render(self, ctx, manip_type: str = "grayscale", angle: float = 0):
        if not ctx.message.attachments:
            return await ctx.reply("📎 Upload an image with the command.")

        att = ctx.message.attachments[0]

        if att.size > MAX_UPLOAD:
            return await ctx.reply("❌ File too big (max 20MB).")

        if not att.content_type or not att.content_type.startswith("image/"):
            return await ctx.reply("❌ Only images are supported.")

        await ctx.reply(f"🧠 Processing image (`{manip_type}`)...")

        image_bytes = await att.read()

        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(image_bytes)),
            "X-Manip-Type": manip_type,
            "X-Angle": str(angle)
        }

        # Send to Java renderer
        conn = http.client.HTTPConnection(
            JAVA_SERVER_IP,
            JAVA_SERVER_PORT,
            timeout=60
        )

        try:
            conn.request("POST", "/process", body=image_bytes, headers=headers)
            res = conn.getresponse()
            result_bytes = res.read()
        finally:
            conn.close()

        if res.status != 200:
            return await ctx.reply("❌ Image processing failed.")

        # Save temp output
        out_path = f"/tmp/render_{uuid.uuid4().hex}.png"
        with open(out_path, "wb") as f:
            f.write(result_bytes)

        # Send back to Discord
        try:
            await ctx.reply(file=discord.File(out_path))
        except Exception as e:
            await ctx.reply(f"❌ Failed to send image: {e}")
        finally:
            try:
                os.remove(out_path)
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(Render(bot))