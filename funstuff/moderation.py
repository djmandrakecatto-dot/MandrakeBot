import discord
from discord.ext import commands
import psutil
import asyncio

class SmartModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_muted_role(self, guild):
        """Smarter Mute: Finds or creates a 'Muted' role with global overrides."""
        role = discord.utils.get(guild.roles, name="Muted")
        if not role:
            try:
                role = await guild.create_role(name="Muted", reason="Automatic Muted role creation")
                for channel in guild.channels:
                    await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
            except discord.Forbidden:
                return None
        return role

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Warns a member and logs it in the channel."""
        # Smarter check: Don't warn yourself or higher staff
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("❌ You cannot warn someone with a higher or equal role.")
        
        embed = discord.Embed(title="⚠️ Member Warned", color=discord.Color.orange())
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)
        try:
            await member.send(f"⚠️ You have been warned in **{ctx.guild.name}** for: {reason}")
        except:
            pass # Member has DMs closed

    @commands.command(name="mute")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Improved Mute: Applies a server-wide 'Muted' role."""
        if psutil.virtual_memory().percent > 90.0:
            return await ctx.send("🚨 RAM too high. Mute aborted to save resources.")

        if member.top_role >= ctx.author.top_role:
            return await ctx.send("❌ Your role is not high enough to mute this person.")

        muted_role = await self.get_muted_role(ctx.guild)
        if not muted_role:
            return await ctx.send("❌ I couldn't find or create a 'Muted' role. Check my permissions.")

        if muted_role in member.roles:
            return await ctx.send(f"ℹ️ {member.display_name} is already muted.")

        await member.add_roles(muted_role, reason=reason)
        await ctx.send(f"🔇 **{member.display_name}** has been muted. | Reason: {reason}")

    @commands.command(name="unmute")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Removes the server-wide 'Muted' role."""
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role)
            await ctx.send(f"🔊 **{member.display_name}** has been unmuted.")
        else:
            await ctx.send("❌ That user is not muted.")

    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        """Smarter Clear: Warns if clearing a huge amount."""
        if amount > 100:
            return await ctx.send("⚠️ To protect the HP-Note, I can only clear 100 messages at a time.")
        
        if psutil.virtual_memory().percent > 90.0:
            return await ctx.send("🚨 System memory too high for mass deletion.")

        deleted = await ctx.channel.purge(limit=amount + 1)
        # Use an ephemeral-style response
        msg = await ctx.send(f"🧹 Successfully cleared **{len(deleted)-1}** messages.")
        await asyncio.sleep(3)
        await msg.delete()

async def setup(bot):
    await bot.add_cog(SmartModeration(bot))