#!/bin/bash

# Telegram Signal Bot Setup Script
# This script helps users configure the bot quickly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Welcome to Telegram Signal Bot Setup!${NC}"
echo -e "${BLUE}This script will help you configure your bot.${NC}"
echo ""

# Function to prompt for input
prompt_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        if [ -z "$input" ]; then
            input="$default"
        fi
    else
        read -p "$prompt: " input
        while [ -z "$input" ]; do
            echo -e "${RED}This field is required!${NC}"
            read -p "$prompt: " input
        done
    fi
    
    eval "$var_name='$input'"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.8+ first.${NC}"
    exit 1
fi

# Install requirements
echo -e "${YELLOW}📦 Installing required packages...${NC}"
pip3 install -r requirements.txt

# Create .env file
echo -e "${YELLOW}⚙️  Configuring bot settings...${NC}"
echo ""

# Bot Token
echo -e "${BLUE}1. Bot Token${NC}"
echo "   Get your bot token from @BotFather on Telegram"
echo "   1. Send /newbot to @BotFather"
echo "   2. Choose a name and username for your bot"
echo "   3. Copy the token provided"
echo ""
prompt_input "Enter your bot token" "" "BOT_TOKEN"

# Channel ID
echo ""
echo -e "${BLUE}2. Signal Channel${NC}"
echo "   1. Create a channel for signals"
echo "   2. Add your bot to the channel as admin"
echo "   3. Forward a message from the channel to @userinfobot"
echo "   4. Copy the channel ID (starts with -100)"
echo ""
prompt_input "Enter your channel ID" "" "SIGNAL_CHANNEL_ID"

# Channel Username
echo ""
echo -e "${BLUE}3. Channel Username${NC}"
echo "   Enter your channel username without @"
echo ""
prompt_input "Enter channel username" "" "CHANNEL_USERNAME"

# Channel Name
echo ""
echo -e "${BLUE}4. Channel Name${NC}"
echo "   Enter a display name for your channel"
echo ""
prompt_input "Enter channel name" "کانال سیگنال" "CHANNEL_NAME"

# Admin User IDs
echo ""
echo -e "${BLUE}5. Admin User IDs${NC}"
echo "   Get your user ID from @userinfobot"
echo "   For multiple admins, separate with commas"
echo ""
prompt_input "Enter admin user IDs" "" "ADMIN_USER_IDS"

# Optional settings
echo ""
echo -e "${BLUE}6. Optional Settings${NC}"
prompt_input "Database file path" "bot_database.db" "DATABASE_PATH"
prompt_input "Max users per page" "10" "MAX_USERS_PER_PAGE"
prompt_input "Invite link expiry hours" "24" "INVITE_LINK_EXPIRY_HOURS"

# Create .env file
echo ""
echo -e "${YELLOW}📝 Creating configuration file...${NC}"
cat > .env << EOF
# Telegram Bot Configuration
BOT_TOKEN=$BOT_TOKEN
SIGNAL_CHANNEL_ID=$SIGNAL_CHANNEL_ID
ADMIN_USER_IDS=$ADMIN_USER_IDS

# Channel Configuration
CHANNEL_USERNAME=$CHANNEL_USERNAME
CHANNEL_NAME=$CHANNEL_NAME

# Database Configuration
DATABASE_PATH=$DATABASE_PATH

# Bot Settings
MAX_USERS_PER_PAGE=$MAX_USERS_PER_PAGE
INVITE_LINK_EXPIRY_HOURS=$INVITE_LINK_EXPIRY_HOURS
EOF

echo -e "${GREEN}✅ Configuration saved to .env file!${NC}"
echo ""

# Make scripts executable
chmod +x start_bot.sh

echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "   1. Make sure your bot is added to the channel as admin"
echo "   2. Test the configuration by running: ./start_bot.sh"
echo "   3. Send /start to your bot to test registration"
echo ""
echo -e "${BLUE}🚀 To start your bot, run:${NC}"
echo "   ./start_bot.sh"
echo ""
echo -e "${BLUE}📚 For more information, check the README.md file${NC}"