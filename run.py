#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ملف تشغيل بوت Hina-Bot
"""

import sys
import os
import logging
import signal
import time
from datetime import datetime

# إضافة المجلد الحالي إلى مسار Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# استيراد البوت
from bot import HinaBot
import config

def setup_logging():
    """إعداد نظام السجلات"""
    # إنشاء مجلد السجلات إذا لم يكن موجوداً
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # إعداد تنسيق السجلات
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # تقليل مستوى سجلات المكتبات الخارجية
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)

def signal_handler(signum, frame):
    """معالج إشارات النظام"""
    print(f"\n🛑 تم استلام إشارة إيقاف ({signum})")
    print("🔄 جاري إيقاف البوت بأمان...")
    sys.exit(0)

def check_requirements():
    """فحص المتطلبات الأساسية"""
    required_modules = [
        'telegram',
        'psutil',
        'flask',
        'requests',
        'pytz'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print("❌ المكتبات التالية مفقودة:")
        for module in missing_modules:
            print(f"   - {module}")
        print("\n💡 قم بتثبيتها باستخدام:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def check_config():
    """فحص ملف التكوين"""
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ يرجى تحديث BOT_TOKEN في ملف config.py")
        return False
    
    if not config.OWNER_ID or config.OWNER_ID == 123456789:
        print("⚠️ تحذير: يرجى تحديث OWNER_ID في ملف config.py")
    
    return True

def create_directories():
    """إنشاء المجلدات المطلوبة"""
    directories = ['logs', 'temp', 'backups', 'templates']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 تم إنشاء مجلد: {directory}")

def print_startup_info():
    """طباعة معلومات البدء"""
    print("=" * 60)
    print("🤖 بوت Hina-Bot")
    print("=" * 60)
    print(f"📅 تاريخ البدء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 إصدار Python: {sys.version}")
    print(f"📂 مجلد العمل: {os.getcwd()}")
    print(f"🌐 واجهة المراقبة: http://{config.SERVER_HOST}:5000")
    print(f"👤 المطور: @{config.OWNER_USERNAME}")
    print("=" * 60)

def main():
    """الدالة الرئيسية"""
    # إعداد معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # إعداد السجلات
    setup_logging()
    
    # طباعة معلومات البدء
    print_startup_info()
    
    # فحص المتطلبات
    print("🔍 فحص المتطلبات...")
    if not check_requirements():
        sys.exit(1)
    
    # فحص التكوين
    print("⚙️ فحص التكوين...")
    if not check_config():
        sys.exit(1)
    
    # إنشاء المجلدات
    print("📁 إنشاء المجلدات...")
    create_directories()
    
    print("✅ جميع الفحوصات تمت بنجاح!")
    print("🚀 بدء تشغيل البوت...")
    
    try:
        # إنشاء وتشغيل البوت
        bot = HinaBot()
        bot.run()
        
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        logging.error(f"خطأ في تشغيل البوت: {e}", exc_info=True)
        sys.exit(1)
    finally:
        print("👋 تم إيقاف البوت")

if __name__ == '__main__':
    main()

