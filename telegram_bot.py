#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sqlite3
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib
import secrets

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    ReplyKeyboardRemove,
    ChatMember
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
SIGNAL_CHANNEL_ID = "YOUR_SIGNAL_CHANNEL_ID_HERE"  # Channel ID for signals
ADMIN_USER_IDS = [123456789]  # Replace with actual admin user IDs

# Conversation states
PHONE_NUMBER, NAME, PRODUCT_ACCESS = range(3)

class TelegramBot:
    def __init__(self):
        self.db_path = "bot_database.db"
        self.init_database()
        self.invite_links = {}  # Store one-time invite links
        
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                phone_number TEXT,
                name TEXT,
                product_access TEXT,
                registration_date TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                channel_member INTEGER DEFAULT 0
            )
        ''')
        
        # Signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_text TEXT,
                sent_date TIMESTAMP,
                admin_id INTEGER
            )
        ''')
        
        # Invite links table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invite_links (
                link_id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_date TIMESTAMP,
                used INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_user(self, user_id: int, username: str, phone: str, name: str, product_access: str):
        """Save user data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, phone_number, name, product_access, registration_date) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, phone, name, product_access, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'user_id': result[0],
                'username': result[1],
                'phone_number': result[2],
                'name': result[3],
                'product_access': result[4],
                'registration_date': result[5],
                'is_active': result[6],
                'channel_member': result[7]
            }
        return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all active users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE is_active = 1')
        results = cursor.fetchall()
        conn.close()
        
        users = []
        for result in results:
            users.append({
                'user_id': result[0],
                'username': result[1],
                'phone_number': result[2],
                'name': result[3],
                'product_access': result[4],
                'registration_date': result[5],
                'is_active': result[6],
                'channel_member': result[7]
            })
        return users
    
    def generate_invite_link(self, user_id: int) -> str:
        """Generate one-time invite link for user"""
        link_id = secrets.token_urlsafe(32)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO invite_links (link_id, user_id, created_date)
            VALUES (?, ?, ?)
        ''', (link_id, user_id, datetime.now()))
        
        conn.commit()
        conn.close()
        
        return f"https://t.me/joinchat/{link_id}"
    
    def save_signal(self, signal_text: str, admin_id: int):
        """Save signal to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signals (signal_text, sent_date, admin_id)
            VALUES (?, ?, ?)
        ''', (signal_text, datetime.now(), admin_id))
        
        conn.commit()
        conn.close()

bot_instance = TelegramBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler"""
    user = update.effective_user
    
    # Check if user is already registered
    existing_user = bot_instance.get_user(user.id)
    if existing_user:
        await show_main_menu(update, context)
        return ConversationHandler.END
    
    # Welcome message
    welcome_text = f"""
🌟 خوش آمدید {user.first_name}!

برای استفاده از ربات، لطفاً اطلاعات زیر را وارد کنید:

مرحله ۱: شماره تماس خود را به اشتراک بگذارید
    """
    
    # Phone number request keyboard
    keyboard = [
        [KeyboardButton("📱 اشتراک گذاری شماره تماس", request_contact=True)],
        [KeyboardButton("❌ انصراف")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    return PHONE_NUMBER

async def phone_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input"""
    if update.message.contact:
        phone_number = update.message.contact.phone_number
        context.user_data['phone_number'] = phone_number
        
        await update.message.reply_text(
            f"✅ شماره تماس شما ثبت شد: {phone_number}\n\n"
            "مرحله ۲: لطفاً نام و نام خانوادگی خود را وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return NAME
    elif update.message.text == "❌ انصراف":
        await update.message.reply_text(
            "❌ ثبت نام لغو شد. برای شروع مجدد /start را بزنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ لطفاً از دکمه اشتراک گذاری شماره استفاده کنید.")
        return PHONE_NUMBER

async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input"""
    name = update.message.text.strip()
    
    if len(name) < 2:
        await update.message.reply_text("❌ لطفاً نام صحیح وارد کنید (حداقل ۲ کاراکتر)")
        return NAME
    
    context.user_data['name'] = name
    
    # Product access keyboard
    keyboard = [
        [KeyboardButton("🥉 پایه")],
        [KeyboardButton("🥈 نقره‌ای")],
        [KeyboardButton("🥇 طلایی")],
        [KeyboardButton("💎 VIP")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"✅ نام شما ثبت شد: {name}\n\n"
        "مرحله ۳: نوع دسترسی محصول را انتخاب کنید:",
        reply_markup=reply_markup
    )
    return PRODUCT_ACCESS

async def product_access_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle product access selection"""
    product_access = update.message.text
    
    if product_access not in ["🥉 پایه", "🥈 نقره‌ای", "🥇 طلایی", "💎 VIP"]:
        await update.message.reply_text("❌ لطفاً یکی از گزینه‌های موجود را انتخاب کنید.")
        return PRODUCT_ACCESS
    
    # Save user data
    user = update.effective_user
    bot_instance.save_user(
        user.id,
        user.username or "",
        context.user_data['phone_number'],
        context.user_data['name'],
        product_access
    )
    
    await update.message.reply_text(
        f"✅ ثبت نام شما با موفقیت انجام شد!\n\n"
        f"📱 شماره تماس: {context.user_data['phone_number']}\n"
        f"👤 نام: {context.user_data['name']}\n"
        f"🎯 نوع دسترسی: {product_access}\n\n"
        "حالا می‌توانید از ربات استفاده کنید.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu to user"""
    user = update.effective_user
    
    # Check if user is admin
    is_admin = user.id in ADMIN_USER_IDS
    
    keyboard = [
        [InlineKeyboardButton("👤 پروفایل من", callback_data="profile")],
        [InlineKeyboardButton("📢 دریافت لینک کانال", callback_data="get_channel_link")],
        [InlineKeyboardButton("📊 آمار کانال", callback_data="channel_stats")],
    ]
    
    if is_admin:
        keyboard.extend([
            [InlineKeyboardButton("🔧 پنل مدیریت", callback_data="admin_panel")],
            [InlineKeyboardButton("📤 ارسال سیگنال", callback_data="send_signal")]
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"🏠 منوی اصلی\n\nسلام {user.first_name}! چه کاری می‌خواهید انجام دهید؟"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "profile":
        await show_profile(update, context)
    elif query.data == "get_channel_link":
        await get_channel_link(update, context)
    elif query.data == "channel_stats":
        await show_channel_stats(update, context)
    elif query.data == "admin_panel":
        await show_admin_panel(update, context)
    elif query.data == "send_signal":
        await send_signal_prompt(update, context)
    elif query.data == "back_to_main":
        await show_main_menu(update, context)
    elif query.data == "user_list":
        await show_user_list(update, context)
    elif query.data == "broadcast_message":
        await broadcast_prompt(update, context)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile"""
    user = update.effective_user
    user_data = bot_instance.get_user(user.id)
    
    if not user_data:
        await update.callback_query.edit_message_text("❌ پروفایل شما یافت نشد. لطفاً مجدداً ثبت نام کنید.")
        return
    
    profile_text = f"""
👤 پروفایل شما:

🆔 شناسه کاربری: {user_data['user_id']}
📱 شماره تماس: {user_data['phone_number']}
👤 نام: {user_data['name']}
🎯 نوع دسترسی: {user_data['product_access']}
📅 تاریخ ثبت نام: {user_data['registration_date'][:10]}
✅ وضعیت: {'فعال' if user_data['is_active'] else 'غیرفعال'}
📢 عضویت کانال: {'عضو' if user_data['channel_member'] else 'غیرعضو'}
    """
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(profile_text, reply_markup=reply_markup)

async def get_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send channel invite link"""
    user = update.effective_user
    
    # Generate one-time invite link
    invite_link = bot_instance.generate_invite_link(user.id)
    
    link_text = f"""
📢 لینک اختصاصی کانال سیگنال:

🔗 {invite_link}

⚠️ این لینک فقط برای شما و یک بار قابل استفاده است.
🕒 مدت اعتبار: ۲۴ ساعت

پس از عضویت در کانال، دوباره به ربات مراجعه کنید.
    """
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(link_text, reply_markup=reply_markup)

async def show_channel_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show channel statistics"""
    all_users = bot_instance.get_all_users()
    total_users = len(all_users)
    channel_members = sum(1 for user in all_users if user['channel_member'])
    
    stats_text = f"""
📊 آمار کانال:

👥 کل کاربران ربات: {total_users}
📢 اعضای کانال: {channel_members}
📈 نرخ عضویت: {(channel_members/total_users*100):.1f}% (اگر کاربر وجود دارد)

🎯 تفکیک بر اساس نوع دسترسی:
    """
    
    access_types = {}
    for user in all_users:
        access_type = user['product_access']
        access_types[access_type] = access_types.get(access_type, 0) + 1
    
    for access_type, count in access_types.items():
        stats_text += f"\n{access_type}: {count} نفر"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(stats_text, reply_markup=reply_markup)

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel"""
    user = update.effective_user
    
    if user.id not in ADMIN_USER_IDS:
        await update.callback_query.edit_message_text("❌ شما دسترسی مدیریتی ندارید.")
        return
    
    admin_text = """
🔧 پنل مدیریت:

به پنل مدیریت خوش آمدید. چه کاری می‌خواهید انجام دهید؟
    """
    
    keyboard = [
        [InlineKeyboardButton("📤 ارسال سیگنال", callback_data="send_signal")],
        [InlineKeyboardButton("👥 لیست کاربران", callback_data="user_list")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast_message")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(admin_text, reply_markup=reply_markup)

async def show_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user list for admin"""
    user = update.effective_user
    
    if user.id not in ADMIN_USER_IDS:
        return
    
    all_users = bot_instance.get_all_users()
    
    if not all_users:
        text = "👥 هیچ کاربری ثبت نام نکرده است."
    else:
        text = f"👥 لیست کاربران ({len(all_users)} نفر):\n\n"
        for i, user_data in enumerate(all_users[:10], 1):  # Show first 10 users
            text += f"{i}. {user_data['name']} (@{user_data['username'] or 'بدون نام کاربری'})\n"
            text += f"   📱 {user_data['phone_number']} | {user_data['product_access']}\n\n"
        
        if len(all_users) > 10:
            text += f"... و {len(all_users) - 10} کاربر دیگر"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل مدیریت", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def send_signal_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to send signal"""
    user = update.effective_user
    
    if user.id not in ADMIN_USER_IDS:
        return
    
    await update.callback_query.edit_message_text(
        "📤 ارسال سیگنال:\n\nلطفاً متن سیگنال خود را در پیام بعدی ارسال کنید.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]])
    )
    
    context.user_data['waiting_for_signal'] = True

async def broadcast_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to broadcast message"""
    user = update.effective_user
    
    if user.id not in ADMIN_USER_IDS:
        return
    
    await update.callback_query.edit_message_text(
        "📢 پیام همگانی:\n\nلطفاً متن پیام همگانی خود را در پیام بعدی ارسال کنید.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]])
    )
    
    context.user_data['waiting_for_broadcast'] = True

async def handle_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin messages (signals and broadcasts)"""
    user = update.effective_user
    
    if user.id not in ADMIN_USER_IDS:
        return
    
    if context.user_data.get('waiting_for_signal'):
        # Send signal to all channel members
        signal_text = f"📊 سیگنال جدید:\n\n{update.message.text}"
        
        all_users = bot_instance.get_all_users()
        channel_members = [user for user in all_users if user['channel_member']]
        
        sent_count = 0
        for user_data in channel_members:
            try:
                await context.bot.send_message(
                    chat_id=user_data['user_id'],
                    text=signal_text
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending signal to user {user_data['user_id']}: {e}")
        
        # Save signal to database
        bot_instance.save_signal(update.message.text, user.id)
        
        await update.message.reply_text(
            f"✅ سیگنال با موفقیت برای {sent_count} کاربر ارسال شد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
        )
        
        context.user_data['waiting_for_signal'] = False
    
    elif context.user_data.get('waiting_for_broadcast'):
        # Send broadcast message to all users
        broadcast_text = f"📢 پیام مدیریت:\n\n{update.message.text}"
        
        all_users = bot_instance.get_all_users()
        sent_count = 0
        for user_data in all_users:
            try:
                await context.bot.send_message(
                    chat_id=user_data['user_id'],
                    text=broadcast_text
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending broadcast to user {user_data['user_id']}: {e}")
        
        await update.message.reply_text(
            f"✅ پیام همگانی با موفقیت برای {sent_count} کاربر ارسال شد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
        )
        
        context.user_data['waiting_for_broadcast'] = False

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu"""
    await show_main_menu(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation"""
    await update.message.reply_text(
        "❌ عملیات لغو شد.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Create conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE_NUMBER: [
                MessageHandler(filters.CONTACT, phone_number_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number_handler),
            ],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler)],
            PRODUCT_ACCESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_access_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages))
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()