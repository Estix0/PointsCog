from redbot.core import commands, Config
import discord
import asyncio
import random
from collections import defaultdict
import datetime

class Points(commands.Cog):
    """A points-based rewards system for user activity."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=2137020405)
        self.config.register_member(points=0,
                                    rewards={}
        )
        self.config.register_guild(reward_channel=None, tiers={})
        self.message_cooldown = {}  # Tracks message cooldowns
        self.active_voice_users = {}  # Tracks active voice users
        self.default_guild_id =   # Replace with a specific default server ID

    def guild_find(self, ctx):
        """Returns the guild ID or a default ID for DM messages."""
        return ctx.guild if ctx.guild else self.bot.get_guild(self.default_guild_id)    

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        author_id = message.author.id
        if author_id in self.message_cooldown:
            return  # Enforce cooldown
        
        current_points = await self.config.member(message.author).points()
        await self.config.member(message.author).points.set(current_points + 3)
        self.message_cooldown[author_id] = True
        await asyncio.sleep(60)  # 1-minute cooldown
        self.message_cooldown.pop(author_id, None)


    active_voice_users = defaultdict(bool)  # Tracks users currently earning points

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        
        # User leaves VC or gets deafened → Stop tracking
        if after.channel is None or after.self_deaf:
            self.active_voice_users.pop(member.id, None)
            return
        
        # User joins VC or undeafens → Start tracking if not already
        if member.id not in self.active_voice_users:
            self.active_voice_users[member.id] = True
            await self.grant_voice_points(member)

    async def grant_voice_points(self, member):
        """Grants points every minute while the user remains valid."""
        while member.id in self.active_voice_users:
            # Stop if user leaves VC or gets deafened
            if not member.voice or member.voice.self_deaf:
                self.active_voice_users.pop(member.id, None)
                break
            
            current_points = await self.config.member(member).points()
            await self.config.member(member).points.set(current_points + 1)
            await asyncio.sleep(60)  # Wait a minute before next award


    @commands.group(name="points", aliases=["p"])
    async def points(self, ctx):
        """Base command for the rewards system."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use !points [commands].")

    @points.command(name="FAQ", aliases=["faq"])
    async def faqinfo(self, ctx):
        """Posts the link to FAQ google doc."""
        embed = discord.Embed(title="", color=discord.Color.pink())
        await ctx.send(embed=embed)


    @points.command(name="commands")
    async def commands_list(self, ctx):
        """List all available user commands."""
        command_descriptions = {
            "faq": "Use **!p FAQ**, to get a link to the Google Doc with the FAQ.",
            "balance": "Check your current amount of points.",
            "rewards": "Display available rewards.",
            "redeem": "Claim a reward using the command **!p redeem [REWARD NAME]**.",
            "gamba": "Test your luck every 7 days for a chance to win (-2500;2500) points.",
        }
        command_list = "\n".join([f"**!points {cmd}** - {desc}" for cmd, desc in command_descriptions.items()])
        embed = discord.Embed(title="Available commands", description=command_list, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @points.command(name="balance")
    async def balance(self, ctx):
        """Check your current points balance."""
        guild = self.guild_find(ctx)      
        member = guild.get_member(ctx.author.id)
        points = await self.config.member(member).points()
        embed = discord.Embed(title="Your current balance", description=f"You have **{points}** points!", color=discord.Color.blue())
        await ctx.send(embed=embed)

    @points.command(name="rewards")
    async def rewards(self, ctx):
        """List available rewards."""
        guild = self.guild_find(ctx)
        tiers = await self.config.guild(guild).tiers()
        reward_list = "\n".join([f"{k}: {v} points" for k, v in tiers.items()]) or "No rewards set."
        embed = discord.Embed(title="Available rewards", description=reward_list, color=discord.Color.green())
        await ctx.send(embed=embed)

    @points.command(name="redeem")
    async def redeem(self, ctx, reward: str):
        """Redeem a reward."""
        guild = self.guild_find(ctx)
        member = guild.get_member(ctx.author.id)
        tiers = await self.config.guild(guild).tiers()
        points = await self.config.member(member).points() or 0
        
        if reward not in tiers:
            await ctx.send("Invalid reward.")
            return
        
        cost = tiers[reward]
        if points < cost:
            await ctx.send("Insufficient points.")
            return
        
        await self.config.member(member).points.set(points - cost)
        
        reward_channel_id = await self.config.guild(guild).reward_channel()
        if reward_channel_id:
            channel = self.bot.get_channel(reward_channel_id)
            if channel:
                await channel.send(f"{ctx.author.mention} redeemed {reward}!")
    
        embed = discord.Embed(title="You redeemed a reward", description=f"**{reward}** was redeemed!", color=discord.Color.gold())
        await ctx.send(embed=embed)


    @commands.admin_or_permissions(manage_guild=True)
    @points.command(name="setreward")
    async def setreward(self, ctx, reward: str, cost: int):
        """Set a reward with a required point cost."""
        guild = self.guild_find(ctx)
        async with self.config.guild(guild).tiers() as tiers:
            tiers[reward] = cost
        embed = discord.Embed(title="Reward set", description=f"{reward} costs **{cost}** points.", color=discord.Color.purple())
        await ctx.send(embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @points.command(name="removereward")
    async def removereward(self, ctx, reward: str):
        """Remove a reward."""
        guild = self.guild_find(ctx)
        async with self.config.guild(guild).tiers() as tiers:
            if reward in tiers:
                del tiers[reward]
                embed = discord.Embed(title="Reward deleted", description=f"Reward **{reward}** was deleted.", color=discord.Color.red())
                await ctx.send(embed=embed)
            else:
                await ctx.send("Invalid reward name.")

    @commands.admin_or_permissions(manage_guild=True)
    @points.command(name="setrewardchannel")
    async def setrewardchannel(self, ctx, channel: discord.TextChannel):
        """Set the channel for reward redemption notifications."""
        guild = self.guild_find(ctx)
        await self.config.guild(guild).reward_channel.set(channel.id)
        embed = discord.Embed(title="Notification channel has been set", description=f"New reward redeem notifications will be sent to {channel.mention}", color=discord.Color.teal())
        await ctx.send(embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @points.command(name="givepoints")
    async def givepoints(self, ctx, member: discord.Member, points: int):
        """Give points to a user."""
        current = await self.config.member(member).points()
        await self.config.member(member).points.set(current + points)
        embed = discord.Embed(title="Awarded points", description=f"{member.mention} receives **{points}** points!", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @points.command(name="removepoints")
    async def removepoints(self, ctx, member: discord.Member, points: int):
        """Remove points from a user."""
        current = await self.config.member(member).points()
        new_points = max(0, current - points)
        await self.config.member(member).points.set(new_points)
        embed = discord.Embed(title="Removed points", description=f"{member.mention} lost **{points}** points.", color=discord.Color.red())
        await ctx.send(embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @points.command(name="userbalance")
    async def userbalance(self, ctx, member: discord.Member):
        """Check current user points balance."""
        points = await self.config.member(member).points()
        embed = discord.Embed(title=f"Current balance of {member.name}", description=f"{member.mention} has **{points}** points", color=discord.Color.blue())
        await ctx.send(embed=embed)

    @points.command(name="LuckyRoll")
    @commands.cooldown(1,604800,commands.BucketType.user)
    async def gamba(self, ctx):
        """Test your luck."""
        guild = self.guild_find(ctx)      
        member = guild.get_member(ctx.author.id)
        current = await self.config.member(member).points()
        gamba = random.randint(-2500,2500)
        new_points = current + gamba
        await self.config.member(member).points.set(new_points)
        embed = discord.Embed(title="Lucky Roll", description=f"{ctx.author.mention} {'won' if gamba >= 0 else 'lost'} **{abs(gamba)}** points.", color=discord.Color.gold())
        await ctx.send(embed=embed)

    @points.command(name="leaderboard")
    async def leaderboard(self, ctx):
        """Show the general leaderboard."""
        members = ctx.guild.members
        points_data = [(m, await self.config.member(m).points()) for m in members if not m.bot]
        
        sorted_members = sorted(points_data, key=lambda x: x[1], reverse=True)[:10]
        
        leaderboard_text = "\n".join([f"**{i+1}. {m[0].display_name}**   {m[1]} points" for i, m in enumerate(sorted_members)]) or "No data."
        embed = discord.Embed(title="Leaderboard", description=leaderboard_text, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @points.command(name="weekly")
    async def weekly_leaderboard(self, ctx):
        """Show the weekly leaderboard."""
        members = ctx.guild.members
        points_data = [(m, await self.config.member(m).weekly_points() or 0) for m in members if not m.bot]
        
        sorted_members = sorted(points_data, key=lambda x: x[1], reverse=True)[:10]
        
        leaderboard_text = "\n".join([f"**{m[0].display_name}** - {m[1]} points" for m in sorted_members]) or "No data."
        embed = discord.Embed(title="Weekly Leaderboard", description=leaderboard_text, color=discord.Color.blue())
        await ctx.send(embed=embed)


    async def reset_weekly_points(self):
        """Reset weekly points every 7 days."""
        while True:
            await asyncio.sleep(604800)  # 7 days in seconds
            guilds = self.bot.guilds
            for guild in guilds:
                for member in guild.members:
                    if not member.bot:
                        await self.config.member(member).weekly_points.set(0)

    @commands.Cog.listener()
    async def on_ready(self):
        """Start the weekly reset loop when the bot is ready."""
        self.bot.loop.create_task(self.reset_weekly_points())

