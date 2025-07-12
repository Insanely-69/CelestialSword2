import os

class Config:
    # Discord Bot Configuration
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    
    # AniGame Bot ID (replace with actual AniGame bot ID)
    ANIGAME_BOT_ID = int(os.getenv("ANIGAME_BOT_ID", "571027211407196161"))
    
    # Channel ID where donations are tracked
    DONATION_CHANNEL_ID = int(os.getenv("DONATION_CHANNEL_ID", "0"))
    
    # Guild/Server ID (optional, for slash commands)
    GUILD_ID = int(os.getenv("GUILD_ID", "0")) if os.getenv("GUILD_ID") else None
    
    # Weekly reset day (0 = Monday, 6 = Sunday)
    RESET_DAY = int(os.getenv("RESET_DAY", "6"))  # Sunday by default
    
    # Timezone for weekly resets
    TIMEZONE = os.getenv("TIMEZONE", "UTC")
    
    # Minimum donation amount to track
    MIN_DONATION_AMOUNT = int(os.getenv("MIN_DONATION_AMOUNT", "1"))
    
    # Maximum players to show in leaderboards
    MAX_LEADERBOARD_SIZE = int(os.getenv("MAX_LEADERBOARD_SIZE", "10"))
    
    # Data file paths
    DATA_DIR = "data"
    DONATIONS_FILE = os.path.join(DATA_DIR, "donations.json")
    PLAYERS_FILE = os.path.join(DATA_DIR, "registered_players.json")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
        
        if cls.DONATION_CHANNEL_ID == 0:
            raise ValueError("DONATION_CHANNEL_ID environment variable is required")
        
        return True
