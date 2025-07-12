import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def setup_commands(bot, donation_tracker):
    """Setup bot commands"""
    
    @bot.command(name='register')
    @commands.has_permissions(manage_messages=True)
    async def register_player(ctx, user: discord.Member, *, player_name: str):
        """Register a player for donation tracking (Mod only)"""
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)
        
        if donation_tracker.register_player(guild_id, user_id, player_name):
            embed = discord.Embed(
                title="✅ Player Registered",
                description=f"**{player_name}** has been registered for donation tracking.",
                color=0x00ff00
            )
            embed.add_field(name="Discord User", value=user.mention, inline=True)
            embed.add_field(name="Player Name", value=player_name, inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to register player.")
    
    @bot.command(name='unregister')
    @commands.has_permissions(manage_messages=True)
    async def unregister_player(ctx, user: discord.Member):
        """Unregister a player from donation tracking (Mod only)"""
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)
        
        if donation_tracker.unregister_player(guild_id, user_id):
            embed = discord.Embed(
                title="✅ Player Unregistered",
                description=f"{user.mention} has been removed from donation tracking.",
                color=0xff9900
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Player was not registered.")
    
    @bot.command(name='players')
    @commands.has_permissions(manage_messages=True)
    async def list_players(ctx):
        """List all registered players with donation stats (Mod only)"""
        guild_id = str(ctx.guild.id)
        players = donation_tracker.get_registered_players(guild_id)
        weekly_data = donation_tracker.get_weekly_donations(guild_id)
        total_data = donation_tracker.get_total_donations(guild_id)
        
        if not players:
            await ctx.send("No registered players found.")
            return
        
        embed = discord.Embed(
            title="📋 Registered Players",
            color=0x0099ff
        )
        
        player_list = []
        active_donors = 0
        
        for user_id, player_name in players.items():
            try:
                user = bot.get_user(int(user_id))
                user_mention = user.mention if user else f"Unknown User ({user_id})"
                
                # Check if player has donated
                weekly_amount = weekly_data.get(user_id, {}).get("amount", 0)
                total_amount = total_data.get(user_id, {}).get("amount", 0)
                
                if weekly_amount > 0:
                    active_donors += 1
                    status = f"🟢 Weekly: {weekly_amount:,} | Total: {total_amount:,}"
                elif total_amount > 0:
                    status = f"🟡 Total: {total_amount:,} coins"
                else:
                    status = "⚪ No donations yet"
                
                player_list.append(f"**{player_name}** - {user_mention}\n└ {status}")
            except:
                player_list.append(f"**{player_name}** - Unknown User ({user_id})\n└ ⚪ No donations yet")
        
        # Split into chunks if too many players
        chunk_size = 8
        for i in range(0, len(player_list), chunk_size):
            chunk = player_list[i:i + chunk_size]
            embed.add_field(
                name=f"Players {i+1}-{min(i+chunk_size, len(player_list))}",
                value="\n".join(chunk),
                inline=False
            )
        
        # Add summary
        embed.add_field(
            name="📊 Summary",
            value=f"**Total Registered**: {len(players)} players\n**Active This Week**: {active_donors} players\n**Donation Rate**: {(active_donors/len(players)*100):.1f}%" if players else "0%",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @bot.command(name='weekly')
    async def weekly_donations(ctx):
        """Show weekly donation leaderboard with totals"""
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        # Check if user is registered (non-mod users must be registered)
        if not ctx.author.guild_permissions.manage_messages:
            if not donation_tracker.is_player_registered(guild_id, user_id):
                await ctx.send("❌ You must be registered to use this command. Ask a moderator to register you with `!register @you YourPlayerName`")
                return
        
        weekly_data = donation_tracker.get_weekly_donations(guild_id)
        total_data = donation_tracker.get_total_donations(guild_id)
        
        if not weekly_data and not total_data:
            embed = discord.Embed(
                title="📊 Donation Statistics",
                description="No donations recorded yet.",
                color=0x999999
            )
            await ctx.send(embed=embed)
            return
        
        current_time = datetime.now(timezone.utc)
        embed = discord.Embed(
            title="📊 Donation Leaderboard",
            description="Individual 7-day tracking + All-time totals",
            color=0x00ff00
        )
        
        # Weekly leaderboard
        if weekly_data:
            sorted_weekly = sorted(weekly_data.items(), key=lambda x: x[1]["amount"], reverse=True)
            weekly_leaderboard = []
            
            for i, (user_id, data) in enumerate(sorted_weekly[:10], 1):
                name = data["name"]
                amount = data["amount"]
                donation_count = len(data["donations"])
                
                # Calculate days remaining and next donation time
                week_start = datetime.fromisoformat(data["week_start"].replace('Z', '+00:00'))
                days_elapsed = (current_time - week_start).days
                days_remaining = max(0, 7 - days_elapsed)
                hours_remaining = max(0, 24 - (current_time - week_start).seconds // 3600)
                
                if i <= 3:
                    emoji = ["🥇", "🥈", "🥉"][i-1]
                else:
                    emoji = f"{i}."
                
                # Get total for this player
                total_amount = total_data.get(user_id, {}).get("amount", 0)
                
                weekly_leaderboard.append(
                    f"{emoji} **{name}**: {amount:,} weekly | {total_amount:,} total ({days_remaining}d {hours_remaining}h left)"
                )
            
            embed.add_field(
                name="🗓️ Weekly Donations (Individual 7-day periods)",
                value="\n".join(weekly_leaderboard),
                inline=False
            )
        
        # Summary stats
        weekly_total = sum(data['amount'] for data in weekly_data.values()) if weekly_data else 0
        all_time_total = sum(data['amount'] for data in total_data.values()) if total_data else 0
        
        embed.add_field(name="📈 Weekly Total", value=f"{weekly_total:,} coins", inline=True)
        embed.add_field(name="🏆 All-Time Total", value=f"{all_time_total:,} coins", inline=True)
        embed.add_field(name="⏰ Next Reset", value="When your 7 days expire", inline=True)
        
        # Show weekly target and progress if set
        weekly_target = donation_tracker.get_weekly_target(guild_id)
        if weekly_target > 0:
            progress = f"{weekly_total:,} / {weekly_target:,} coins ({(weekly_total/weekly_target*100):.1f}%)"
            embed.add_field(name="🎯 Weekly Target", value=progress, inline=True)
        else:
            embed.add_field(name="🎯 Weekly Target", value="Not set", inline=True)
        
        await ctx.send(embed=embed)
    

    
    @bot.command(name='player')
    async def player_stats(ctx, *, player_name: str = None):
        """Show individual player donation stats"""
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        # Check if user is registered (non-mod users must be registered)
        if not ctx.author.guild_permissions.manage_messages:
            if not donation_tracker.is_player_registered(guild_id, user_id):
                await ctx.send("❌ You must be registered to use this command. Ask a moderator to register you with `!register @you YourPlayerName`")
                return
        
        if not player_name:
            # Show stats for the command user if they're registered
            players = donation_tracker.get_registered_players(guild_id)
            if user_id in players:
                player_name = players[user_id]
            else:
                await ctx.send("❌ Please specify a player name or register yourself first.")
                return
        
        # Find player by name
        players = donation_tracker.get_registered_players(guild_id)
        target_user_id = None
        
        for uid, name in players.items():
            if name.lower() == player_name.lower():
                target_user_id = uid
                player_name = name  # Use exact case
                break
        
        if not target_user_id:
            await ctx.send(f"❌ Player '{player_name}' not found in registered players.")
            return
        
        # Get donation data
        weekly_data = donation_tracker.get_weekly_donations(guild_id)
        total_data = donation_tracker.get_total_donations(guild_id)
        
        embed = discord.Embed(
            title=f"📊 {player_name}'s Donation Stats",
            color=0x00ffff
        )
        
        # Weekly stats
        weekly_amount = 0
        weekly_count = 0
        if target_user_id in weekly_data:
            weekly_amount = weekly_data[target_user_id]["amount"]
            weekly_count = len(weekly_data[target_user_id]["donations"])
        
        # Total stats
        total_amount = 0
        total_count = 0
        if target_user_id in total_data:
            total_amount = total_data[target_user_id]["amount"]
            total_count = len(total_data[target_user_id]["donations"])
        
        embed.add_field(name="This Week", value=f"{weekly_amount:,} coins ({weekly_count} donations)", inline=True)
        embed.add_field(name="All Time", value=f"{total_amount:,} coins ({total_count} donations)", inline=True)
        
        # Calculate average if there are donations
        if total_count > 0:
            avg_donation = total_amount // total_count
            embed.add_field(name="Average Donation", value=f"{avg_donation:,} coins", inline=True)
        
        await ctx.send(embed=embed)
    
    @bot.command(name='testdonate')
    @commands.has_permissions(manage_messages=True)
    async def test_donate(ctx, user: discord.Member, amount: int):
        """Manually add a test donation (Mod only)"""
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)
        
        if donation_tracker.is_player_registered(guild_id, user_id):
            players = donation_tracker.get_registered_players(guild_id)
            player_name = players[user_id]
            donation_tracker.add_donation(guild_id, user_id, player_name, amount)
            
            embed = discord.Embed(
                title="✅ Test Donation Added",
                description=f"Added {amount:,} coins for **{player_name}**",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ User is not registered. Register them first with `!register @user PlayerName`")
    
    @bot.command(name='setprefix')
    @commands.has_permissions(manage_messages=True)
    async def set_prefix(ctx, new_prefix: str):
        """Change bot command prefix (Mod only)"""
        if len(new_prefix) > 5:
            await ctx.send("❌ Prefix must be 5 characters or less.")
            return
        
        bot.command_prefix = new_prefix
        
        embed = discord.Embed(
            title="✅ Prefix Changed",
            description=f"Bot prefix changed to `{new_prefix}`",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @bot.command(name='setchannel')
    @commands.has_permissions(manage_messages=True)
    async def set_channel(ctx, channel: discord.TextChannel = None):
        """Set donation tracking channel (Mod only)"""
        if channel is None:
            channel = ctx.channel
        
        # Update the config (in a real implementation, you'd save this to a file)
        from config import Config
        Config.DONATION_CHANNEL_ID = channel.id
        
        embed = discord.Embed(
            title="✅ Channel Set",
            description=f"Donation tracking set to {channel.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @bot.command(name='settarget')
    @commands.has_permissions(manage_messages=True)
    async def set_weekly_target(ctx, amount: int):
        """Set the weekly donation target (Mod only)"""
        guild_id = str(ctx.guild.id)
        if amount < 0:
            await ctx.send("❌ Target must be a positive number.")
            return
        donation_tracker.set_weekly_target(guild_id, amount)
        await ctx.send(f"✅ Weekly donation target set to {amount:,} coins.")
    
    @bot.command(name='commands')
    async def commands_help(ctx):
        """Show bot commands and usage"""
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        # Check if user is registered (non-mod users must be registered)
        if not ctx.author.guild_permissions.manage_messages:
            if not donation_tracker.is_player_registered(guild_id, user_id):
                await ctx.send("❌ You must be registered to use this command. Ask a moderator to register you with `!register @you YourPlayerName`")
                return
        
        embed = discord.Embed(
            title="🤖 AniGame Donation Tracker Commands",
            description="Track clan donations from AniGame bot",
            color=0x0099ff
        )
        
        # Mod commands
        mod_commands = [
            "`!register @user PlayerName` - Register a player for tracking",
            "`!unregister @user` - Remove a player from tracking", 
            "`!players` - List all registered players with stats",
            "`!setprefix <prefix>` - Change bot command prefix",
            "`!setchannel #channel` - Set donation tracking channel",
            "`!testdonate @user <amount>` - Manually add test donation",
            "`!settarget <amount>` - Set the weekly donation target"
        ]
        embed.add_field(
            name="📋 Moderator Commands (Requires Manage Messages)",
            value="\n".join(mod_commands),
            inline=False
        )
        
        # Public commands
        public_commands = [
            "`!weekly` - Show weekly + total donation leaderboard",
            "`!player PlayerName` - Show specific player's stats",
            "`!commands` - Show this help message"
        ]
        embed.add_field(
            name="📊 Public Commands",
            value="\n".join(public_commands),
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ How it Works",
            value="The bot automatically tracks donations when registered players donate through AniGame. Weekly reports are posted every Sunday.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # Error handling for commands
    @register_player.error
    async def register_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ This command requires **Manage Messages** permission.")
        elif isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'user':
                await ctx.send("❌ Please mention a user to register.\n**Usage:** `!register @username PlayerName`")
            elif error.param.name == 'player_name':
                await ctx.send("❌ Please provide a player name.\n**Usage:** `!register @username PlayerName`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid user mentioned.\n**Usage:** `!register @username PlayerName`")
        else:
            logger.error(f"Command error in register: {error}")
            await ctx.send("❌ Command error. **Usage:** `!register @username PlayerName`")
    
    @unregister_player.error
    async def unregister_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ This command requires **Manage Messages** permission.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Please mention a user to unregister.\n**Usage:** `!unregister @username`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid user mentioned.\n**Usage:** `!unregister @username`")
        else:
            logger.error(f"Command error in unregister: {error}")
            await ctx.send("❌ Command error. **Usage:** `!unregister @username`")
    
    @list_players.error
    async def list_players_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ This command requires **Manage Messages** permission.")
        else:
            logger.error(f"Command error in players: {error}")
            await ctx.send("❌ An error occurred while listing players.")
