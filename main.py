import os
import json
import time
import asyncio
import re
from datetime import datetime, timedelta
from collections import defaultdict, deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
import logging

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from environment variable
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

# Admin user IDs
ADMIN_IDS = [int(os.environ.get('ADMIN_ID', '0'))]
ADMIN_IDS = [aid for aid in ADMIN_IDS if aid != 0]

# File paths for persistent storage
DATA_FILE = 'user_data.json'
CONTENT_FILE = 'content_data.json'
BLACKLIST_FILE = 'blacklist.json'
ADMIN_LOGS_FILE = 'admin_logs.json'
BACKUP_DIR = 'backups'

# Create backup directory if it doesn't exist
os.makedirs(BACKUP_DIR, exist_ok=True)

# Default category limits
CATEGORY_LIMITS = {
    'photos': 2,
    'india_pakistan': 3,
    'files': 1,
    'links': 1,
    'candid': 2,
    'cctv': 2,
    'english': 2,
    'cppz': 2,
    'gay': 2,
    'dark': 2,
    'lesbo': 2
}

# Videos per tap for each category
VIDEOS_PER_TAP = {
    'candid': 10,
    'cctv': 10,
    'english': 13,
    'cppz': 15,
    'gay': 10,
    'dark': 2,
    'lesbo': 13
}

# Category display names
CATEGORY_NAMES = {
    'photos': '📸 Photos',
    'india_pakistan': '🇮🇳🇵🇰 India & Pakistan',
    'files': '📁 Files',
    'links': '🔗 Links',
    'candid': '🎥 Candid',
    'cctv': '📹 CCTV',
    'english': '🇬🇧 English',
    'cppz': '🎞️ Cppz',
    'gay': '🏳️‍🌈 Gay',
    'dark': '🌑 Dark',
    'lesbo': '👩‍❤️‍👩 Lesbo'
}

# Category emojis for buttons
CATEGORY_EMOJIS = {
    'photos': '📸',
    'india_pakistan': '🇮🇳🇵🇰',
    'files': '📁',
    'links': '🔗',
    'candid': '🎥',
    'cctv': '📹',
    'english': '🇬🇧',
    'cppz': '🎞️',
    'gay': '🏳️‍🌈',
    'dark': '🌑',
    'lesbo': '👩‍❤️‍👩'
}

