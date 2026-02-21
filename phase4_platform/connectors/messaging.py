"""
Slack Connector — Deploys the twin on Slack.

From the original 2020 system: "I implemented a messaging bot in platforms like
Keybase and Slack, and the system was able to imposter me on messaging
platforms... My friends got fooled many times, thinking they were
texting me, but it was the bot."

This is the modern version targeting 85%+ similarity (up from 55-65%).

Setup:
1. Create a Slack App at api.slack.com
2. Add Bot Token Scopes: chat:write, channels:read, channels:history, users:read
3. Enable Socket Mode and get an App-Level Token
4. Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN in .env
"""

import asyncio
import random
import time
from loguru import logger


class SlackConnector:
    """
    Slack bot that responds as the digital twin.
    
    Features:
    - Responds to direct messages
    - Can be mentioned in channels
    - Adds human-like response delays
    - Logs all interactions for similarity analysis
    """
    
    def __init__(self, twin=None, response_delay: tuple[float, float] = (1.0, 5.0)):
        from config_loader import settings
        
        self.bot_token = settings.slack_bot_token
        self.app_token = settings.slack_app_token
        self.response_delay = response_delay
        self._twin = twin
        self._app = None
    
    @property
    def twin(self):
        if self._twin is None:
            from phase2_logic_twin.twin import DigitalTwin
            self._twin = DigitalTwin(access_tier="friends")
        return self._twin
    
    def start(self):
        """Start the Slack bot."""
        try:
            from slack_bolt import App
            from slack_bolt.adapter.socket_mode import SocketModeHandler
        except ImportError:
            logger.error("slack_bolt not installed. Run: pip install slack-bolt")
            return
        
        if not self.bot_token or not self.app_token:
            logger.error("SLACK_BOT_TOKEN and SLACK_APP_TOKEN required. See .env.example")
            return
        
        self._app = App(token=self.bot_token)
        
        # Handle direct messages
        @self._app.event("message")
        def handle_message(event, say):
            # Skip bot messages and thread replies for now
            if event.get("bot_id") or event.get("subtype"):
                return
            
            text = event.get("text", "")
            user = event.get("user", "unknown")
            channel = event.get("channel", "")
            
            if not text.strip():
                return
            
            logger.info(f"Slack message from {user}: {text[:50]}...")
            
            # Add human-like delay
            delay = random.uniform(*self.response_delay)
            time.sleep(delay)
            
            # Generate twin response
            response = self.twin.respond(
                message=text,
                sender=user,
                context=f"Slack channel: {channel}",
            )
            
            say(response)
            logger.info(f"Twin responded in {delay:.1f}s: {response[:50]}...")
        
        # Handle app mentions in channels
        @self._app.event("app_mention")
        def handle_mention(event, say):
            text = event.get("text", "")
            user = event.get("user", "unknown")
            
            # Remove the bot mention from the text
            import re
            text = re.sub(r"<@\w+>", "", text).strip()
            
            if not text:
                say("Hey! What's up?")
                return
            
            delay = random.uniform(*self.response_delay)
            time.sleep(delay)
            
            response = self.twin.respond(
                message=text,
                sender=user,
                context="Slack channel mention",
            )
            
            say(response)
        
        # Start
        logger.info("🤖 Slack connector starting...")
        handler = SocketModeHandler(self._app, self.app_token)
        handler.start()


class DiscordConnector:
    """
    Discord bot that responds as the digital twin.
    
    Similar to Slack connector but for Discord platforms.
    """
    
    def __init__(self, twin=None, response_delay: tuple[float, float] = (1.0, 5.0)):
        from config_loader import settings
        self.token = settings.discord_bot_token
        self.response_delay = response_delay
        self._twin = twin
    
    @property
    def twin(self):
        if self._twin is None:
            from phase2_logic_twin.twin import DigitalTwin
            self._twin = DigitalTwin(access_tier="friends")
        return self._twin
    
    def start(self):
        """Start the Discord bot."""
        try:
            import discord
        except ImportError:
            logger.error("discord.py not installed. Run: pip install discord.py")
            return
        
        if not self.token:
            logger.error("DISCORD_BOT_TOKEN required. See .env.example")
            return
        
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        
        @client.event
        async def on_ready():
            logger.info(f"Discord bot logged in as {client.user}")
        
        @client.event
        async def on_message(message):
            # Don't respond to ourselves
            if message.author == client.user:
                return
            
            # Respond to DMs or mentions
            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mentioned = client.user in message.mentions
            
            if not is_dm and not is_mentioned:
                return
            
            text = message.content
            # Remove mention
            import re
            text = re.sub(r"<@!?\d+>", "", text).strip()
            
            if not text:
                return
            
            # Human-like delay
            delay = random.uniform(*self.response_delay)
            await asyncio.sleep(delay)
            
            # Type indicator
            async with message.channel.typing():
                response = self.twin.respond(
                    message=text,
                    sender=str(message.author),
                    context=f"Discord {'DM' if is_dm else f'#{message.channel.name}'}",
                )
            
            await message.channel.send(response)
        
        logger.info("🤖 Discord connector starting...")
        client.run(self.token)
