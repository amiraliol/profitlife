# 🚀 Quick Start Guide - Telegram Signal Bot

Your Telegram Signal Bot is ready! Follow these steps to get it running:

## ✅ What's Ready

All files have been created and configured:
- ✅ Bot code (`telegram_bot_improved.py`)
- ✅ Configuration system (`config.py`)
- ✅ Database initialization
- ✅ Requirements installed
- ✅ Setup and start scripts
- ✅ Complete documentation

## 📋 Setup Steps (5 minutes)

### 1. Get Bot Token
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "My Signal Bot")
4. Choose a username (e.g., "MySignalBot")
5. Copy the bot token (looks like: `123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 2. Create Signal Channel
1. Create a new Telegram channel
2. Add your bot as an administrator
3. Forward any message from your channel to `@userinfobot`
4. Copy the channel ID (starts with `-100`)

### 3. Get Your User ID
1. Send any message to `@userinfobot`
2. Copy your user ID (a number like `123456789`)

### 4. Configure Bot
Edit the `.env` file with your details:
```bash
BOT_TOKEN=123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
SIGNAL_CHANNEL_ID=-1001234567890
ADMIN_USER_IDS=123456789
CHANNEL_USERNAME=your_channel_username
```

### 5. Start Bot
```bash
./start_bot.sh
```

## 🎯 Bot Features

### For Users:
- **Registration**: Phone number sharing + personal info
- **Profile**: Personal user profile with access level
- **Channel Access**: One-time invite links
- **Signals**: Automatic signal delivery to channel members

### For Admins:
- **Admin Panel**: Complete management dashboard
- **Send Signals**: Manual signal distribution
- **User Management**: View and manage all users
- **Broadcast**: Send messages to all users
- **Analytics**: User statistics and channel metrics

## 🔧 Commands

### User Commands:
- `/start` - Register with the bot
- `/menu` - Show main menu

### Admin Features:
- 🔧 Admin Panel
- 📤 Send Signal
- 👥 User List
- 📢 Broadcast Message
- 📊 Statistics

## 📱 User Flow

1. User sends `/start`
2. Bot requests phone number sharing
3. User enters name and selects access level
4. Bot generates one-time channel invite link
5. User joins channel and returns to bot
6. Bot verifies membership and activates account
7. User receives automatic signals from channel

## 🛠️ Troubleshooting

### Bot doesn't start?
- Check bot token in `.env` file
- Ensure bot is added to channel as admin
- Verify channel ID is correct

### Signals not being sent?
- Check channel membership verification
- Ensure users are channel members
- Check bot logs for errors

### Users can't join channel?
- Verify channel username in `.env`
- Check if invite links are being generated
- Ensure bot has admin rights in channel

## 📊 Database

The bot automatically creates `bot_database.db` with:
- User profiles and registration data
- Signal history and delivery stats
- Channel membership tracking
- Invite link management

## 🔒 Security

- All sensitive data in `.env` file
- Secure invite link generation
- Admin access control
- Comprehensive logging

## 📈 Monitoring

Check `bot.log` for:
- User registration events
- Signal delivery statistics
- Channel membership changes
- Error messages and debugging

## 🎉 You're All Set!

Your bot includes everything requested:
- ✅ Phone number sharing registration
- ✅ Personal user profiles
- ✅ One-time invite link generation
- ✅ Channel membership verification
- ✅ Signal forwarding to members only
- ✅ Admin panel for management
- ✅ Button-based interface
- ✅ Persian language support

**Happy Trading! 📈**

---

Need help? Check `README.md` for detailed documentation or `SUMMARY.md` for project overview.