import discord
from discord.ext import commands
import platform
import struct
import hashlib

class HashTranslator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Detect 32/64 bit for the Endian Rule
        self.arch_bits = 64 if "64" in platform.architecture()[0] else 32
        self.pack_fmt = 'Q' if self.arch_bits == 64 else 'I'

    def translate_hash_to_math(self, message):
        """Translates a message hash into hardware-compiled math."""
        # 1. Create the base hash
        hash_obj = hashlib.sha256(message.encode())
        hex_digest = hash_obj.hexdigest()
        
        # 2. Slice the hash into 4-byte or 8-byte chunks (Translation)
        # We use the Endian rule to ensure it matches your PC architecture
        chunk_size = 8 if self.arch_bits == 64 else 4
        raw_bytes = hash_obj.digest()[:chunk_size]
        
        # 3. Recompile the bytes into a 'Hard Math' integer
        # This converts the 'Message Hash' into a compiled numerical result
        compiled_int = struct.unpack(self.pack_fmt, raw_bytes)[0]
        
        # 4. Scramble using all operators to 'verify' the translation
        scrambled = (compiled_int << 2) ^ (compiled_int >> 1)
        scrambled = (scrambled * 31) % (2**self.arch_bits)
        
        return hex_digest, compiled_int, scrambled

    @commands.hybrid_command(name="translate_hash")
    async def translate_hash(self, ctx, *, message: str):
        """Translates a text message hash into compiled hard math."""
        # Force stop logic mentioned in constraints should be handled 
        # outside this logic to prevent bot hang.
        
        digest, compiled, math_result = self.translate_hash_to_math(message)
        
        embed = discord.Embed(title="📜 Hash Translation Successful", color=0x2f3136)
        embed.add_field(name="Original Message", value=f"`{message}`", inline=False)
        embed.add_field(name="SHA-256 Digest", value=f"`{digest[:16]}...`", inline=True)
        embed.add_field(name=f"Compiled ({self.arch_bits}-bit)", value=f"`{compiled}`", inline=True)
        embed.add_field(name="Scrambled Result", value=f"`{math_result}`", inline=False)
        embed.set_footer(text=f"Hardware: HP-Note | Endian: Little")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HashTranslator(bot))