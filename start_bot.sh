#!/bin/bash

# Telegram Signal Bot Startup Script
# This script starts the bot with proper error handling and logging

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Bot configuration
BOT_SCRIPT="telegram_bot_improved.py"
LOG_FILE="bot.log"
ENV_FILE=".env"

echo -e "${GREEN}🤖 Starting Telegram Signal Bot...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.8+ first.${NC}"
    exit 1
fi

# Check if required files exist
if [ ! -f "$BOT_SCRIPT" ]; then
    echo -e "${RED}❌ Bot script $BOT_SCRIPT not found!${NC}"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  Environment file $ENV_FILE not found.${NC}"
    echo -e "${YELLOW}   Creating from template...${NC}"
    
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}   Please edit .env file with your bot configuration and run again.${NC}"
        exit 1
    else
        echo -e "${RED}❌ .env.example file not found!${NC}"
        exit 1
    fi
fi

# Check if requirements are installed
echo -e "${YELLOW}📦 Checking requirements...${NC}"
if ! python3 -c "import telegram" &> /dev/null; then
    echo -e "${YELLOW}📦 Installing required packages...${NC}"
    pip3 install -r requirements.txt
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the bot
echo -e "${GREEN}🚀 Starting bot with logging to $LOG_FILE...${NC}"
echo -e "${GREEN}   Press Ctrl+C to stop the bot${NC}"
echo -e "${GREEN}   Logs are saved to $LOG_FILE${NC}"
echo ""

# Run the bot with logging
python3 "$BOT_SCRIPT" 2>&1 | tee "$LOG_FILE"

echo -e "${YELLOW}🛑 Bot stopped.${NC}"