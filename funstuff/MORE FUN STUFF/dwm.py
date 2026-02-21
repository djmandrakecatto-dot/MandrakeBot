import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io

class AeroWindow:
    def __init__(self, title="System", content="Hello", x=50, y=50):
        self.x = x
        self.y = y
        self.width = 400
        self.height = 250
        self.workspace_size = (1366, 768)
        self.title = title
        self.content = content
        self.accent_color = (0, 102, 204, 160)

    def update_position(self, x: int, y: int):
        self.x = max(0, min(x, self.workspace_size[0] - self.width))
        self.y = max(0, min(y, self.workspace_size[1] - self.height))

    def __call__(self):
        canvas = Image.new("RGBA", self.workspace_size, (0, 0, 0, 0))
        window_surf = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        w_draw = ImageDraw.Draw(window_surf)

        # Window Body
        w_draw.rounded_rectangle([0, 0, self.width, self.height], radius=12, 
                                 fill=self.accent_color, outline=(255, 255, 255, 200), width=2)
        
        # Gloss Effect
        gloss = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(gloss)
        g_draw.ellipse([-50, -100, self.width + 50, self.height // 2], fill=(255, 255, 255, 50))
        window_surf = Image.alpha_composite(window_surf, gloss)

        # Safety Font Loading
        try:
            # Try to find a system font, fallback to default if it fails
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(window_surf)
        draw.text((15, 8), self.title, font=font, fill=(255, 255, 255, 200))
        draw.text((20, 60), self.content, font=font, fill=(255, 255, 255, 255))

        canvas.paste(window_surf, (self.x, self.y), window_surf)
        
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

class PositionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ui = AeroWindow()

    def force_stop_system(self):
        """Helper to handle your crash prevention rules."""
        # Insert your code here to stop audio and index
        print("System: Audio and Index stopped for generation.")

    @commands.command(name="move")
    async def move(self, ctx, x: int, y: int):
        print(f"Move command triggered: x={x}, y={y}")
        
        # PREVENT CRASH
        self.force_stop_system()
        
        try:
            self.ui.update_position(x, y)
            data = self.ui()
            
            file = discord.File(fp=data, filename="aero.png")
            await ctx.send(f"Window repositioned to `{x}, {y}`", file=file)
        except Exception as e:
            print(f"Error during image gen: {e}")
            await ctx.send(f"Failed to generate window: {e}")

async def setup(bot):
    await bot.add_cog(PositionCog(bot))