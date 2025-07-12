import os
from typing import List

class Config:
    """Configuration settings for the Telegram bot"""
    
    # Bot Token (get from @BotFather)
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    # Signal Channel ID (the channel where signals are posted)
    SIGNAL_CHANNEL_ID: str = os.getenv("SIGNAL_CHANNEL_ID", "YOUR_SIGNAL_CHANNEL_ID_HERE")
    
    # Admin User IDs (users who can access admin panel)
    ADMIN_USER_IDS: List[int] = [
        int(user_id) for user_id in os.getenv("ADMIN_USER_IDS", "123456789").split(",")
    ]
    
    # Database settings
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_database.db")
    
    # Channel settings
    CHANNEL_USERNAME: str = os.getenv("CHANNEL_USERNAME", "YOUR_CHANNEL_USERNAME")
    CHANNEL_NAME: str = os.getenv("CHANNEL_NAME", "کانال سیگنال")
    
    # Bot settings
    MAX_USERS_PER_PAGE: int = int(os.getenv("MAX_USERS_PER_PAGE", "10"))
    INVITE_LINK_EXPIRY_HOURS: int = int(os.getenv("INVITE_LINK_EXPIRY_HOURS", "24"))
    
    # Messages
    WELCOME_MESSAGE: str = """
🌟 خوش آمدید به ربات سیگنال!

این ربات برای ارسال سیگنال‌های معاملاتی و مدیریت کاربران طراحی شده است.

برای شروع، لطفاً اطلاعات خود را ثبت کنید.
    """
    
    REGISTRATION_COMPLETE_MESSAGE: str = """
🎉 ثبت نام شما با موفقیت تکمیل شد!

حالا می‌توانید از تمام امکانات ربات استفاده کنید:
• دریافت سیگنال‌های معاملاتی
• مشاهده پروفایل شخصی
• عضویت در کانال اختصاصی
    """
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration settings"""
        if cls.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("⚠️ Warning: BOT_TOKEN is not set!")
            return False
        
        if cls.SIGNAL_CHANNEL_ID == "YOUR_SIGNAL_CHANNEL_ID_HERE":
            print("⚠️ Warning: SIGNAL_CHANNEL_ID is not set!")
            return False
        
        if 123456789 in cls.ADMIN_USER_IDS:
            print("⚠️ Warning: Default admin user ID is still in use!")
            return False
        
        return True
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables"""
        # Load from .env file if exists
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        return cls()