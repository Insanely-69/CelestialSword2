import discord
from discord.ext import commands, tasks
import os
import webserver
import logging
from datetime import datetime, timezone
from bot.donation_tracker import DonationTracker
from bot.commands import setup_commands
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
donation_tracker = DonationTracker()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    # Start the daily cleanup task
    daily_cleanup.start()
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Check if message is from AniGame bot in the configured channel
    if (message.author.id == Config.ANIGAME_BOT_ID and 
        message.channel.id == Config.DONATION_CHANNEL_ID):
        
        # Process donation message
        await donation_tracker.process_donation_message(message)
    
    # Process commands
    await bot.process_commands(message)

@tasks.loop(hours=24)
async def daily_cleanup():
    now = datetime.now(timezone.utc)
    logger.info("Performing daily cleanup...")
    
    # Clean up expired weekly data
    donation_tracker.cleanup_expired_weeks()
    
    # Optional: Post weekly summary on Sundays
    if now.weekday() == 6:  # Sunday
        logger.info("Posting weekly summary...")
        channel = bot.get_channel(Config.DONATION_CHANNEL_ID)
        if channel:
            report = await donation_tracker.generate_weekly_report()
            if report and "No donations recorded" not in report:
                embed = discord.Embed(
                    title="📊 Weekly Donation Summary",
                    description=report,
                    color=0x00ff00,
                    timestamp=now
                )
                await channel.send(embed=embed)

@daily_cleanup.before_loop
async def before_daily_cleanup():
    await bot.wait_until_ready()

# Setup commands
setup_commands(bot, donation_tracker)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred while processing the command.")

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    webserver.keep_alive()
    bot.run(DISCORD_BOT_TOKEN)
