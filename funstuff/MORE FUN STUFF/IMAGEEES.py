import discord
from discord.ext import commands
import aiohttp
import io
import struct
import json

class ImageBridge(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="renderjson")
    async def render(self, ctx, *, json_config: str):

        if not ctx.message.attachments:
            return await ctx.send("Attach an image.")

        try:
            config = json.loads(json_config)
        except:
            return await ctx.send("Invalid JSON.")

        attachment = ctx.message.attachments[0]
        image_bytes = await attachment.read()

        json_bytes = json.dumps(config).encode()

        payload = struct.pack(">I", len(json_bytes)) + json_bytes + image_bytes

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8080/process",
                data=payload
            ) as resp:

                if resp.status != 200:
                    return await ctx.send("Processing failed.")

                result = await resp.read()

        await ctx.send(file=discord.File(io.BytesIO(result), "result.png"))

async def setup(bot):
    await bot.add_cog(ImageBridge(bot))