import discord
from discord.ext import commands
import numpy as np
import io
import wave
import traceback
import psutil
import re

class Bytebeat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sample_rate = 8000

    def translate_formula(self, formula):
        """ 
        Smarter Translation: 
        Converts (a ? b : c) into np.where(a, b, c) for NumPy compatibility.
        """
        # This regex looks for the C-style ternary and wraps it in np.where
        # Input: (t%16?2:6) -> Output: np.where(t%16, 2, 6)
        translated = re.sub(r'([^?()]+)\s*\?\s*([^:()]+)\s*:\s*([^()]+)', r'np.where(\1, \2, \3)', formula)
        return translated

    def generate_audio(self, formula, duration=15, unsigned=True):
        sample_rate = 22050
        t_raw = np.arange(0, sample_rate * duration, dtype=np.float64)
        
        # We define 't' here so the user doesn't have to scale it themselves
        t_scaled = t_raw * (8000.0 / 22050.0)

        # In your generate_audio function:
        safe_dict = {
            't': t_scaled,
            'np': np,
            'abs': np.abs,
            'I': lambda x: np.floor(np.nan_to_num(x)).astype(np.int64), # Renamed to 'I'
            'where': np.where
        }
        
        try:
            # We allow the formula to be evaluated directly
            result = eval(formula, {"__builtins__": None}, safe_dict)
            
            # Wrap to 8-bit and follow the Endian Rule (byte-by-byte)
            result = np.array(result, dtype=np.int64) & 255
            audio_data = result.astype(np.uint8)

            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(1)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            
            buffer.seek(0)
            return buffer
        except Exception as e:
            raise e

    async def run_bytebeat(self, ctx, formula, unsigned):
        # Resource Guard (90% RAM Limit)
        if psutil.virtual_memory().percent > 90.0:
            return await ctx.send("🚨 **RAM Guard**: System is too heavy to synthesize.")

        await ctx.send(f"🔨 **Synthesizing...**")

        try:
            # Run in executor to prevent "Heartbeat Blocked"
            loop = self.bot.loop
            buffer = await loop.run_in_executor(None, self.generate_audio, formula, 5, unsigned)
            
            filename = "ubytebeat.wav" if unsigned else "bytebeat.wav"
            await ctx.send(file=discord.File(buffer, filename=filename))

        except Exception:
            # 📋 Send the Traceback to user if the math is wrong
            error_trace = traceback.format_exc()
            await ctx.send(f"❌ **Formula Error!** Traceback:\n```python\n{error_trace[-1900:]}\n```")

    @commands.command(name="bytebeat")
    async def bytebeat(self, ctx, *, formula: str):
        await self.run_bytebeat(ctx, formula, unsigned=False)

    @commands.command(name="ubytebeat")
    async def ubytebeat(self, ctx, *, formula: str):
        await self.run_bytebeat(ctx, formula, unsigned=True)

async def setup(bot):
    await bot.add_cog(Bytebeat(bot))