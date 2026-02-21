import discord
from discord.ext import commands
import io
import mido
import numpy as np
import wave
import asyncio
from functools import partial

class MidiSampler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def process_midi_pure(self, midi_data, wav_data):
        with wave.open(io.BytesIO(wav_data), 'rb') as wf:
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            dtype = np.int16 if sample_width == 2 else np.uint8
            raw_samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype=dtype).astype(np.float32)

        mid = mido.MidiFile(file=io.BytesIO(midi_data))
        total_samples = int(sample_rate * min(mid.length, 60))
        output_buffer = np.zeros(total_samples + sample_rate, dtype=np.float32)

        current_time_samples = 0
        notes_processed = 0
        
        # --- CUTOFF SETTING ---
        # Limits bleeding. 0.3 = 300ms. 
        max_note_len = int(sample_rate * 0.3) 

        for msg in mid:
            current_time_samples += int(msg.time * sample_rate)
            if current_time_samples >= len(output_buffer): break
            
            if msg.type == 'note_on' and msg.velocity > 0:
                if notes_processed >= 10000: break # Safety limit
                
                shift_factor = 2 ** ((msg.note - 60) / 12.0)
                indices = np.arange(0, len(raw_samples), shift_factor).astype(int)
                indices = indices[indices < len(raw_samples)]
                
                # Apply cutoff and fade
                pitched_note = raw_samples[indices][:max_note_len]
                if len(pitched_note) > 100:
                    fade_len = 100
                    pitched_note[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)

                pitched_note *= (msg.velocity / 127.0)

                end_pos = current_time_samples + len(pitched_note)
                if end_pos > len(output_buffer):
                    pitched_note = pitched_note[:len(output_buffer) - current_time_samples]
                    end_pos = len(output_buffer)
                
                output_buffer[current_time_samples:end_pos] += pitched_note
                notes_processed += 1

        # Normalize to max volume (prevents distortion/clipping)
        max_val = np.max(np.abs(output_buffer))
        if max_val > 0:
            output_buffer = (output_buffer / max_val) * 32767

        output_buffer = output_buffer.astype(np.int16)

        out_buf = io.BytesIO()
        with wave.open(out_buf, 'wb') as out_wf:
            out_wf.setnchannels(1)
            out_wf.setsampwidth(2)
            out_wf.setframerate(sample_rate)
            out_wf.writeframes(output_buffer.tobytes())
        
        out_buf.seek(0)
        return out_buf, notes_processed # Return BOTH values here

    @commands.command(name="midi", aliases=["midisample"])
    async def midisample(self, ctx):
        if len(ctx.message.attachments) < 2:
            return await ctx.send("❓ Attach **1 MIDI** file and **1 WAV** sample!")

        midi_data = None
        wav_data = None

        for att in ctx.message.attachments:
            if att.filename.lower().endswith(('.mid', '.midi')):
                midi_data = await att.read()
            elif att.filename.lower().endswith('.wav'):
                wav_data = await att.read()

        if not midi_data or not wav_data:
            return await ctx.send("❌ I need a `.mid` and a `.wav` file!")

        msg = await ctx.send("🎹 Rendering MIDI with Note Cutoff...")

        try:
            loop = asyncio.get_event_loop()
            # Now result, count will unpack correctly
            result, count = await loop.run_in_executor(
                None, 
                partial(self.process_midi_pure, midi_data, wav_data)
            )
            
            await ctx.send(
                content=f"✅ Rendered **{count}** notes with cutoff.",
                file=discord.File(result, filename="sampled_midi.wav")
            )
            await msg.delete()
        except Exception as e:
            await ctx.send(f"⚠️ Audio Error: {e}")

async def setup(bot):
    await bot.add_cog(MidiSampler(bot))