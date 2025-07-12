import json
import re
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import os

logger = logging.getLogger(__name__)

class DonationTracker:
    def __init__(self):
        self.donations_file = "data/donations.json"
        self.players_file = "data/registered_players.json"
        self.donations_data = self.load_donations()
        self.registered_players = self.load_registered_players()
    
    def load_donations(self) -> Dict:
        """Load donation data from JSON file"""
        if os.path.exists(self.donations_file):
            try:
                with open(self.donations_file, 'r') as f:
                    data = json.load(f)
                    # Migrate old format to server-based format
                    if "weekly_donations" in data and not any(str(k).isdigit() and len(str(k)) > 10 for k in data.keys()):
                        logger.info("Migrating old donation format to server-based format")
                        # This is old format, wrap it in a default server
                        return {"0": data}
                    return data
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning("Could not load donations data, starting fresh")
        
        return {}
    
    def load_registered_players(self) -> Dict:
        """Load registered players from JSON file"""
        if os.path.exists(self.players_file):
            try:
                with open(self.players_file, 'r') as f:
                    data = json.load(f)
                    # Migrate old format to server-based format
                    if data and not any(str(k).isdigit() and len(str(k)) > 10 for k in data.keys()):
                        logger.info("Migrating old players format to server-based format")
                        # This is old format, wrap it in a default server
                        return {"0": data}
                    return data
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning("Could not load registered players, starting fresh")
        
        return {}
    
    def save_donations(self):
        """Save donation data to JSON file"""
        os.makedirs(os.path.dirname(self.donations_file), exist_ok=True)
        with open(self.donations_file, 'w') as f:
            json.dump(self.donations_data, f, indent=2)
    
    def save_registered_players(self):
        """Save registered players to JSON file"""
        os.makedirs(os.path.dirname(self.players_file), exist_ok=True)
        with open(self.players_file, 'w') as f:
            json.dump(self.registered_players, f, indent=2)
    
    def load_weekly_target(self) -> Dict:
        """Load weekly donation targets from JSON file"""
        target_file = "data/weekly_target.json"
        if os.path.exists(target_file):
            try:
                with open(target_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning("Could not load weekly target, starting fresh")
        return {"targets": {}}

    def save_weekly_target(self, targets: Dict):
        """Save weekly donation targets to JSON file"""
        target_file = "data/weekly_target.json"
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, 'w') as f:
            json.dump(targets, f, indent=2)

    def set_weekly_target(self, guild_id: str, amount: int):
        targets = self.load_weekly_target()
        targets["targets"][guild_id] = amount
        self.save_weekly_target(targets)

    def get_weekly_target(self, guild_id: str) -> int:
        targets = self.load_weekly_target()
        return targets["targets"].get(guild_id, 0)
    
    async def process_donation_message(self, message):
        """Process a potential donation message from AniGame bot"""
        try:
            logger.info(f"Processing message from {message.author.name} (ID: {message.author.id})")
            logger.info(f"Message content: '{message.content}'")
            logger.info(f"Message embeds: {len(message.embeds)}")
            
            # Log embed content if any
            for i, embed in enumerate(message.embeds):
                logger.info(f"Embed {i}: title='{embed.title}', description='{embed.description}'")
                for field in embed.fields:
                    logger.info(f"Embed field: name='{field.name}', value='{field.value}'")
            
            # Parse donation from AniGame bot message
            donation_info = self.parse_donation_message(message.content)
            
            # Also check embeds for donation info
            if not donation_info:
                for embed in message.embeds:
                    if embed.description:
                        donation_info = self.parse_donation_message(embed.description)
                        if donation_info:
                            logger.info(f"Found donation in embed description: {donation_info}")
                            break
                    if embed.title:
                        donation_info = self.parse_donation_message(embed.title)
                        if donation_info:
                            logger.info(f"Found donation in embed title: {donation_info}")
                            break
            
            if donation_info:
                logger.info(f"Donation detected: {donation_info}")
                
                # Look for mentioned users in the message
                mentioned_users = [str(user.id) for user in message.mentions]
                logger.info(f"Mentioned users: {mentioned_users}")
                
                # Also search for registered player names in the message content
                content_to_search = message.content
                for embed in message.embeds:
                    if embed.description:
                        content_to_search += " " + embed.description
                    if embed.title:
                        content_to_search += " " + embed.title
                
                logger.info(f"Searching for player names in: {content_to_search}")
                
                # Check each mentioned user if they're registered
                donation_recorded = False
                guild_id = str(message.guild.id)
                for user_id in mentioned_users:
                    if self.is_player_registered(guild_id, user_id):
                        player_name = self.registered_players[guild_id][user_id]
                        amount = donation_info['amount']
                        
                        # Update donation tracking
                        self.add_donation(str(message.guild.id), user_id, player_name, amount)
                        
                        logger.info(f"Recorded donation: {player_name} (ID: {user_id}) donated {amount}")
                        donation_recorded = True
                
                # If no mentioned users, search for registered player names in message content
                if not donation_recorded:
                    registered_players = self.registered_players.get(guild_id, {})
                    for user_id, player_name in registered_players.items():
                        # Clean player name for searching (remove special characters)
                        clean_player_name = player_name.replace("⚔️", "").replace("  ", " ").strip()
                        logger.info(f"Checking if '{clean_player_name}' is in message")
                        
                        if clean_player_name.lower() in content_to_search.lower():
                            amount = donation_info['amount']
                            
                            # Update donation tracking
                            self.add_donation(str(message.guild.id), user_id, player_name, amount)
                            
                            logger.info(f"Recorded donation by name match: {player_name} (ID: {user_id}) donated {amount}")
                            donation_recorded = True
                            break
                
                if donation_recorded:
                    # React to the message to show it was tracked
                    await message.add_reaction("✅")
                else:
                    logger.info(f"Donation detected but no registered users mentioned")
                    await message.add_reaction("❓")
            else:
                logger.info("No donation pattern found in message")
        
        except Exception as e:
            logger.error(f"Error processing donation message: {e}")
    
    def parse_donation_message(self, content: str) -> Optional[Dict]:
        """Parse donation amount from AniGame bot message"""
        # Specific patterns for AniGame donation messages
        patterns = [
            r"donated\s+\*\*(\d+(?:,\d+)*)\*\*\s+gold",
            r"you have donated\s+\*\*(\d+(?:,\d+)*)\*\*\s+gold",
            r"donated\s+(\d+(?:,\d+)*)\s+coins?",
            r"contributed\s+(\d+(?:,\d+)*)\s+coins?", 
            r"gave\s+(\d+(?:,\d+)*)\s+coins?",
            r"(\d+(?:,\d+)*)\s+coins?\s+donated",
            r"(\d+(?:,\d+)*)\s+coins?\s+to\s+the\s+clan",
            r"clan donation.*?(\d+(?:,\d+)*)",
            r"(\d+(?:,\d+)*)\s+coins?\s+added\s+to\s+clan",
            r"clan\s+treasury.*?(\d+(?:,\d+)*)",
            r"(\d+(?:,\d+)*)\s+coins?\s+clan\s+donation",
            r"deposited\s+(\d+(?:,\d+)*)\s+coins?",
            r"(\d+(?:,\d+)*)\s+coins?\s+deposited",
            r"(\d+(?:,\d+)*)\s+rubies?\s+donated",
            r"donated\s+(\d+(?:,\d+)*)\s+rubies?",
            r"(\d+(?:,\d+)*)\s+rubies?\s+to\s+the\s+clan",
            r"(\d+(?:,\d+)*)\s+rubies?\s+added\s+to\s+clan"
        ]
        
        content_lower = content.lower()
        
        # Check if message contains donation keywords
        donation_keywords = ["donated", "donation", "contribute", "clan", "gave", "treasury", "deposited", "coins", "rubies"]
        if not any(keyword in content_lower for keyword in donation_keywords):
            logger.info(f"No donation keywords found in: {content_lower}")
            return None
        
        # Try to extract amount
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, content_lower)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    amount = int(amount_str)
                    logger.info(f"Pattern {i+1} matched: {pattern} -> {amount}")
                    return {"amount": amount}
                except ValueError:
                    logger.info(f"Pattern {i+1} matched but failed to parse number: {amount_str}")
                    continue
        
        logger.info(f"No patterns matched for message: {content_lower}")
        return None
    
    def add_donation(self, guild_id: str, user_id: str, player_name: str, amount: int):
        """Add a donation record"""
        current_time = datetime.now(timezone.utc)
        timestamp = current_time.isoformat()
        guild_id = str(guild_id)
        
        # Initialize server data if not exists
        if guild_id not in self.donations_data:
            self.donations_data[guild_id] = {
                "weekly_donations": {},
                "total_donations": {},
                "last_reset": None
            }
        
        # Initialize user data if not exists
        if user_id not in self.donations_data[guild_id]["weekly_donations"]:
            self.donations_data[guild_id]["weekly_donations"][user_id] = {
                "name": player_name,
                "amount": 0,
                "donations": [],
                "week_start": timestamp  # Track when their week started
            }
        
        if user_id not in self.donations_data[guild_id]["total_donations"]:
            self.donations_data[guild_id]["total_donations"][user_id] = {
                "name": player_name,
                "amount": 0,
                "donations": []
            }
        
        # Check if player's week has expired (7 days from their first donation)
        week_start = datetime.fromisoformat(self.donations_data[guild_id]["weekly_donations"][user_id]["week_start"].replace('Z', '+00:00'))
        days_since_start = (current_time - week_start).days
        
        if days_since_start >= 7:
            # Reset weekly data for this player
            self.donations_data[guild_id]["weekly_donations"][user_id] = {
                "name": player_name,
                "amount": 0,
                "donations": [],
                "week_start": timestamp  # Start new week
            }
        
        # Add donation
        donation_record = {
            "amount": amount,
            "timestamp": timestamp
        }
        
        # Update weekly donations
        self.donations_data[guild_id]["weekly_donations"][user_id]["amount"] += amount
        self.donations_data[guild_id]["weekly_donations"][user_id]["donations"].append(donation_record)
        
        # Update total donations
        self.donations_data[guild_id]["total_donations"][user_id]["amount"] += amount
        self.donations_data[guild_id]["total_donations"][user_id]["donations"].append(donation_record)
        
        # Save data
        self.save_donations()
    
    def register_player(self, guild_id: str, user_id: str, player_name: str) -> bool:
        """Register a player"""
        guild_id = str(guild_id)
        if guild_id not in self.registered_players:
            self.registered_players[guild_id] = {}
        
        self.registered_players[guild_id][user_id] = player_name
        self.save_registered_players()
        logger.info(f"Registered player: {player_name} (ID: {user_id}) in server {guild_id}")
        return True
    
    def unregister_player(self, guild_id: str, user_id: str) -> bool:
        """Unregister a player"""
        guild_id = str(guild_id)
        if guild_id in self.registered_players and user_id in self.registered_players[guild_id]:
            player_name = self.registered_players[guild_id].pop(user_id)
            self.save_registered_players()
            logger.info(f"Unregistered player: {player_name} (ID: {user_id}) from server {guild_id}")
            return True
        return False
    
    def get_registered_players(self, guild_id: str) -> Dict:
        """Get all registered players for a server"""
        guild_id = str(guild_id)
        return self.registered_players.get(guild_id, {}).copy()
    
    def is_player_registered(self, guild_id: str, user_id: str) -> bool:
        """Check if a player is registered in this server"""
        guild_id = str(guild_id)
        return guild_id in self.registered_players and user_id in self.registered_players[guild_id]
    
    def get_weekly_donations(self, guild_id: str) -> Dict:
        """Get weekly donation data for a server"""
        guild_id = str(guild_id)
        return self.donations_data.get(guild_id, {}).get("weekly_donations", {})
    
    def get_total_donations(self, guild_id: str) -> Dict:
        """Get total donation data for a server"""
        guild_id = str(guild_id)
        return self.donations_data.get(guild_id, {}).get("total_donations", {})
    
    async def generate_weekly_report(self) -> str:
        """Generate weekly donation report"""
        weekly_data = self.donations_data["weekly_donations"]
        
        if not weekly_data:
            return "No donations recorded this week."
        
        # Sort by donation amount (descending)
        sorted_players = sorted(
            weekly_data.items(),
            key=lambda x: x[1]["amount"],
            reverse=True
        )
        
        report_lines = ["**Weekly Donation Summary:**\n"]
        total_donated = 0
        current_time = datetime.now(timezone.utc)
        
        for i, (user_id, data) in enumerate(sorted_players, 1):
            name = data["name"]
            amount = data["amount"]
            donation_count = len(data["donations"])
            
            # Calculate days remaining in player's week
            week_start = datetime.fromisoformat(data["week_start"].replace('Z', '+00:00'))
            days_elapsed = (current_time - week_start).days
            days_remaining = max(0, 7 - days_elapsed)
            
            total_donated += amount
            
            # Add medal emojis for top 3
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"{i}."
            
            report_lines.append(
                f"{emoji} **{name}**: {amount:,} coins ({donation_count} donations) - {days_remaining} days left"
            )
        
        report_lines.append(f"\n**Total Clan Donations**: {total_donated:,} coins")
        report_lines.append(f"**Active Donors**: {len(sorted_players)} players")
        
        return "\n".join(report_lines)
    
    def cleanup_expired_weeks(self):
        """Clean up expired weekly donation data"""
        current_time = datetime.now(timezone.utc)
        total_cleaned = 0
        
        for guild_id, guild_data in self.donations_data.items():
            if "weekly_donations" not in guild_data:
                continue
                
            expired_players = []
            
            for user_id, data in guild_data["weekly_donations"].items():
                week_start = datetime.fromisoformat(data["week_start"].replace('Z', '+00:00'))
                days_elapsed = (current_time - week_start).days
                
                if days_elapsed >= 7:
                    expired_players.append(user_id)
            
            # Remove expired weeks
            for user_id in expired_players:
                player_name = guild_data["weekly_donations"][user_id]["name"]
                del guild_data["weekly_donations"][user_id]
                logger.info(f"Cleaned up expired week for player: {player_name} in server {guild_id}")
                total_cleaned += 1
        
        if total_cleaned > 0:
            self.save_donations()
            logger.info(f"Cleaned up {total_cleaned} expired weekly records across all servers")
    
    def reset_weekly_data(self):
        """Reset weekly donation data (legacy function, now just cleans up expired weeks)"""
        self.cleanup_expired_weeks()
        # Update last_reset for all servers
        for guild_id, guild_data in self.donations_data.items():
            guild_data["last_reset"] = datetime.now(timezone.utc).isoformat()
        self.save_donations()
        logger.info("Weekly cleanup completed")
