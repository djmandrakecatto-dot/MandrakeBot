import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class SpaceRank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Fixed: Ensuring variable names are consistent
        self.data_file = "user_ranks.json"
        self.owner_id = 1461996896825380904 
        self.rank_data = {
            "ENLISTED": [
                "Specialist 1", "Specialist 2", "Specialist 3", "Specialist 4",
                "Sergeant", "Technical Sergeant", "Master Sergeant", 
                "Senior Master Sergeant", "Chief Master Sergeant",
                "Chief Master Sergeant of the Space Force"
            ],
            "OFFICER": [
                "Second Lieutenant", "First Lieutenant", "Captain", "Major",
                "Lieutenant Colonel", "Colonel", "Brigadier General",
                "Major General", "Lieutenant General", "General"
            ]
        }

    def load_data(self):
        """Creates the file if it doesn't exist and handles empty files."""
        if not os.path.exists(self.data_file):
            return {}
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_data(self, data):
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=4)

    @commands.hybrid_command(name="addrank")
    async def addrank(self, ctx, member: discord.Member, *, rank_name: str):
        """Owner only: Adds a person to the service list with a rank"""
        if ctx.author.id != self.owner_id:
            return await ctx.send("❌ Permission denied: Command reserved for Space Force Commander.")

        # Normalize the rank input (Capitalize Each Word)
        rank_name = rank_name.title()
        all_valid_ranks = self.rank_data["ENLISTED"] + self.rank_data["OFFICER"]
        
        if rank_name not in all_valid_ranks:
            # List valid ranks to help the user
            return await ctx.send(f"❌ Invalid Rank. Use titles like 'Specialist 1' or 'Sergeant'.")

        data = self.load_data()
        data[str(member.id)] = {
            "rank": rank_name,
            "name": member.display_name
        }
        self.save_data(data)

        await ctx.send(f"🎖️ **{member.display_name}** has been commissioned as a **{rank_name}**!")

    @commands.hybrid_command(name="unrank")
    async def unrank(self, ctx, member: discord.Member):
        """Owner only: Removes (unlists) a person from the rank list"""
        if ctx.author.id != self.owner_id:
            return await ctx.send("❌ Permission denied.")

        data = self.load_data()
        user_id_str = str(member.id)
        
        if user_id_str in data:
            old_rank = data[user_id_str]["rank"]
            del data[user_id_str]
            self.save_data(data)
            await ctx.send(f"🚫 **{member.display_name}** has been stripped of their **{old_rank}** status and unlisted.")
        else:
            await ctx.send("❌ This user is not currently in the service list.")

async def setup(bot):
    # Fixed: Match the class name defined above
    await bot.add_cog(SpaceRank(bot))