import asyncio
import functools
import os
import shutil
import numpy as np
import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image
from moviepy import VideoFileClip, ImageSequenceClip
from concurrent.futures import ProcessPoolExecutor

def lerp(start, end, t):
    """Linear interpolation for smooth X/Y movement."""
    return int(start + (end - start) * t)

def bake_single_frame(args):
    """CPU-heavy work: Reads one frame, edits it, saves to disk, returns PATH."""
    frame_path, start_k, end_k, f_idx, output_dir = args
    LIMIT_X, LIMIT_Y = 640, 360
    
    # Create unique baked path
    baked_path = os.path.join(output_dir, f"baked_{f_idx:04d}.png")

    with Image.open(frame_path) as base_img:
        base_img = base_img.convert("RGBA")
        
        # 1. Lerp Logic
        if start_k['f'] == end_k['f']:
            t = 1.0
        else:
            t = max(0, min(1, (f_idx - start_k['f']) / (end_k['f'] - start_k['f'])))
        
        curr_x = lerp(start_k['x'], end_k['x'], t)
        curr_y = lerp(start_k['y'], end_k['y'], t)
        
        # 2. Dynamic Loading (34.png, 59.png, etc.)
        img_path = f"./images/{start_k['img']}"
        
        if os.path.exists(img_path):
            with Image.open(img_path) as overlay:
                overlay = overlay.convert("RGBA")
                
                # Apply the -30 size reduction
                new_w = max(1, overlay.width - 30)
                new_h = max(1, overlay.height - 30)
                overlay = overlay.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # 3. THE "LAZY" CLIPPER (Hide out of bounds)
                if not (curr_x >= LIMIT_X or curr_y >= LIMIT_Y or \
                        curr_x + new_w <= 0 or curr_y + new_h <= 0):
                    base_img.alpha_composite(overlay, (curr_x, curr_y))

        # 4. Save to disk as Palette (RAM Safe)
        final_frame = base_img.convert("RGB").quantize(colors=256)
        final_frame.save(baked_path, optimize=True)
        
    return baked_path # Returns STRING, not LIST or IMAGE

class VideoBaker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_dir = "temp_sequence"
        self.baked_dir = "baked_sequence"

    def run_baker(self, input_path, instruction_file):
        output_video = "final_baked.mp4"
        
        # Cleanup
        for d in [self.temp_dir, self.baked_dir]:
            if os.path.exists(d): shutil.rmtree(d)
            os.makedirs(d)

        # 1. Load Keyframe Data
        keyframes = []
        with open(instruction_file, "r") as f:
            for line in f:
                if "|" in line:
                    f_num, img, x, y = line.strip().split("|")
                    keyframes.append({'f': int(f_num), 'img': img, 'x': int(x), 'y': int(y)})
        keyframes.sort(key=lambda k: k['f'])

        # 2. Extract Video
        with VideoFileClip(input_path) as clip:
            audio = clip.audio
            fps = clip.fps
            clip.write_images_sequence(os.path.join(self.temp_dir, "f%04d.png"), fps=fps, logger=None)
            
            extracted = sorted([os.path.join(self.temp_dir, f) for f in os.listdir(self.temp_dir) if f.endswith('.png')])
            
            # 3. Build Arguments
            bake_args = []
            for i in range(len(extracted)):
                start_k = keyframes[0]
                end_k = keyframes[-1]
                for j in range(len(keyframes) - 1):
                    if keyframes[j]['f'] <= i <= keyframes[j+1]['f']:
                        start_k, end_k = keyframes[j], keyframes[j+1]
                        break
                    elif i > keyframes[-1]['f']:
                        start_k = end_k = keyframes[-1]

                bake_args.append((extracted[i], start_k, end_k, i, self.baked_dir))

            # 4. Multi-Core Bake (Return string paths)
            with ProcessPoolExecutor(max_workers=2) as executor:
                # result is an iterator of strings
                result = executor.map(bake_single_frame, bake_args)
                baked_frame_paths = list(result) 

            # 5. Render Final Result (Uses paths)
            new_clip = ImageSequenceClip(baked_frame_paths, fps=fps)
            if audio:
                new_clip = new_clip.with_audio(audio)
            
            new_clip.write_videofile(output_video, codec="libx264", preset="ultrafast", logger=None)
            return output_video

    @commands.hybrid_command(name="bake")
    async def bake(self, ctx):
        if ctx.interaction: await ctx.defer()
        await ctx.send("⚡ **Bake Started.** Processing 990 frames...")
        
        loop = asyncio.get_event_loop()
        try:
            if not os.path.exists("input.mp4"):
                return await ctx.send("❌ Error: `input.mp4` not found.")
            
            task = functools.partial(self.run_baker, "input.mp4", "cocielochaves1.txt")
            output_file = await loop.run_in_executor(None, task)
            await ctx.send(file=discord.File(output_file))
        except Exception as e:
            await ctx.send(f"⚠️ Bake Failed: {e}")
        finally:
            for d in [self.temp_dir, self.baked_dir]:
                if os.path.exists(d): shutil.rmtree(d)

async def setup(bot):
    await bot.add_cog(VideoBaker(bot))