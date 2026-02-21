# ===============================
# Secure Roblox-like Luau VM Cog for Discord
# Command: !luau (with .luau script attachment + optional assets)
# ===============================

import os
import time
import hashlib
import discord
from discord.ext import commands
from lupa import LuaRuntime
from PIL import Image
from pygltflib import GLTF2

# ===============================
# CONFIG
# ===============================

CACHE_DIR = "cache"
CACHE_TTL = 300          # 5 minutes
MAX_IMAGE_SIZE = 1024
MAX_ASSET_SIZE = 8 * 1024 * 1024  # 8 MB per asset

# ===============================
# ERROR CODES
# ===============================

NO_MESSAGE_OR_INTERACTABLES = 0
OK = 1
INVALID_RETURN_TYPE = -1

# ===============================
# SHARED LUA RUNTIME (SANDBOXED)
# ===============================
lua = LuaRuntime(unpack_returned_tuples=True)

# Aggressive sandboxing — remove almost everything dangerous
lua_globals = lua.globals()
dangerous = [
    'io', 'os', 'package', 'debug', 'loadfile', 'dofile', 'load', 'loadstring',
    'collectgarbage', 'newproxy', 'setfenv', 'getfenv', 'rawget', 'rawset'
]

for item in dangerous:
    if item in lua_globals:
        del lua_globals[item]

# Also remove require if you don't want any module loading
if 'require' in lua_globals:
    del lua_globals['require']

# ===============================
# UTILITIES
# ===============================

def cleanup_cache():
    now = time.time()
    for filename in os.listdir(CACHE_DIR):
        path = os.path.join(CACHE_DIR, filename)
        if os.path.isfile(path) and now - os.path.getmtime(path) > CACHE_TTL:
            try:
                os.remove(path)
            except:
                pass

def safe_path(path: str) -> str:
    """Prevent path traversal"""
    abs_path = os.path.abspath(path)
    abs_cache = os.path.abspath(CACHE_DIR)
    if not abs_path.startswith(abs_cache):
        raise ValueError("Path traversal attempt detected")
    return path

# ===============================
# IMAGE / GIF ALLOCATOR
# ===============================

def allocate_image(fmt="bmp", width=512, height=512):
    width = min(int(width), MAX_IMAGE_SIZE)
    height = min(int(height), MAX_IMAGE_SIZE)

    key = hashlib.sha256(f"{fmt}{width}{height}{time.time()}".encode()).hexdigest()[:16]
    path = os.path.join(CACHE_DIR, f"{key}.{fmt}")

    if os.path.exists(path):
        return path

    try:
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        img.save(path, format=fmt.upper())
        return path
    except Exception as e:
        raise RuntimeError(f"Failed to create image: {e}")

# ===============================
# 3D MODEL VALIDATOR
# ===============================

def load_model(model_info: dict):
    path = model_info.get("path")
    mtype = model_info.get("type", "").lower()

    if not path:
        raise ValueError("No model path provided")

    safe_path(path)  # enforce cache dir only

    if not os.path.exists(path):
        raise ValueError("Model file not found")

    if mtype == "obj":
        if not path.lower().endswith(".obj"):
            raise ValueError("File does not have .obj extension")
        # Very basic sanity check
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read(1024)
            if "v " not in content and "f " not in content:
                raise ValueError("Doesn't look like a valid OBJ file")
        return path

    elif mtype in ("gltf", "glb"):
        if not path.lower().endswith((".gltf", ".glb")):
            raise ValueError("File does not have .gltf / .glb extension")
        try:
            GLTF2().load(path)
            return path
        except Exception as e:
            raise ValueError(f"Invalid GLTF/GLB: {e}")

    else:
        raise ValueError("Unsupported model type (only obj, gltf, glb allowed)")

# ===============================
# LUAU EXECUTION
# ===============================

# ===============================
# LUAU EXECUTION (fixed version)
# ===============================

