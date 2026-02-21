import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="banflip")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def banflip(self, ctx, *, user: str):
        guild = ctx.guild
        me = guild.me

        bans = [entry async for entry in guild.bans()]

        if user.isdigit():
            uid = int(user)

            if uid == self.bot.user.id:
                await ctx.send("❌ I won’t ban myself.")
                return

            banned = next((b.user for b in bans if b.user.id == uid), None)

            try:
                if banned:
                    await guild.unban(banned)
                    await ctx.send(f"🔓 Unbanned **{banned}**")
                else:
                    target = await self.bot.fetch_user(uid)
                    await guild.ban(target, reason=f"Banned by {ctx.author}")
                    await ctx.send(f"🔨 Banned **{target}**")
            except discord.Forbidden:
                await ctx.send("❌ Missing permissions or role hierarchy issue.")
            return

        try:
            member = await commands.MemberConverter().convert(ctx, user)

            if member.top_role >= me.top_role:
                await ctx.send("❌ My role is not high enough to ban this user.")
                return

            await guild.ban(member, reason=f"Banned by {ctx.author}")
            await ctx.send(f"🔨 Banned **{member}**")

        except discord.Forbidden:
            await ctx.send("❌ Missing permissions or hierarchy issue.")
        except:
            await ctx.send("❌ User not found.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
