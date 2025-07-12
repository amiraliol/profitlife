#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import secrets
import json

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    ReplyKeyboardRemove,
    ChatMember,
    ChatMemberStatus,
    Message
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    ChatMemberHandler
)
from telegram.error import TelegramError

from config import Config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configuration
config = Config.load_from_env()

# Conversation states
PHONE_NUMBER, NAME, PRODUCT_ACCESS = range(3)

class TelegramBot:
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone_number TEXT,
                name TEXT,
                product_access TEXT,
                registration_date TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                channel_member INTEGER DEFAULT 0,
                last_activity TIMESTAMP
            )
        ''')
        
        # Signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_text TEXT,
                signal_type TEXT,
                sent_date TIMESTAMP,
                admin_id INTEGER,
                recipient_count INTEGER DEFAULT 0
            )
        ''')
        
        # Invite links table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invite_links (
                link_id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_date TIMESTAMP,
                expiry_date TIMESTAMP,
                used INTEGER DEFAULT 0,
                used_date TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Channel events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT,
                event_date TIMESTAMP,
                details TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_user(self, user_id: int, username: str, first_name: str, last_name: str, 
                  phone: str, name: str, product_access: str):
        """Save user data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, phone_number, name, 
             product_access, registration_date, last_activity) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, phone, name, 
              product_access, datetime.now(), datetime.now()))
        
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
                'first_name': result[2],
                'last_name': result[3],
                'phone_number': result[4],
                'name': result[5],
                'product_access': result[6],
                'registration_date': result[7],
                'is_active': result[8],
                'channel_member': result[9],
                'last_activity': result[10]
            }
        return None
    
    def update_user_activity(self, user_id: int):
        """Update user's last activity timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET last_activity = ? WHERE user_id = ?
        ''', (datetime.now(), user_id))
        
        conn.commit()
        conn.close()
    
    def update_channel_membership(self, user_id: int, is_member: bool):
        """Update user's channel membership status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET channel_member = ? WHERE user_id = ?
        ''', (1 if is_member else 0, user_id))
        
        conn.commit()
        conn.close()
    
    def get_all_users(self, active_only: bool = True) -> List[Dict]:
        """Get all users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute('SELECT * FROM users WHERE is_active = 1')
        else:
            cursor.execute('SELECT * FROM users')
        
        results = cursor.fetchall()
        conn.close()
        
        users = []
        for result in results:
            users.append({
                'user_id': result[0],
                'username': result[1],
                'first_name': result[2],
                'last_name': result[3],
                'phone_number': result[4],
                'name': result[5],
                'product_access': result[6],
                'registration_date': result[7],
                'is_active': result[8],
                'channel_member': result[9],
                'last_activity': result[10]
            })
        return users
    
    def get_channel_members(self) -> List[Dict]:
        """Get all channel members"""
        return [user for user in self.get_all_users() if user['channel_member']]
    
    def generate_invite_link(self, user_id: int) -> str:
        """Generate one-time invite link for user"""
        link_id = secrets.token_urlsafe(32)
        expiry_date = datetime.now() + timedelta(hours=config.INVITE_LINK_EXPIRY_HOURS)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO invite_links (link_id, user_id, created_date, expiry_date)
            VALUES (?, ?, ?, ?)
        ''', (link_id, user_id, datetime.now(), expiry_date))
        
        conn.commit()
        conn.close()
        
        return f"https://t.me/{config.CHANNEL_USERNAME}?start={link_id}"
    
    def validate_invite_link(self, link_id: str) -> Optional[int]:
        """Validate invite link and return user_id if valid"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, expiry_date FROM invite_links 
            WHERE link_id = ? AND used = 0
        ''', (link_id,))
        result = cursor.fetchone()
        
        if result:
            user_id, expiry_date = result
            if datetime.now() < datetime.fromisoformat(expiry_date):
                return user_id
        
        conn.close()
        return None
    
    def mark_invite_used(self, link_id: str):
        """Mark invite link as used"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE invite_links SET used = 1, used_date = ? WHERE link_id = ?
        ''', (datetime.now(), link_id))
        
        conn.commit()
        conn.close()
    
    def save_signal(self, signal_text: str, signal_type: str, admin_id: int, recipient_count: int):
        """Save signal to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signals (signal_text, signal_type, sent_date, admin_id, recipient_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (signal_text, signal_type, datetime.now(), admin_id, recipient_count))
        
        conn.commit()
        conn.close()
    
    def log_channel_event(self, user_id: int, event_type: str, details: str = ""):
        """Log channel-related events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO channel_events (user_id, event_type, event_date, details)
            VALUES (?, ?, ?, ?)
        ''', (user_id, event_type, datetime.now(), details))
        
        conn.commit()
        conn.close()

bot_instance = TelegramBot()

async def check_channel_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Check if user is a member of the signal channel"""
    try:
        member = await context.bot.get_chat_member(config.SIGNAL_CHANNEL_ID, user_id)
        is_member = member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
        
        # Update database
        bot_instance.update_channel_membership(user_id, is_member)
        
        # Log event
        status = "joined" if is_member else "left"
        bot_instance.log_channel_event(user_id, f"channel_{status}")
        
        return is_member
    except TelegramError as e:
        logger.error(f"Error checking channel membership for user {user_id}: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler"""
    user = update.effective_user
    bot_instance.update_user_activity(user.id)
    
    # Check if user is already registered
    existing_user = bot_instance.get_user(user.id)
    if existing_user:
        await show_main_menu(update, context)
        return ConversationHandler.END
    
    # Check for invite link parameter
    if context.args:
        link_id = context.args[0]
        valid_user_id = bot_instance.validate_invite_link(link_id)
        if valid_user_id and valid_user_id == user.id:
            bot_instance.mark_invite_used(link_id)
            context.user_data['from_invite_link'] = True
    
    # Welcome message
    welcome_text = f"""
🌟 خوش آمدید {user.first_name}!

{config.WELCOME_MESSAGE}

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
        user.first_name or "",
        user.last_name or "",
        context.user_data['phone_number'],
        context.user_data['name'],
        product_access
    )
    
    # Check channel membership
    is_member = await check_channel_membership(context, user.id)
    
    registration_text = f"""
✅ ثبت نام شما با موفقیت انجام شد!

{config.REGISTRATION_COMPLETE_MESSAGE}

📊 اطلاعات شما:
📱 شماره تماس: {context.user_data['phone_number']}
👤 نام: {context.user_data['name']}
🎯 نوع دسترسی: {product_access}
📢 وضعیت عضویت: {'عضو کانال' if is_member else 'غیرعضو'}
    """
    
    await update.message.reply_text(
        registration_text,
        reply_markup=ReplyKeyboardRemove()
    )
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu to user"""
    user = update.effective_user
    bot_instance.update_user_activity(user.id)
    
    # Check if user is admin
    is_admin = user.id in config.ADMIN_USER_IDS
    
    # Check channel membership
    is_member = await check_channel_membership(context, user.id)
    
    keyboard = [
        [InlineKeyboardButton("👤 پروفایل من", callback_data="profile")],
        [InlineKeyboardButton("📊 آمار کانال", callback_data="channel_stats")],
    ]
    
    if is_member:
        keyboard.append([InlineKeyboardButton("📢 وضعیت عضویت", callback_data="membership_status")])
    else:
        keyboard.append([InlineKeyboardButton("📢 دریافت لینک کانال", callback_data="get_channel_link")])
    
    if is_admin:
        keyboard.extend([
            [InlineKeyboardButton("🔧 پنل مدیریت", callback_data="admin_panel")],
            [InlineKeyboardButton("📤 ارسال سیگنال", callback_data="send_signal")]
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    membership_emoji = "✅" if is_member else "❌"
    text = f"""
🏠 منوی اصلی

سلام {user.first_name}! 
{membership_emoji} وضعیت عضویت: {'عضو کانال' if is_member else 'غیرعضو'}

چه کاری می‌خواهید انجام دهید؟
    """
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    bot_instance.update_user_activity(user_id)
    
    if query.data == "profile":
        await show_profile(update, context)
    elif query.data == "get_channel_link":
        await get_channel_link(update, context)
    elif query.data == "membership_status":
        await show_membership_status(update, context)
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
    elif query.data == "refresh_membership":
        await refresh_membership(update, context)

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
⏰ آخرین فعالیت: {user_data['last_activity'][:16] if user_data['last_activity'] else 'نامشخص'}
✅ وضعیت: {'فعال' if user_data['is_active'] else 'غیرفعال'}
📢 عضویت کانال: {'عضو' if user_data['channel_member'] else 'غیرعضو'}
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی عضویت", callback_data="refresh_membership")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(profile_text, reply_markup=reply_markup)

async def get_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send channel invite link"""
    user = update.effective_user
    
    # Generate one-time invite link
    invite_link = bot_instance.generate_invite_link(user.id)
    
    link_text = f"""
📢 لینک اختصاصی کانال {config.CHANNEL_NAME}:

🔗 {invite_link}

⚠️ مهم:
• این لینک فقط برای شما و یک بار قابل استفاده است
• مدت اعتبار: {config.INVITE_LINK_EXPIRY_HOURS} ساعت
• پس از عضویت، به ربات برگردید تا عضویت شما تأیید شود

📱 نحوه استفاده:
۱. روی لینک کلیک کنید
۲. در کانال عضو شوید
۳. به ربات برگردید و دکمه "🔄 بروزرسانی عضویت" را بزنید
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی عضویت", callback_data="refresh_membership")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(link_text, reply_markup=reply_markup)

async def show_membership_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show membership status"""
    user = update.effective_user
    is_member = await check_channel_membership(context, user.id)
    
    status_text = f"""
📢 وضعیت عضویت کانال:

{'✅ شما عضو کانال هستید' if is_member else '❌ شما عضو کانال نیستید'}

🏷️ نام کانال: {config.CHANNEL_NAME}
🔗 آدرس کانال: @{config.CHANNEL_USERNAME}

{'🎉 شما مشمول دریافت سیگنال‌ها هستید!' if is_member else '⚠️ برای دریافت سیگنال‌ها باید عضو کانال شوید.'}
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی وضعیت", callback_data="refresh_membership")],
    ]
    
    if not is_member:
        keyboard.append([InlineKeyboardButton("📢 دریافت لینک کانال", callback_data="get_channel_link")])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(status_text, reply_markup=reply_markup)

async def refresh_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh user's membership status"""
    user = update.effective_user
    is_member = await check_channel_membership(context, user.id)
    
    if is_member:
        await update.callback_query.edit_message_text(
            "✅ عضویت شما تأیید شد! حالا مشمول دریافت سیگنال‌ها هستید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]])
        )
    else:
        await update.callback_query.edit_message_text(
            "❌ عضویت شما تأیید نشد. لطفاً ابتدا عضو کانال شوید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 دریافت لینک کانال", callback_data="get_channel_link")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
            ])
        )

async def show_channel_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show channel statistics"""
    all_users = bot_instance.get_all_users()
    total_users = len(all_users)
    channel_members = bot_instance.get_channel_members()
    member_count = len(channel_members)
    
    stats_text = f"""
📊 آمار کانال:

👥 کل کاربران ربات: {total_users}
📢 اعضای کانال: {member_count}
📈 نرخ عضویت: {(member_count/total_users*100):.1f}% (اگر کاربر وجود دارد)

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
    
    if user.id not in config.ADMIN_USER_IDS:
        await update.callback_query.edit_message_text("❌ شما دسترسی مدیریتی ندارید.")
        return
    
    all_users = bot_instance.get_all_users()
    channel_members = bot_instance.get_channel_members()
    
    admin_text = f"""
🔧 پنل مدیریت:

📊 آمار کلی:
• کل کاربران: {len(all_users)}
• اعضای کانال: {len(channel_members)}
• نرخ عضویت: {(len(channel_members)/len(all_users)*100):.1f}%

چه کاری می‌خواهید انجام دهید؟
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
    
    if user.id not in config.ADMIN_USER_IDS:
        return
    
    all_users = bot_instance.get_all_users()
    
    if not all_users:
        text = "👥 هیچ کاربری ثبت نام نکرده است."
    else:
        text = f"👥 لیست کاربران ({len(all_users)} نفر):\n\n"
        for i, user_data in enumerate(all_users[:config.MAX_USERS_PER_PAGE], 1):
            member_status = "✅" if user_data['channel_member'] else "❌"
            text += f"{i}. {user_data['name']} {member_status}\n"
            text += f"   @{user_data['username'] or 'بدون نام کاربری'}\n"
            text += f"   📱 {user_data['phone_number']} | {user_data['product_access']}\n\n"
        
        if len(all_users) > config.MAX_USERS_PER_PAGE:
            text += f"... و {len(all_users) - config.MAX_USERS_PER_PAGE} کاربر دیگر"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل مدیریت", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def send_signal_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to send signal"""
    user = update.effective_user
    
    if user.id not in config.ADMIN_USER_IDS:
        return
    
    channel_members = bot_instance.get_channel_members()
    
    await update.callback_query.edit_message_text(
        f"📤 ارسال سیگنال:\n\n"
        f"سیگنال برای {len(channel_members)} عضو کانال ارسال خواهد شد.\n\n"
        f"لطفاً متن سیگنال خود را در پیام بعدی ارسال کنید.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]])
    )
    
    context.user_data['waiting_for_signal'] = True

async def broadcast_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to broadcast message"""
    user = update.effective_user
    
    if user.id not in config.ADMIN_USER_IDS:
        return
    
    all_users = bot_instance.get_all_users()
    
    await update.callback_query.edit_message_text(
        f"📢 پیام همگانی:\n\n"
        f"پیام برای {len(all_users)} کاربر ارسال خواهد شد.\n\n"
        f"لطفاً متن پیام همگانی خود را در پیام بعدی ارسال کنید.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]])
    )
    
    context.user_data['waiting_for_broadcast'] = True

async def handle_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin messages (signals and broadcasts)"""
    user = update.effective_user
    
    if user.id not in config.ADMIN_USER_IDS:
        return
    
    if context.user_data.get('waiting_for_signal'):
        # Send signal to all channel members
        signal_text = f"🚨 سیگنال جدید:\n\n{update.message.text}\n\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        channel_members = bot_instance.get_channel_members()
        
        sent_count = 0
        failed_count = 0
        
        for user_data in channel_members:
            try:
                await context.bot.send_message(
                    chat_id=user_data['user_id'],
                    text=signal_text,
                    parse_mode='HTML'
                )
                sent_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending signal to user {user_data['user_id']}: {e}")
        
        # Save signal to database
        bot_instance.save_signal(update.message.text, "signal", user.id, sent_count)
        
        result_text = f"✅ سیگنال با موفقیت ارسال شد!\n\n"
        result_text += f"📊 آمار ارسال:\n"
        result_text += f"• موفق: {sent_count}\n"
        result_text += f"• ناموفق: {failed_count}\n"
        result_text += f"• کل اعضا: {len(channel_members)}"
        
        await update.message.reply_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
        )
        
        context.user_data['waiting_for_signal'] = False
    
    elif context.user_data.get('waiting_for_broadcast'):
        # Send broadcast message to all users
        broadcast_text = f"📢 پیام مدیریت:\n\n{update.message.text}\n\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        all_users = bot_instance.get_all_users()
        
        sent_count = 0
        failed_count = 0
        
        for user_data in all_users:
            try:
                await context.bot.send_message(
                    chat_id=user_data['user_id'],
                    text=broadcast_text,
                    parse_mode='HTML'
                )
                sent_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending broadcast to user {user_data['user_id']}: {e}")
        
        # Save broadcast to database
        bot_instance.save_signal(update.message.text, "broadcast", user.id, sent_count)
        
        result_text = f"✅ پیام همگانی با موفقیت ارسال شد!\n\n"
        result_text += f"📊 آمار ارسال:\n"
        result_text += f"• موفق: {sent_count}\n"
        result_text += f"• ناموفق: {failed_count}\n"
        result_text += f"• کل کاربران: {len(all_users)}"
        
        await update.message.reply_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
        )
        
        context.user_data['waiting_for_broadcast'] = False

async def handle_channel_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new posts in the signal channel for automatic forwarding"""
    if update.channel_post and str(update.channel_post.chat.id) == config.SIGNAL_CHANNEL_ID:
        # This is a new post in the signal channel
        post_text = update.channel_post.text or update.channel_post.caption
        
        if post_text:
            # Forward to all channel members
            channel_members = bot_instance.get_channel_members()
            
            signal_text = f"📊 سیگنال خودکار:\n\n{post_text}\n\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            sent_count = 0
            for user_data in channel_members:
                try:
                    await context.bot.send_message(
                        chat_id=user_data['user_id'],
                        text=signal_text
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error forwarding signal to user {user_data['user_id']}: {e}")
            
            # Save auto-forwarded signal
            bot_instance.save_signal(post_text, "auto_forward", 0, sent_count)
            
            logger.info(f"Auto-forwarded signal to {sent_count} users")

async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chat member updates (join/leave events)"""
    if update.chat_member:
        user_id = update.chat_member.from_user.id
        chat_id = str(update.chat_member.chat.id)
        
        if chat_id == config.SIGNAL_CHANNEL_ID:
            # Channel membership change
            old_status = update.chat_member.old_chat_member.status
            new_status = update.chat_member.new_chat_member.status
            
            was_member = old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
            is_member = new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
            
            if was_member != is_member:
                # Membership status changed
                bot_instance.update_channel_membership(user_id, is_member)
                
                if is_member:
                    bot_instance.log_channel_event(user_id, "channel_joined")
                    # Send welcome message to new member
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"🎉 خوش آمدید به کانال {config.CHANNEL_NAME}!\n\n"
                                 f"از این پس سیگنال‌های معاملاتی را دریافت خواهید کرد.",
                        )
                    except Exception as e:
                        logger.error(f"Error sending welcome message to user {user_id}: {e}")
                else:
                    bot_instance.log_channel_event(user_id, "channel_left")

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
    if not config.validate_config():
        logger.error("Configuration validation failed. Please check your settings.")
        return
    
    # Create application
    application = Application.builder().token(config.BOT_TOKEN).build()
    
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
    application.add_handler(MessageHandler(filters.StatusUpdate.CHAT_MEMBER, chat_member_handler))
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, handle_channel_posts))
    
    logger.info("Bot started successfully!")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()