class ProtectionSystem:
    """Enterprise-level protection system"""
    
    def __init__(self):
        # Anti-spam
        self.user_message_count = defaultdict(lambda: deque(maxlen=60))
        self.user_warnings = defaultdict(int)
        self.user_temporary_bans = {}
        self.user_restrictions = {}
        
        # Anti-flood
        self.user_last_message = defaultdict(float)
        self.user_flood_count = defaultdict(int)
        
        # Rate limiting
        self.user_rate_limits = defaultdict(lambda: deque(maxlen=10))
        
        # Duplicate media detection
        self.recent_media = defaultdict(lambda: deque(maxlen=20))
        
        # Suspicious user tracking
        self.suspicious_users = defaultdict(int)
        
        # Admin whitelist
        self.admin_whitelist = set(ADMIN_IDS)
        
        # Blacklist
        self.blacklist = set()
        self.load_blacklist()
        
        # Protection settings
        self.WARNING_THRESHOLD = 5
        self.FLOOD_THRESHOLD = 10
        self.RATE_LIMIT = 3
        self.MAX_WARNINGS = 3
        
        # Ban durations (in hours)
        self.BAN_DURATIONS = {
            1: 24,
            2: 48,
            3: 168
        }
        
        # Restricted keywords
        self.restricted_keywords = [
            'spam', 'scam', 'hack', 'crack', 'cheat',
            'illegal', 'drug', 'porn', 'gambling',
            'casino', 'phishing', 'malware'
        ]
        
        self.load_restricted_keywords()
        
        # Admin logs
        self.admin_logs = []
        self.load_admin_logs()
        
        # Protection status
        self.protection_active = True
    
    def load_blacklist(self):
        try:
            if os.path.exists(BLACKLIST_FILE):
                with open(BLACKLIST_FILE, 'r') as f:
                    data = json.load(f)
                    self.blacklist = set(data.get('blacklist', []))
        except Exception as e:
            logger.error(f"Error loading blacklist: {e}")
    
    def save_blacklist(self):
        try:
            with open(BLACKLIST_FILE, 'w') as f:
                json.dump({'blacklist': list(self.blacklist)}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving blacklist: {e}")
    
    def load_restricted_keywords(self):
        try:
            if os.path.exists('restricted_keywords.json'):
                with open('restricted_keywords.json', 'r') as f:
                    data = json.load(f)
                    self.restricted_keywords = data.get('keywords', [])
        except Exception as e:
            logger.error(f"Error loading restricted keywords: {e}")
    
    def load_admin_logs(self):
        try:
            if os.path.exists(ADMIN_LOGS_FILE):
                with open(ADMIN_LOGS_FILE, 'r') as f:
                    self.admin_logs = json.load(f)
        except Exception as e:
            logger.error(f"Error loading admin logs: {e}")
    
    def save_admin_logs(self):
        try:
            if len(self.admin_logs) > 1000:
                self.admin_logs = self.admin_logs[-1000:]
            with open(ADMIN_LOGS_FILE, 'w') as f:
                json.dump(self.admin_logs, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving admin logs: {e}")
    
    def is_admin(self, user_id):
        return user_id in self.admin_whitelist
    
    def is_blacklisted(self, user_id):
        return user_id in self.blacklist
    
    def check_anti_spam(self, user_id):
        if self.is_admin(user_id) or self.is_blacklisted(user_id):
            return True
        
        now = time.time()
        message_times = self.user_message_count[user_id]
        message_times.append(now)
        
        recent_messages = [t for t in message_times if now - t <= 60]
        
        if len(recent_messages) > self.WARNING_THRESHOLD:
            self.user_warnings[user_id] += 1
            
            if self.user_warnings[user_id] >= self.MAX_WARNINGS:
                ban_level = min(self.user_warnings[user_id] - self.MAX_WARNINGS + 1, 3)
                ban_hours = self.BAN_DURATIONS.get(ban_level, 24)
                self.user_temporary_bans[user_id] = now + (ban_hours * 3600)
                
                self.log_admin_action(
                    f"🚨 Auto-ban applied to user {user_id} for spam. Duration: {ban_hours} hours."
                )
                return False
        
        return True
    
    def check_anti_flood(self, user_id):
        if self.is_admin(user_id) or self.is_blacklisted(user_id):
            return True
        
        now = time.time()
        
        if user_id in self.user_temporary_bans:
            if now < self.user_temporary_bans[user_id]:
                return False
            else:
                del self.user_temporary_bans[user_id]
        
        last_msg = self.user_last_message.get(user_id, 0)
        time_diff = now - last_msg
        
        if time_diff < 0.5:
            self.user_flood_count[user_id] += 1
            if self.user_flood_count[user_id] > self.FLOOD_THRESHOLD:
                self.log_admin_action(f"🚨 Flood detected from user {user_id}")
                return False
        else:
            self.user_flood_count[user_id] = max(0, self.user_flood_count[user_id] - 1)
        
        self.user_last_message[user_id] = now
        return True
    
    def check_rate_limit(self, user_id):
        if self.is_admin(user_id) or self.is_blacklisted(user_id):
            return True
        
        now = time.time()
        requests = self.user_rate_limits[user_id]
        requests.append(now)
        
        recent_requests = [t for t in requests if now - t <= 1]
        
        if len(recent_requests) > self.RATE_LIMIT:
            return False
        
        return True
    
    def check_keyword_filter(self, text):
        if not text:
            return True
        
        text_lower = text.lower()
        for keyword in self.restricted_keywords:
            if keyword in text_lower:
                return False
        return True
    
    def check_duplicate_media(self, user_id, media_id):
        if self.is_admin(user_id):
            return True
        
        recent = self.recent_media[user_id]
        if media_id in recent:
            return False
        
        recent.append(media_id)
        return True
    
    def check_raid_protection(self, user_ids):
        if len(user_ids) > 10:
            return False
        return True
    
    def check_abuse_detection(self, user_id, action_type):
        if self.is_admin(user_id):
            return True
        
        self.suspicious_users[user_id] += 1
        
        if self.suspicious_users[user_id] > 50:
            self.log_admin_action(f"⚠️ Suspicious user detected: {user_id}")
            return False
        
        return True
    
    def log_admin_action(self, action):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action
        }
        self.admin_logs.append(log_entry)
        self.save_admin_logs()
        logger.info(f"Admin log: {action}")
    
    def backup_data(self):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{BACKUP_DIR}/backup_{timestamp}.json"
            
            backup_data = {
                'user_data': data_manager.user_data,
                'content_data': data_manager.content_data,
                'blacklist': list(self.blacklist),
                'admin_logs': self.admin_logs[-1000:],
                'timestamp': timestamp
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            backups = sorted(os.listdir(BACKUP_DIR))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    os.remove(os.path.join(BACKUP_DIR, old_backup))
            
            logger.info(f"Backup created: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False

class UserDataManager:
    def __init__(self):
        self.user_data = {}
        self.content_data = {}
        self.load_data()
        self.protection = ProtectionSystem()
        self.last_backup = time.time()
        self.message_schedule = {}
    
    def load_data(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    self.user_data = json.load(f)
            else:
                self.user_data = {}
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
            self.user_data = {}
        
        try:
            if os.path.exists(CONTENT_FILE):
                with open(CONTENT_FILE, 'r') as f:
                    self.content_data = json.load(f)
            else:
                self.content_data = {}
        except Exception as e:
            logger.error(f"Error loading content data: {e}")
            self.content_data = {}
    
    def save_data(self):
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.user_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
        
        try:
            with open(CONTENT_FILE, 'w') as f:
                json.dump(self.content_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving content data: {e}")
        
        if time.time() - self.last_backup > 3600:
            self.protection.backup_data()
            self.last_backup = time.time()
    
    def get_user(self, user_id):
        user_id = str(user_id)
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'taps': {cat: 0 for cat in CATEGORY_LIMITS.keys()},
                'last_reset': datetime.now().isoformat(),
                'extra_access': {cat: 0 for cat in CATEGORY_LIMITS.keys()},
                'joined_date': datetime.now().isoformat(),
                'total_requests': 0,
                'last_request': None
            }
        return self.user_data[user_id]
    
    def reset_daily_limits(self, user_id):
        user_id = str(user_id)
        if user_id in self.user_data:
            now = datetime.now()
            last_reset = datetime.fromisoformat(self.user_data[user_id]['last_reset'])
            
            if (now - last_reset).total_seconds() >= 86400:
                self.user_data[user_id]['taps'] = {cat: 0 for cat in CATEGORY_LIMITS.keys()}
                self.user_data[user_id]['last_reset'] = now.isoformat()
                self.save_data()
                return True
        return False
    
    def get_remaining_taps(self, user_id, category):
        user_id = str(user_id)
        self.reset_daily_limits(user_id)
        user = self.get_user(user_id)
        
        used = user['taps'].get(category, 0)
        limit = CATEGORY_LIMITS.get(category, 2)
        extra = user['extra_access'].get(category, 0)
        
        return max(0, limit + extra - used)
    
    def can_tap(self, user_id, category):
        user_id = str(user_id)
        self.reset_daily_limits(user_id)
        return self.get_remaining_taps(user_id, category) > 0
    
    def use_tap(self, user_id, category):
        user_id = str(user_id)
        if self.can_tap(user_id, category):
            user = self.get_user(user_id)
            user['taps'][category] = user['taps'].get(category, 0) + 1
            user['total_requests'] = user.get('total_requests', 0) + 1
            user['last_request'] = datetime.now().isoformat()
            self.save_data()
            return True
        return False
    
    def add_extra_access(self, user_id, category, count):
        user_id = str(user_id)
        user = self.get_user(user_id)
        user['extra_access'][category] = user['extra_access'].get(category, 0) + count
        self.save_data()
        return True
    
    def get_videos(self, category):
        return self.content_data.get(category, [])
    
    def add_video(self, category, video_id):
        if category not in self.content_data:
            self.content_data[category] = []
        self.content_data[category].append(video_id)
        self.save_data()
        return True
    
    def remove_video(self, category, index):
        if category in self.content_data and 0 <= index < len(self.content_data[category]):
            self.content_data[category].pop(index)
            self.save_data()
            return True
        return False
    
    def schedule_message_deletion(self, message_id, chat_id, delete_after=86400):
        deletion_time = time.time() + delete_after
        self.message_schedule[message_id] = {
            'chat_id': chat_id,
            'deletion_time': deletion_time,
            'message_id': message_id
        }
        return True

# Initialize data manager
data_manager = UserDataManager()

# Rate limiting
user_last_command = {}

def rate_limit_check(user_id, cooldown=2):
    if data_manager.protection.is_admin(user_id):
        return True
    
    now = time.time()
    if user_id in user_last_command:
        if now - user_last_command[user_id] < cooldown:
            return False
    user_last_command[user_id] = now
    return True

# Anti-spam protection
user_spam_count = {}
spam_block_time = {}

def anti_spam_check(user_id):
    if data_manager.protection.is_admin(user_id):
        return True
    
    now = time.time()
    
    if user_id in spam_block_time:
        if now - spam_block_time[user_id] < 300:
            return False
        else:
            del spam_block_time[user_id]
    
    if user_id not in user_spam_count:
        user_spam_count[user_id] = []
    
    user_spam_count[user_id] = [t for t in user_spam_count[user_id] if now - t < 60]
    
    if len(user_spam_count[user_id]) >= 10:
        spam_block_time[user_id] = now
        user_spam_count[user_id] = []
        data_manager.protection.log_admin_action(f"🚨 Spam block applied to user {user_id}")
        return False
    
    user_spam_count[user_id].append(now)
    return True

def check_protection(user_id, text=None, media_id=None):
    if data_manager.protection.is_admin(user_id):
        return True
    
    if data_manager.protection.is_blacklisted(user_id):
        return False
    
    if not data_manager.protection.check_anti_spam(user_id):
        return False
    
    if not data_manager.protection.check_anti_flood(user_id):
        return False
    
    if not data_manager.protection.check_rate_limit(user_id):
        return False
    
    if text and not data_manager.protection.check_keyword_filter(text):
        data_manager.protection.log_admin_action(f"⚠️ Keyword filter triggered by user {user_id}")
        return False
    
    if media_id and not data_manager.protection.check_duplicate_media(user_id, media_id):
        return False
    
    if not data_manager.protection.check_abuse_detection(user_id, 'request'):
        return False
    
    return True

async def auto_delete_messages(context: ContextTypes.DEFAULT_TYPE):
    try:
        current_time = time.time()
        to_delete = []
        
        for msg_id, data in data_manager.message_schedule.items():
            if current_time >= data['deletion_time']:
                try:
                    await context.bot.delete_message(
                        chat_id=data['chat_id'],
                        message_id=data['message_id']
                    )
                    to_delete.append(msg_id)
                except Exception as e:
                    logger.error(f"Error deleting message {msg_id}: {e}")
                    to_delete.append(msg_id)
        
        for msg_id in to_delete:
            del data_manager.message_schedule[msg_id]
            
    except Exception as e:
        logger.error(f"Error in auto_delete_messages: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when /start is issued."""
    user = update.effective_user
    user_id = user.id
    
    if not check_protection(user_id):
        await update.message.reply_text("⚠️ Your request has been blocked due to protection measures.")
        return
    
    if not anti_spam_check(user_id):
        await update.message.reply_text("⚠️ You have been temporarily blocked due to spam. Please try again later.")
        return
    
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_contact = f"https://t.me/{admin_username}" if admin_username != 'admin' else "https://t.me/your_admin_username"
    
    welcome_text = f"""
👋 Welcome {user.first_name}!

I am your content management bot. Access various categories with daily limits.

📊 **Your Daily Access:**

"""
    
    for category in CATEGORY_LIMITS.keys():
        remaining = data_manager.get_remaining_taps(user_id, category)
        name = CATEGORY_NAMES.get(category, category)
        welcome_text += f"{name}: {remaining} remaining\n"
    
    welcome_text += f"""
⏰ All limits reset automatically every 24 hours.

📌 **Important Information:**
• All content is auto-deleted after 24 hours
• For more taps, contact Admin: {admin_contact}
• Admin can grant you free extra taps

ℹ️ Powered by @{admin_username}
"""
    
    keyboard = [
    [InlineKeyboardButton("📸 Photos", callback_data='category_photos')],
    [InlineKeyboardButton("🇮🇳🇵🇰 India & Pakistan", callback_data='category_india_pakistan')],
    [InlineKeyboardButton("📁 Files", callback_data='category_files')],
    [InlineKeyboardButton("🔗 Links", callback_data='category_links')],
    [InlineKeyboardButton("🎥 Candid", callback_data='category_candid')],
    [InlineKeyboardButton("📹 CCTV", callback_data='category_cctv')],
    [InlineKeyboardButton("🇬🇧 English", callback_data='category_english')],
    [InlineKeyboardButton("🎞️ Cppz", callback_data='category_cppz')],
    [InlineKeyboardButton("🏳️‍🌈 Gay", callback_data='category_gay')],
    [InlineKeyboardButton("🌑 Dark", callback_data='category_dark')],
    [InlineKeyboardButton("👩‍❤️‍👩 Lesbo", callback_data='category_lesbo')],
    [InlineKeyboardButton("📊 Daily Access", callback_data='check_access')],
    [InlineKeyboardButton("📩 Contact Admin", url=admin_contact)]
    ]
