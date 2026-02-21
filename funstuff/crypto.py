import discord
from discord.ext import commands
import platform
import struct
import hashlib
import math
import psutil
import asyncio

class TotalOperatorMiner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bit_size = 64 if "64" in platform.architecture()[0] else 32
        self.pack_fmt = 'Q' if self.bit_size == 64 else 'I'
        self.mask = (2**self.bit_size) - 1  # Ensures we stay in bit-range

    def deep_scramble(self, seed):
        """Recompiles hash to hard math using ALL operators."""
        curr = seed & self.mask #
        
        for i in range(50000):
            # 1. Generate the Cryptographic Hash
            h_bytes = hashlib.sha256(str(curr).encode()).digest()
            h_int = int.from_bytes(h_bytes[:8], 'big') & self.mask #
            
            # 2. Use ALL Math & Bitwise Operators
            # Arithmetic: +, -, *, //, %, ** (limited)
            # Bitwise: &, |, ^, ~, <<, >>
            
            # Scramble Step A: Arithmetic
            curr = (curr + h_int) % self.mask
            curr = (curr * (i + 1)) // ( (i % 5) + 1 ) # Floor division
            curr = (curr - (h_int >> 2)) & self.mask # Subtraction + Shift
            
            # Scramble Step B: Logic Gates
            curr ^= h_int  # XOR
            curr |= (i << 1) & self.mask # OR + Left Shift
            curr &= ~(i >> 1) & self.mask # AND + NOT + Right Shift
            
            # Scramble Step C: Complex Recompilation
            if i % 10 == 0:
                # Modulo and Exponentiation (kept small to prevent crash)
                curr = (curr ** 2) % self.mask if curr < 10**6 else curr % self.mask

        return curr

    @commands.hybrid_command(name="recompile_full")
    async def recompile_full(self, ctx, input_val: int):
        """Uses ALL operators to recompile hash into scrambled hard math."""
        await ctx.send(f"⛏️ **Full-Operator Recompilation ({self.bit_size}-bit)...**")
        
        loop = asyncio.get_event_loop()
        # run_in_executor protects your audio/index from crashing
        result = await loop.run_in_executor(None, self.deep_scramble, input_val)
        
        # Enforce Endian rule and Architecture compilation
        final = struct.unpack(self.pack_fmt, struct.pack(self.pack_fmt, result))[0]
        
        await ctx.send(f"✅ **Mentioned:** `{input_val}`\n💎 **Fully Compiled:** `{final}`")

async def setup(bot):
    await bot.add_cog(TotalOperatorMiner(bot))