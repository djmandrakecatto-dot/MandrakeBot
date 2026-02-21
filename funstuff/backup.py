import discord
from discord.ext import commands, tasks
import os
import zipfile
import datetime
import platform
import ctypes
import shutil

class BackupManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_dir = "user_backups"
        self.data_dir = "user_data"
        self.limit_2gb = 2 * 1024 * 1024 * 1024 # Unpacked limit
        self.max_upload = 10 * 1024 * 1024      # Discord 10MB limit
        
        # Ensure folders exist
        for d in [self.backup_dir, self.data_dir]:
            if not os.path.exists(d): 
                os.makedirs(d)
        
        self.auto_cleanup.start()

    def cog_unload(self):
        self.auto_cleanup.cancel()

    def get_free_space(self):
        """Hardware check for HP-Note storage"""
        if platform.system() == 'Windows':
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p("C:\\"), None, None, ctypes.pointer(free_bytes))
            return free_bytes.value
        return os.statvfs('/').f_bavail * os.statvfs('/').f_frsize

    def get_folder_size(self, path):
        """Calculates total size of a directory"""
        total = 0
        if not os.path.exists(path): return 0
        for root, _, files in os.walk(path):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
        return total

    def clean_temp(self):
        """Wipes %temp% files to free up space"""
        temp = os.environ.get('TEMP')
        if temp and os.path.exists(temp):
            for f in os.listdir(temp):
                try:
                    path = os.path.join(temp, f)
                    if os.path.isfile(path): os.unlink(path)
                    elif os.path.isdir(path): shutil.rmtree(path)
                except: continue

    @tasks.loop(minutes=10)
    async def auto_cleanup(self):
        """Deletes zips not looked at for 1 hour"""
        now = datetime.datetime.now()
        for f in os.listdir(self.backup_dir):
            path = os.path.join(self.backup_dir, f)
            if (now - datetime.datetime.fromtimestamp(os.path.getatime(path))).seconds > 3600:
                os.remove(path)

    @commands.hybrid_command(name="backup_make")
    async def backup_make(self, ctx):
        """Limit: 1 per month. Checks for 2GB limit and creates a private chat."""
        user_path = os.path.join(self.data_dir, str(ctx.author.id))
        zip_name = f"backup_{ctx.author.id}.zip"
        zip_path = os.path.join(self.backup_dir, zip_name)

        # 1. Check Monthly Limit
        if os.path.exists(zip_path):
            last_mod = datetime.datetime.fromtimestamp(os.path.getmtime(zip_path))
            if (datetime.datetime.now() - last_mod).days < 30:
                return await ctx.send("❌ **Limit Reached:** 1 backup per month.")

        # 2. Check 2GB Limit & Disk Space
        unpacked_size = self.get_folder_size(user_path)
        if unpacked_size > self.limit_2gb or self.get_free_space() < self.limit_2gb:
            return await ctx.send("⚠️ **Error:** 2GBs Limited! Cannot process backup.")

        # 3. Create Private Thread Chat
        thread = await ctx.channel.create_thread(name=f"Backup-{ctx.author.name}", type=discord.ChannelType.private_thread)
        await ctx.send(f"📂 Backup started in {thread.mention}")

        # 4. Zip Process
        await thread.send("🗜️ **Compressing...**")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(user_path):
                for f in files:
                    zipf.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), user_path))
        
        await thread.send("✅ Done! Use `/backup_save` here to download.")

    @commands.hybrid_command(name="backup_upload")
    async def backup_upload(self, ctx, attachment: discord.Attachment):
        """Uploads file to your data folder. Blocks if space < 2GB."""
        self.clean_temp() # Auto-clean temp to free space
        user_path = os.path.join(self.data_dir, str(ctx.author.id))
        if not os.path.exists(user_path): os.makedirs(user_path)

        if attachment.size > self.max_upload:
            return await ctx.send("❌ Discord limit is 10MB!")

        if self.get_folder_size(user_path) + attachment.size > self.limit_2gb:
            return await ctx.send("⚠️ **Error:** 2GBs Limited!")

        if self.get_free_space() < self.limit_2gb:
            return await ctx.send("❌ PC Storage too low (< 2GB)!")

        await attachment.save(os.path.join(user_path, attachment.filename))
        await ctx.send(f"📥 Saved `{attachment.filename}`")

    @commands.hybrid_command(name="tree_data")
    async def tree_data(self, ctx):
        """Visual tree of YOUR files only."""
        user_path = os.path.join(self.data_dir, str(ctx.author.id))
        if not os.path.exists(user_path): return await ctx.send("Empty.")

        # Reset 1-hour timer for zip if user looks at files
        zip_path = os.path.join(self.backup_dir, f"backup_{ctx.author.id}.zip")
        if os.path.exists(zip_path): os.utime(zip_path, None)

        tree = "📁 **Your Storage**\n"
        for r, d, fs in os.walk(user_path):
            indent = " " * 4 * (r.replace(user_path, "").count(os.sep))
            tree += f"{indent}┣ {os.path.basename(r)}/\n"
            for f in fs: tree += f"{indent}┃ ┗ {f}\n"

        await ctx.send(f"```\n{tree[:1900]}\n```")
    @commands.hybrid_command(name="backup_see")
    async def backup_see(self, ctx):
        """Generates a full tree view of everything currently in your storage."""
        user_path = os.path.join(self.data_dir, str(ctx.author.id))
        
        if not os.path.exists(user_path) or not os.listdir(user_path):
            return await ctx.send("📂 Your storage is currently empty.")

        # Update access time on the zip if it exists to keep it alive
        zip_path = os.path.join(self.backup_dir, f"backup_{ctx.author.id}.zip")
        if os.path.exists(zip_path): 
            os.utime(zip_path, None)

        def build_tree(path, prefix=""):
            items = sorted(os.listdir(path))
            tree_str = ""
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                connector = "┗ " if is_last else "┣ "
                full_path = os.path.join(path, item)
                
                tree_str += f"{prefix}{connector}{item}\n"
                
                if os.path.isdir(full_path):
                    extension = "  " if is_last else "┃ "
                    tree_str += build_tree(full_path, prefix + extension)
            return tree_str

        full_tree = build_tree(user_path)
        
        # Split message if it's longer than 2000 characters
        if len(full_tree) > 1950:
            # If the tree is massive, send as a text file
            with open("temp_tree.txt", "w", encoding="utf-8") as f:
                f.write(full_tree)
            await ctx.send("📄 The file list is too long for Discord, here is the full map:", 
                           file=discord.File("temp_tree.txt", "storage_map.txt"))
            os.remove("temp_tree.txt")
        else:
            await ctx.send(f"📂 **Full Storage Map:**\n```\n{full_tree}\n```")

    @commands.hybrid_command(name="backup_download")
    async def backup_download(self, ctx, filename: str):
        """Download a specific file from your data folder."""
        user_path = os.path.join(self.data_dir, str(ctx.author.id))
        file_path = os.path.join(user_path, filename)

        # Security check: Ensure they aren't trying to escape their folder
        if not os.path.abspath(file_path).startswith(os.path.abspath(user_path)):
            return await ctx.send("❌ Access denied.")

        if not os.path.exists(file_path):
            return await ctx.send(f"❌ File `{filename}` not found in your storage.")

        if os.path.isdir(file_path):
            return await ctx.send("❌ That is a folder. Use `/backup_make` to zip and download folders.")

        # Check Discord upload limit (10MB)
        file_size = os.path.getsize(file_path)
        if file_size > self.max_upload:
            return await ctx.send(f"❌ `{filename}` is {file_size/(1024*1024):.1f}MB, which exceeds the 10MB limit.")

        await ctx.send(f"📤 Sending `{filename}`...", file=discord.File(file_path))
    @commands.hybrid_command(name="file_delete")
    async def file_delete(self, ctx, filename: str):
        """Delete specific file to free up space."""
        path = os.path.join(self.data_dir, str(ctx.author.id), filename)
        if os.path.exists(path):
            os.remove(path)
            await ctx.send(f"🗑️ Deleted `{filename}`")
        else:
            await ctx.send("❌ Not found.")

async def setup(bot):
    await bot.add_cog(BackupManager(bot))