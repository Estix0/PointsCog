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
        self.config.register_member(points=0, weeklypoints=0, rewards={})
        self.config.register_guild(reward_channel=None, weekly_channel=None, tiers={})
        self.message_cooldown = {}  # Tracks message cooldowns
        self.active_voice_users = {}  # Tracks active voice users
        self.voice_loop_task = self.bot.loop.create_task(self.voice_points_loop())
        self.default_guild_id =   # Replace with your server ID

    def guild_find(self, ctx):
        return ctx.guild if ctx.guild else self.bot.get_guild(self.default_guild_id)
    
    async def _post_weekly_leaderboards_and_reset(self):
        for guild in self.bot.guilds:
            members = [m for m in guild.members if not m.bot]
            points_data = [(m, await self.config.member(m).weeklypoints()) for m in members]
            sorted_members = sorted(points_data, key=lambda x: x[1], reverse=True)[:10]

            leaderboard_text = "\n".join(
                [f"**{i+1}. {m[0].display_name}** {m[1]} points" for i, m in enumerate(sorted_members)]
            ) or "No Data."

            weekly_channel_id = await self.config.guild(guild).weekly_channel()
            if weekly_channel_id:
                channel = self.bot.get_channel(weekly_channel_id)
                if channel:
                    embed = discord.Embed(
                        title="Weekly Activity Leaderboard",
                        description=leaderboard_text,
                        color=discord.Color.blue()
                    )
                    await channel.send(embed=embed)

            for member in members:
                await self.config.member(member).weeklypoints.set(0)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        author_id = message.author.id
        if author_id in self.message_cooldown:
            return
        current_points = await self.config.member(message.author).points()
        weekly_points = await self.config.member(message.author).weeklypoints()
        await self.config.member(message.author).points.set(current_points + 3)
        await self.config.member(message.author).weeklypoints.set(weekly_points + 3)
        self.message_cooldown[author_id] = True
        await asyncio.sleep(60)
        self.message_cooldown.pop(author_id, None)

    active_voice_users = defaultdict(bool)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        if after.channel is None or after.self_deaf:
            self.active_voice_users.pop(member.id, None)
        else:
            self.active_voice_users[member.id] = member  # Store the full member object

    async def voice_points_loop(self):
        await self.bot.wait_until_ready()
        while True:
            to_remove = []
            for member_id, member in self.active_voice_users.items():
                if not member.voice or member.voice.self_deaf:
                    to_remove.append(member_id)
                    continue
                # Grant points
                points = await self.config.member(member).points()
                weekly = await self.config.member(member).weeklypoints()
                await self.config.member(member).points.set(points + 1)
                await self.config.member(member).weeklypoints.set(weekly + 1)

            # Clean up inactive users
            for member_id in to_remove:
                self.active_voice_users.pop(member_id, None)

            await asyncio.sleep(60)
    @commands.group(name="points", aliases=["p"])
    async def points(self, ctx):
        """Base command for the rewards system."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use !points [commands].")

    @commands.admin_or_permissions(manage_guild=True)
    @points.command(name="ResetWeekly", aliases=["resetweekly"])
    async def testweeklyreset(self,ctx):
        """Reset weekly points."""
        await self._post_weekly_leaderboards_and_reset()

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

        members = [m for m in guild.members if not m.bot]
        points_data = [(m, await self.config.member(m).points()) for m in members if not m.bot]
        points_data = [entry for entry in points_data if entry[1] != 0]
        points_data.sort(key=lambda x: x[1], reverse=True)
        rank = next((i + 1 for i, (m, _) in enumerate(points_data) if m.id == member.id), None)

        total_ranked = len(points_data)

        rank = next((i + 1 for i, (m, _) in enumerate(points_data) if m.id == member.id), None)

        desc = f"You have **{points}** points!"
        if rank:
            desc += f"\nYour current rank is **{rank}** / **{total_ranked}**."

        embed = discord.Embed(title="Your current balance", description=desc, color=discord.Color.blue())
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
    async def gamba(self, ctx):
        """Gamble your points away."""
        guild = self.guild_find(ctx)      
        member = guild.get_member(ctx.author.id)
        current = await self.config.member(member).points()

        now = int(datetime.datetime.utcnow().timestamp())
        last_roll = await self.config.member(member).get_raw("last_roll", default=0)

        cooldown = 604800  # 7 days in seconds
        remaining = cooldown - (now - last_roll)

        if remaining > 0:
            hours, minutes = divmod(remaining // 60, 60)
            time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
            await ctx.send(f"You can use `LuckyRoll` in {time_str}.")
            return

        gamba = random.randint(-2500,2500)
        new_points = current + gamba
        await self.config.member(member).points.set(new_points)
        await self.config.member(member).set_raw("last_roll", value=now)

        embed = discord.Embed(title="LuckyRoll", description=f"{ctx.author.mention} {'wins' if gamba >= 0 else 'looses'} **{abs(gamba)}** points.", color=discord.Color.gold())
        await ctx.send(embed=embed)

    @points.command(name="leaderboard")
    async def leaderboard(self, ctx):
        """Show the general leaderboard."""
        members = ctx.guild.members
        points_data = [(m, await self.config.member(m).points()) for m in members if not m.bot]        
        points_data = [entry for entry in points_data if entry[1] != 0]

        sorted_members = sorted(points_data, key=lambda x: x[1], reverse=True)[:10]
        
        leaderboard_text = "\n".join([f"**{i+1}. {m[0].display_name}**   {m[1]} points" for i, m in enumerate(sorted_members)]) or "No data."
        embed = discord.Embed(title="Leaderboard", description=leaderboard_text, color=discord.Color.blue())
        await ctx.send(embed=embed)


    @points.command(name="bottomboard")
    async def bottomboard(self, ctx):
        """Show the general leaderboard."""
        members = ctx.guild.members
        points_data = [(m, await self.config.member(m).points()) for m in members if not m.bot]
        points_data = [entry for entry in points_data if entry[1] < 0]

        sorted_members = sorted(points_data, key=lambda x: x[1])[:10]
        
        leaderboard_text = "\n".join([f"**{i+1}. {m[0].display_name}**   {m[1]} points" for i, m in enumerate(sorted_members)]) or "No data."
        embed = discord.Embed(title="Bottomboard", description=leaderboard_text, color=discord.Color.red())
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