def run_luau_script(code: str, attachment_info: dict):
    cleanup_cache()

    try:
        # Create a proper Lua table for the top-level info
        lua_info = lua.table()

        lua_info["script"] = attachment_info["script"]
        lua_info["has_image"] = attachment_info["has_image"]
        lua_info["has_gif"] = attachment_info["has_gif"]
        lua_info["has_bitmap"] = attachment_info["has_bitmap"]

        # Convert the assets list to a real Lua table (1-based)
        lua_assets = lua.table()
        for i, asset_dict in enumerate(attachment_info["assets"], 1):
            lua_asset = lua.table()
            for key, value in asset_dict.items():
                lua_asset[key] = value  # strings, ints, bools convert automatically
            lua_assets[i] = lua_asset

        lua_info["assets"] = lua_assets

        # Now execute the script and call it with the clean Lua table
        chunk = lua.execute(code)
        result = chunk(lua_info) if callable(chunk) else chunk

        if not isinstance(result, dict):  # Note: this is Python dict (lupa converts Lua table → dict)
            return INVALID_RETURN_TYPE, {"error": "Script must return a table"}

        output = {}
        has_content = False

        if msg := result.get("message"):
            output["message"] = str(msg)
            has_content = True

        if result.get("image") or result.get("bitmap"):
            cfg = result.get("image") or result.get("bitmap") or {}
            w = cfg.get("width", 512)
            h = cfg.get("height", 512)
            output["image"] = allocate_image("bmp", w, h)
            has_content = True

        if gif_cfg := result.get("gif"):
            w = gif_cfg.get("width", 512)
            h = gif_cfg.get("height", 512)
            output["gif"] = allocate_image("gif", w, h)
            has_content = True

        if model := result.get("model3d"):
            output["model3d"] = load_model(model)
            has_content = True

        if not has_content:
            return NO_MESSAGE_OR_INTERACTABLES, None

        return OK, output

    except Exception as e:
        return INVALID_RETURN_TYPE, {"error": str(e)}
# ===============================
# COG
# ===============================

class LuauVMCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.makedirs(CACHE_DIR, exist_ok=True)

    @commands.command(name="luau")
    async def luau(self, ctx: commands.Context):
        if not ctx.message.attachments:
            await ctx.send("❌ Please attach at least one `.luau` script file.")
            return

        script_attachment = None
        assets = []

        # Find the .luau script (only one allowed)
        for att in ctx.message.attachments:
            if att.filename.lower().endswith(".luau"):
                if script_attachment is not None:
                    await ctx.send("❌ Only **one** `.luau` script is allowed per command.")
                    return
                script_attachment = att
            else:
                if att.size > MAX_ASSET_SIZE:
                    await ctx.send(f"⚠️ File `{att.filename}` is too large (max {MAX_ASSET_SIZE//1024//1024}MB).")
                    return
                assets.append(att)

        if script_attachment is None:
            await ctx.send("❌ No `.luau` script found in attachments.")
            return

        # Read script
        try:
            code_bytes = await script_attachment.read()
            code = code_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            await ctx.send(f"⚠️ Failed to read script: {e}")
            return

        # Process assets
        asset_list = []
        has_image = has_gif = has_bitmap = False

        for asset in assets:
            ext = os.path.splitext(asset.filename)[1].lower()
            filename_hash = hashlib.sha256(asset.filename.encode()).hexdigest()[:16]
            safe_name = f"{filename_hash}{ext}"
            save_path = os.path.join(CACHE_DIR, safe_name)

            try:
                await asset.save(save_path)
            except Exception as e:
                await ctx.send(f"⚠️ Failed to save asset `{asset.filename}`: {e}")
                return

            info = {
                "filename": asset.filename,
                "size": asset.size,
                "content_type": asset.content_type,
                "path": save_path
            }

            fname_lower = asset.filename.lower()
            if fname_lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                info["type"] = "image"
                has_image = True
            elif fname_lower.endswith(".gif"):
                info["type"] = "gif"
                has_gif = True
            elif fname_lower.endswith(".bmp"):
                info["type"] = "bitmap"
                has_bitmap = True
            elif fname_lower.endswith(".obj"):
                info["type"] = "obj"
            elif fname_lower.endswith((".gltf", ".glb")):
                info["type"] = "gltf"
            else:
                info["type"] = "unknown"

            asset_list.append(info)

        att_info = {
            "script": script_attachment.filename,
            "assets": asset_list,
            "has_image": has_image,
            "has_gif": has_gif,
            "has_bitmap": has_bitmap,
        }

        # Execute
        status, result = run_luau_script(code, att_info)

        if status == NO_MESSAGE_OR_INTERACTABLES:
            await ctx.send("❌ Script didn't produce any output (message, image, gif, or model).")
            return

        if status == INVALID_RETURN_TYPE:
            err = result.get("error", "Unknown error")
            await ctx.send(f"⚠️ Script error: {err}")
            return

        # Send results
        try:
            if message := result.get("message"):
                await ctx.send(message)

            if img_path := result.get("image"):
                await ctx.send(file=discord.File(img_path))

            if gif_path := result.get("gif"):
                await ctx.send(file=discord.File(gif_path))

            if model_path := result.get("model3d"):
                await ctx.send(file=discord.File(model_path), content="📦 3D Model:")

        except Exception as e:
            await ctx.send(f"⚠️ Failed to send output: {e}")

# ===============================
# SETUP
# ===============================

async def setup(bot: commands.Bot):
    await bot.add_cog(LuauVMCog(bot))