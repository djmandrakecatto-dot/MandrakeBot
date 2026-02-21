import discord
from discord.ext import commands

class AuditLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="log")
    @commands.has_permissions(view_audit_log=True)
    async def log(self, ctx, count: int = 5):
        """Usage: !log 10 (Shows the last 10 actions)"""
        
        # Cap the count to prevent spam/lag
        if count > 50:
            count = 50
            await ctx.send("⚠️ Capping request to 50 logs for stability.")

        try:
            embed = discord.Embed(
                title=f"📜 Recent Audit Logs for {ctx.guild.name}",
                color=discord.Color.blue()
            )

            # We iterate through the audit logs
            async for entry in ctx.guild.audit_logs(limit=count):
                # Format: User performed Action on Target
                user = entry.user
                action = str(entry.action).replace("AuditLogAction.", "").replace("_", " ").title()
                target = entry.target

                # Handle different target types (Member, Channel, Role, etc.)
                target_name = "Unknown"
                if hasattr(target, "name"):
                    target_name = target.name
                elif isinstance(target, discord.User) or isinstance(target, discord.Member):
                    target_name = f"{target.name}#{target.discriminator}"
                
                log_value = f"**User:** {user.mention}\n**Target:** {target_name}"
                
                # Add time in a readable format
                time_str = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
                
                embed.add_field(
                    name=f"🛠️ {action} ({time_str})",
                    value=log_value,
                    inline=False
                )

            if not embed.fields:
                return await ctx.send("🤷 No logs found.")

            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to `View Audit Log`!")
        except Exception as e:
            await ctx.send(f"⚠️ Error fetching logs: {e}")

async def setup(bot):
    await bot.add_cog(AuditLogs(bot))