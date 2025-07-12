# تلگرام بات با ارسال خودکار سیگنال، ذخیره پروفایل و ارسال به مخاطبین عضو

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, ChannelPostHandler
import logging, json, os, random, string

# فعال کردن لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# دیتابیس ساده برای کاربران
USER_DB_FILE = 'users.json'
def load_users():
    if not os.path.exists(USER_DB_FILE): return {}
    with open(USER_DB_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

users = load_users()

# شناسه کانال رسمی
OFFICIAL_CHANNEL_ID = -1002443021723  # جایگزین شود با آیدی واقعی کانال شما

# شناسه ادمین ها (عددی)
ADMIN_IDS = [123456789]  # آیدی عددی ادمین ها را اینجا قرار دهید

# ساخت لینک یک‌بار مصرف برای عضویت در کانال
def generate_invite_link(user_id):
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"https://t.me/YOUR_CHANNEL?start={suffix}"

# منوی اصلی به صورت دکمه
MAIN_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("👤 پروفایل", callback_data='profile'),
        InlineKeyboardButton("📢 دریافت لینک کانال", callback_data='get_channel_link')
    ],
    [
        InlineKeyboardButton("📦 اشتراک‌ها", callback_data='subscriptions'),
        InlineKeyboardButton("🎓 آموزش", callback_data='education')
    ],
    [
        InlineKeyboardButton("🛟 ارتباط با پشتیبانی", url='https://t.me/melika_sadat1')
    ]
])

# /start command handler
def start(update: Update, context: CallbackContext):
    user_id = str(update.message.chat_id)

    if user_id not in users:
        users[user_id] = {"step": "phone"}
        save_users(users)
        btn = KeyboardButton(text="📞 ارسال شماره تماس", request_contact=True)
        update.message.reply_text("برای شروع، لطفاً شماره تماس خود را ارسال کنید:",
                                  reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True))
    else:
        update.message.reply_text("از منوی زیر استفاده کنید:", reply_markup=MAIN_MENU)

# دکمه‌های منو

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = str(query.message.chat_id)

    if query.data == 'get_channel_link':
        link = generate_invite_link(user_id)
        query.edit_message_text(text=f"📢 لینک اختصاصی عضویت شما در کانال:\n{link}", reply_markup=MAIN_MENU)

    elif query.data == 'profile':
        if user_id in users:
            u = users[user_id]
            text = f"👤 پروفایل شما:\n📞 شماره: {u.get('phone')}\n🧑‍💼 نام: {u.get('name')}\n📦 دسترسی: {u.get('product', '---')}"
            query.edit_message_text(text=text, reply_markup=MAIN_MENU)
        else:
            query.edit_message_text("برای شروع ابتدا /start را بزنید.", reply_markup=MAIN_MENU)

    elif query.data == 'subscriptions':
        query.edit_message_text("📦 در حال حاضر اشتراک شما فعال است چون عضو کانال هستید. به‌روزرسانی‌های جدید به‌صورت خودکار برای شما ارسال می‌شود.", reply_markup=MAIN_MENU)

    elif query.data == 'education':
        query.edit_message_text("🎓 آموزش‌ها به‌زودی در دسترس خواهند بود. در کانال عضو باشید.", reply_markup=MAIN_MENU)

    # پنل ادمین
    elif query.data == 'admin_send_signal' and int(user_id) in ADMIN_IDS:
        context.user_data['await_signal'] = True
        query.edit_message_text("✏️ لطفاً سیگنال مورد نظر را ارسال کنید:")

# گرفتن شماره تماس
def contact_handler(update: Update, context: CallbackContext):
    user_id = str(update.message.chat_id)
    contact = update.message.contact.phone_number
    users[user_id] = {
        "phone": contact,
        "step": "name"
    }
    save_users(users)
    update.message.reply_text("✅ شماره ذخیره شد. لطفاً نام کامل خود را ارسال کنید:")

# گرفتن نام و ثبت پروفایل
def name_handler(update: Update, context: CallbackContext):
    user_id = str(update.message.chat_id)
    if user_id in users and users[user_id].get("step") == "name":
        users[user_id]["name"] = update.message.text
        users[user_id]["step"] = "product"
        save_users(users)
        update.message.reply_text("✅ نام شما ذخیره شد. لطفاً نام محصول/دسترسی مورد نظر خود را وارد کنید:")

# گرفتن دسترسی/محصول
def product_handler(update: Update, context: CallbackContext):
    user_id = str(update.message.chat_id)
    if user_id in users and users[user_id].get("step") == "product":
        users[user_id]["product"] = update.message.text
        users[user_id]["step"] = "done"
        save_users(users)
        update.message.reply_text("✅ دسترسی شما ثبت شد. از منوی زیر استفاده کنید:", reply_markup=MAIN_MENU)

# ارسال پیام به تمام کاربران عضو شده
def broadcast_signal(text: str):
    """ارسال پیام به تمام کاربران کامل ثبت‌نام‌شده که عضو کانال هستند."""
    for uid, data in users.items():
        if data.get("step") != "done":
            continue
        try:
            member = updater.bot.get_chat_member(chat_id=OFFICIAL_CHANNEL_ID, user_id=int(uid))
            if member.status in ["member", "administrator", "creator"]:
                updater.bot.send_message(chat_id=int(uid), text=text)
        except Exception as e:
            logging.warning(f"Failed to broadcast to {uid}: {e}")

# تابع هندل پیام‌های دریافتی از کانال
def forward_from_channel(update: Update, context: CallbackContext):
    message = update.channel_post
    if message.chat_id == OFFICIAL_CHANNEL_ID:
        broadcast_signal(message.text)

# هندل پیام سیگنال توسط ادمین
def admin_signal_text_handler(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if int(user_id) in ADMIN_IDS and context.user_data.get('await_signal'):
        context.user_data['await_signal'] = False
        broadcast_signal(update.message.text)
        update.message.reply_text("✅ سیگنال به کاربران ارسال شد.", reply_markup=MAIN_MENU)

# کامند پنل ادمین
def admin_panel(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if int(user_id) not in ADMIN_IDS:
        update.message.reply_text("⛔️ دسترسی ندارید.")
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 ارسال سیگنال", callback_data='admin_send_signal')]
    ])
    update.message.reply_text("🔧 پنل مدیریت:", reply_markup=kb)

# اجرای بات
TOKEN = '8133412407:AAER0aKfU0nbLmhUfn5bn-9vBhzaXPekYAY'
updater = Updater(token=TOKEN, use_context=True)
dp = updater.dispatcher

# هندلرها
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CallbackQueryHandler(button_handler))
dp.add_handler(MessageHandler(Filters.contact, contact_handler))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, name_handler))
dp.add_handler(ChannelPostHandler(forward_from_channel))

print("ربات آماده اجراست...")
updater.start_polling()
updater.idle()
