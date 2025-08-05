# -*- coding: utf-8 -*-
"""
ملف التكوين الرئيسي لبوت تيليجرام Hina-Bot
"""

import os
import logging

# إعدادات البوت الأساسية
BOT_TOKEN = "8086106444:AAG-BiKHdAcgEDYxp6264s4yGBhikK8rswc"
API_IMAGE_TOKEN = "4332bb825ca269dfa54503f393522710"
API_IMAGE_URL = "https://api.remove.bg/v1.0/removebg"  # رابط افتراضي، يمكن تغييره

# معلومات المالك
OWNER_ID = 7734153571  # معرف المالك الحقيقي
OWNER_USERNAME = "Alone1P"

# معلومات السيرفر
SERVER_HOST = "35.209.34.130"
SERVER_USER = "alone"
SERVER_PASSWORD = "Alone#001"

# إعدادات قاعدة البيانات
DATABASE_PATH = "hina_bot.db"

# إعدادات السجلات
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# إعدادات الأمان
MAX_MESSAGE_LENGTH = 4096
MAX_COMMANDS_PER_MINUTE = 30
SPAM_THRESHOLD = 5

# إعدادات الاختصارات
MAX_SHORTCUTS_PER_USER = 50
MAX_SHORTCUT_LENGTH = 20

# إعدادات التنبيهات
MAX_REMINDERS_PER_USER = 100

# إعدادات المجموعات
MAX_GROUPS_TO_MANAGE = 1000

# إعدادات القنوات
MAX_CHANNELS_TO_MANAGE = 100

# إعدادات النسخ الاحتياطي
BACKUP_INTERVAL_HOURS = 24
MAX_BACKUP_FILES = 7

# رسائل النظام
WELCOME_MESSAGE = "مرحباً بك في بوت Hina! اكتب /مساعدة لعرض الأوامر المتاحة."
HELP_MESSAGE = "قائمة الأوامر المتاحة:\n/مساعدة - عرض هذه الرسالة\n/ايدي - عرض معرفك\n/معلوماتي - عرض معلوماتك"

# إعدادات اللغة
DEFAULT_LANGUAGE = "ar"
SUPPORTED_LANGUAGES = ["ar", "en"]

# إعدادات الوقت
DEFAULT_TIMEZONE = "Asia/Riyadh"

# إعدادات الملفات
TEMP_DIR = "temp"
BACKUP_DIR = "backups"
LOGS_DIR = "logs"

# إنشاء المجلدات المطلوبة
for directory in [TEMP_DIR, BACKUP_DIR, LOGS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

