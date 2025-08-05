# -*- coding: utf-8 -*-
"""
بوت تيليجرام Hina-Bot
بوت شامل مع جميع الميزات المطلوبة
"""

import logging
import asyncio
import time
import os
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, Bot, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, CallbackContext
)

# استيراد الوحدات المحلية
import config
from database import db
from monitoring import monitor
import web_monitor
from commands_menu import get_commands_menu

# إعداد نظام السجلات
logging.basicConfig(
    format=config.LOG_FORMAT,
    level=config.LOG_LEVEL,
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HinaBot:
    def __init__(self):
        self.application = None
        self.start_time = datetime.now()
        self.command_stats = {}
        self.user_last_command = {}
        self.shortcuts = {}
        
        # تحميل الاختصارات من قاعدة البيانات
        self.load_shortcuts()
        
        # بدء خادم الويب في خيط منفصل
        web_thread = threading.Thread(target=web_monitor.start_web_server, daemon=True)
        web_thread.start()
        
        logger.info("تم تهيئة بوت Hina بنجاح")
    
    def load_shortcuts(self):
        """تحميل الاختصارات من قاعدة البيانات"""
        try:
            # سيتم تنفيذ هذا لاحقاً عند إضافة جدول الاختصارات
            pass
        except Exception as e:
            logger.error(f"خطأ في تحميل الاختصارات: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر البدء"""
        user = update.effective_user
        
        # إضافة المستخدم إلى قاعدة البيانات
        db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code or 'ar'
        )
        
        welcome_text = f"""˼👋┊اهلـا بـك˹ ⟣⊰ 『 @{user.username or user.first_name} 』
˼🤖┊اسـمـي˹ ⟣⊰ 『 هـينـا ╎ 𝐇𝐢𝐧𝐚』

─ الـبوت يدعـم الـاوامـࢪ بالـانجـليـزي بـس

عـايز مسـاعدة ؟ ⤺
اكـتب 「.الاوامر ┆ .Menu」
قـبل كـل امـࢪ ↫ ⧼ . ⧽

˼📋┊الاقسـام˹ ⟣⊰
⧼ .الاوامر1 ⧽ ← اوامـر الـمالـك
⧼ .الاوامر2 ⧽ ← اوامـر الـمجـموعـات  
⧼ .الاوامر3 ⧽ ← اوامـر عـامـة
⧼ .الاوامر4 ⧽ ← الـتـرفـيـه والالـعـاب
⧼ .الاوامر5 ⧽ ← الادوات الـمسـاعـدة
⧼ .الاوامر6 ⧽ ← ادارة الـقـنـوات
⧼ .الاوامر7 ⧽ ← الاشـعـارات والـتـنـبـيـهـات
⧼ .الاوامر8 ⧽ ← جـمـيـع الاوامـر

˼👨‍💻┊الـمـطـوࢪ˹ ⟣⊰ 『 @{config.OWNER_USERNAME} 』"""
        
        # إرسال صورة مع الرسالة
        photo_url = "https://i.ibb.co/H5vwMW7/212aca21df414fb8c9bcca368f361eeb.jpg"
        
        try:
            await update.message.reply_photo(
                photo=photo_url,
                caption=welcome_text,
                parse_mode='HTML'
            )
        except:
            # في حالة فشل إرسال الصورة، أرسل النص فقط
            await update.message.reply_text(welcome_text, parse_mode='HTML')
        
        # تسجيل النشاط
        db.update_user_activity(user.id)
        await self.log_command_usage(update, context, 'start')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر المساعدة"""
        text, photo_url = get_commands_menu(0)
        
        try:
            await update.message.reply_photo(
                photo=photo_url,
                caption=text,
                parse_mode='HTML'
            )
        except:
            await update.message.reply_text(text, parse_mode='HTML')
        
        await self.log_command_usage(update, context, 'help')
    
    async def my_id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر عرض الايدي"""
        user = update.effective_user
        chat = update.effective_chat
        
        id_text = f"""
🆔 **معلومات الهوية**

👤 **معرفك:** `{user.id}`
📝 **اسم المستخدم:** @{user.username or 'غير محدد'}
📛 **الاسم:** {user.first_name} {user.last_name or ''}

💬 **معرف المحادثة:** `{chat.id}`
📋 **نوع المحادثة:** {chat.type}

⏰ **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(id_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'my_id')
    
    async def my_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر عرض معلومات المستخدم"""
        user = update.effective_user
        user_data = db.get_user(user.id)
        
        if not user_data:
            await update.message.reply_text("❌ لم يتم العثور على بياناتك في النظام.")
            return
        
        join_date = datetime.fromisoformat(user_data['join_date']).strftime('%Y-%m-%d')
        last_activity = datetime.fromisoformat(user_data['last_activity']).strftime('%Y-%m-%d %H:%M')
        
        info_text = f"""
👤 **معلوماتك الشخصية**

🆔 **المعرف:** `{user_data['user_id']}`
📝 **اسم المستخدم:** @{user_data['username'] or 'غير محدد'}
📛 **الاسم:** {user_data['first_name']} {user_data['last_name'] or ''}
🌐 **اللغة:** {user_data['language_code']}
🕐 **المنطقة الزمنية:** {user_data['timezone']}

📊 **الإحصائيات:**
• تاريخ الانضمام: {join_date}
• آخر نشاط: {last_activity}
• إجمالي الأوامر: {user_data['total_commands']}
• التحذيرات: {user_data['warnings']}

🔰 **الحالة:**
• مالك: {'✅' if user_data['is_owner'] else '❌'}
• مشرف: {'✅' if user_data['is_admin'] else '❌'}
• محظور: {'✅' if user_data['is_banned'] else '❌'}
        """
        
        await update.message.reply_text(info_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'my_info')
    
    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر فحص سرعة الاستجابة"""
        start_time = time.time()
        
        # إرسال رسالة مؤقتة
        message = await update.message.reply_text("🏓 جاري قياس سرعة الاستجابة...")
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # بالميلي ثانية
        
        # تحديث الرسالة
        ping_text = f"""
🏓 **نتائج فحص سرعة الاستجابة**

⚡ **سرعة الاستجابة:** {response_time:.2f} مللي ثانية
📊 **الحالة:** {'ممتاز' if response_time < 100 else 'جيد' if response_time < 500 else 'بطيء'}
🕐 **الوقت:** {datetime.now().strftime('%H:%M:%S')}
⏱️ **وقت تشغيل البوت:** {self.get_uptime()}
        """
        
        await message.edit_text(ping_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'ping', response_time/1000)
    
    async def server_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر معلومات السيرفر"""
        if not await self.is_owner(update.effective_user.id):
            await update.message.reply_text("❌ هذا الأمر متاح للمالك فقط.")
            return
        
        try:
            import psutil
            
            # معلومات النظام
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            server_text = f"""
🖥️ **معلومات السيرفر**

💻 **المعالج:**
• الاستخدام: {cpu_percent:.1f}%
• عدد النوى: {psutil.cpu_count()}

🧠 **الذاكرة:**
• الاستخدام: {memory.percent:.1f}%
• المستخدم: {self.format_bytes(memory.used)}
• المتاح: {self.format_bytes(memory.available)}
• الإجمالي: {self.format_bytes(memory.total)}

💾 **القرص الصلب:**
• الاستخدام: {disk.percent:.1f}%
• المستخدم: {self.format_bytes(disk.used)}
• المتاح: {self.format_bytes(disk.free)}
• الإجمالي: {self.format_bytes(disk.total)}

🌐 **الشبكة:**
• عنوان IP: {config.SERVER_HOST}
• المستخدم: {config.SERVER_USER}

⏰ **وقت التشغيل:** {self.get_uptime()}
            """
            
            await update.message.reply_text(server_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في الحصول على معلومات السيرفر: {str(e)}")
        
        await self.log_command_usage(update, context, 'server_info')
    
    async def bot_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر إحصائيات البوت"""
        if not await self.is_owner(update.effective_user.id):
            await update.message.reply_text("❌ هذا الأمر متاح للمالك فقط.")
            return
        
        try:
            stats = db.get_stats()
            
            stats_text = f"""
📊 **إحصائيات البوت الشاملة**

👥 **المستخدمون:**
• إجمالي المستخدمين: {stats.get('total_users', 0)}
• المستخدمون النشطون (24 ساعة): {stats.get('active_users', 0)}

💬 **المجموعات:**
• إجمالي المجموعات: {stats.get('total_groups', 0)}

⚡ **الأوامر:**
• إجمالي الأوامر المنفذة: {stats.get('total_commands', 0)}
• متوسط الأوامر يومياً: {stats.get('total_commands', 0) // max(1, (datetime.now() - self.start_time).days or 1)}

🗄️ **قاعدة البيانات:**
• حجم قاعدة البيانات: {self.format_bytes(stats.get('database_size', 0))}

⏰ **معلومات التشغيل:**
• وقت بدء التشغيل: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
• وقت التشغيل: {self.get_uptime()}
• الإصدار: 1.0.0

🔗 **الروابط:**
• واجهة المراقبة: http://{config.SERVER_HOST}:5000
• GitHub: https://github.com/{config.OWNER_USERNAME}/Hina-Bot
            """
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في الحصول على الإحصائيات: {str(e)}")
        
        await self.log_command_usage(update, context, 'bot_stats')
    
    async def dice_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر رمي النرد"""
        import random
        
        dice_result = random.randint(1, 6)
        dice_emoji = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅'][dice_result - 1]
        
        dice_text = f"""
🎲 **رمي النرد**

{dice_emoji} **النتيجة:** {dice_result}

{'🎉 رائع!' if dice_result == 6 else '👍 جيد!' if dice_result >= 4 else '😅 حظ أفضل المرة القادمة!'}
        """
        
        await update.message.reply_text(dice_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'dice')
    
    async def coin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر رمي العملة"""
        import random
        
        result = random.choice(['heads', 'tails'])
        result_ar = 'صورة' if result == 'heads' else 'كتابة'
        emoji = '🪙' if result == 'heads' else '📝'
        
        coin_text = f"""
🪙 **رمي العملة**

{emoji} **النتيجة:** {result_ar}

{random.choice(['🎯 توقع ممتاز!', '✨ حظ سعيد!', '🎲 مثير للاهتمام!'])}
        """
        
        await update.message.reply_text(coin_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'coin')
    
    async def joke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر النكت"""
        jokes = [
            "لماذا لا يمكن للدراجة أن تقف بمفردها؟ لأنها متعبة! 😄",
            "ما هو الشيء الذي يكتب ولا يقرأ؟ القلم! ✏️",
            "لماذا ذهب الموز إلى الطبيب؟ لأنه لم يكن يشعر بالقشرة! 🍌",
            "ما هو الشيء الذي له عين واحدة ولا يرى؟ الإبرة! 👁️",
            "لماذا لا تلعب الأسماك البوكر في الأدغال؟ لأن هناك الكثير من الفهود! 🐆",
            "ما هو الشيء الذي يجري ولا يمشي؟ الماء! 💧",
            "لماذا لا يمكن للدب أن يكون طباخاً؟ لأنه يأكل كل شيء نيئاً! 🐻",
            "ما هو الشيء الذي له أسنان ولا يعض؟ المشط! 🪮"
        ]
        
        import random
        joke = random.choice(jokes)
        
        joke_text = f"""
😂 **نكتة اليوم**

{joke}

😄 أتمنى أن تكون قد أعجبتك!
        """
        
        await update.message.reply_text(joke_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'joke')
    
    async def quote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر الاقتباسات"""
        quotes = [
            "النجاح هو الانتقال من فشل إلى فشل دون فقدان الحماس. - ونستون تشرشل",
            "الطريقة الوحيدة للقيام بعمل عظيم هي أن تحب ما تفعله. - ستيف جوبز",
            "الحياة هي ما يحدث لك بينما أنت مشغول بوضع خطط أخرى. - جون لينون",
            "كن التغيير الذي تريد أن تراه في العالم. - المهاتما غاندي",
            "المستقبل ينتمي لأولئك الذين يؤمنون بجمال أحلامهم. - إليانور روزفلت",
            "لا تحكم على كل يوم بالحصاد الذي تجنيه، بل بالبذور التي تزرعها. - روبرت لويس ستيفنسون",
            "الطموح هو الوقود الذي يحرك الإنسان نحو تحقيق أهدافه. - مجهول",
            "العقل الذي ينفتح على فكرة جديدة لن يعود أبداً إلى حجمه الأصلي. - ألبرت أينشتاين"
        ]
        
        import random
        quote = random.choice(quotes)
        
        quote_text = f"""
💭 **اقتباس ملهم**

"{quote}"

✨ دع هذا الاقتباس يلهمك اليوم!
        """
        
        await update.message.reply_text(quote_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'quote')
    
    async def time_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر الوقت الحالي"""
        import pytz
        
        # الحصول على المنطقة الزمنية للمستخدم
        user_data = db.get_user(update.effective_user.id)
        timezone_str = user_data.get('timezone', 'Asia/Riyadh') if user_data else 'Asia/Riyadh'
        
        try:
            timezone = pytz.timezone(timezone_str)
            current_time = datetime.now(timezone)
            
            time_text = f"""
🕐 **الوقت الحالي**

⏰ **الوقت:** {current_time.strftime('%H:%M:%S')}
📅 **التاريخ:** {current_time.strftime('%Y-%m-%d')}
🌍 **المنطقة الزمنية:** {timezone_str}
📆 **اليوم:** {current_time.strftime('%A')}

🌅 **معلومات إضافية:**
• الأسبوع: {current_time.isocalendar()[1]}
• اليوم في السنة: {current_time.timetuple().tm_yday}
            """
            
        except Exception as e:
            time_text = f"❌ خطأ في الحصول على الوقت: {str(e)}"
        
        await update.message.reply_text(time_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'time')
    
    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر الطقس"""
        if not context.args:
            await update.message.reply_text("❌ يرجى تحديد اسم المدينة.\nمثال: `/طقس الرياض`", parse_mode='Markdown')
            return
        
        city = ' '.join(context.args)
        
        # هنا يمكن إضافة API للطقس الحقيقي
        # للآن سنعرض رسالة تجريبية
        weather_text = f"""
🌤️ **حالة الطقس في {city}**

🌡️ **درجة الحرارة:** 25°C
💧 **الرطوبة:** 60%
💨 **سرعة الرياح:** 15 كم/ساعة
☁️ **الحالة:** غائم جزئياً

📊 **توقعات اليوم:**
• الصباح: 22°C ☀️
• الظهر: 28°C 🌤️
• المساء: 24°C 🌙

⚠️ **ملاحظة:** هذه بيانات تجريبية. سيتم ربط API الطقس الحقيقي قريباً.
        """
        
        await update.message.reply_text(weather_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'weather')
    
    async def translate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر الترجمة"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ يرجى تحديد اللغة والنص.\nمثال: `/ترجمة en مرحبا`", 
                parse_mode='Markdown'
            )
            return
        
        target_lang = context.args[0]
        text_to_translate = ' '.join(context.args[1:])
        
        try:
            from deep_translator import GoogleTranslator
            
            # ترجمة النص
            translator = GoogleTranslator(source='auto', target=target_lang)
            translated_text = translator.translate(text_to_translate)
            
            translate_text = f"""
🌐 **نتيجة الترجمة**

📝 **النص الأصلي:** {text_to_translate}
🎯 **اللغة الهدف:** {target_lang}
✅ **الترجمة:** {translated_text}
            """
            
        except Exception as e:
            translate_text = f"❌ خطأ في الترجمة: {str(e)}\n\n💡 تأكد من صحة رمز اللغة (مثل: en, fr, es)"
        
        await update.message.reply_text(translate_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'translate')
    
    async def calculator_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر الآلة الحاسبة"""
        if not context.args:
            await update.message.reply_text(
                "❌ يرجى إدخال العملية الحسابية.\nمثال: `/آلة_حاسبة 2+2`", 
                parse_mode='Markdown'
            )
            return
        
        expression = ' '.join(context.args)
        
        try:
            # تنظيف التعبير من الأحرف الخطيرة
            safe_chars = set('0123456789+-*/().= ')
            if not all(c in safe_chars for c in expression):
                raise ValueError("تعبير غير صالح")
            
            # حساب النتيجة
            result = eval(expression)
            
            calc_text = f"""
🧮 **نتيجة العملية الحسابية**

📝 **العملية:** `{expression}`
✅ **النتيجة:** `{result}`

💡 **أمثلة على العمليات المدعومة:**
• الجمع: 5 + 3
• الطرح: 10 - 4
• الضرب: 6 * 7
• القسمة: 15 / 3
• الأقواس: (2 + 3) * 4
            """
            
        except Exception as e:
            calc_text = f"❌ خطأ في العملية الحسابية: {str(e)}\n\n💡 تأكد من صحة التعبير الرياضي."
        
        await update.message.reply_text(calc_text, parse_mode='Markdown')
        await self.log_command_usage(update, context, 'calculator')
    
    # وظائف مساعدة
    async def is_owner(self, user_id: int) -> bool:
        """التحقق من كون المستخدم مالك البوت"""
        return user_id == config.OWNER_ID
    
    async def is_admin(self, user_id: int) -> bool:
        """التحقق من كون المستخدم مشرف"""
        user_data = db.get_user(user_id)
        return user_data and (user_data['is_admin'] or user_data['is_owner'])
    
    def get_uptime(self) -> str:
        """الحصول على وقت تشغيل البوت"""
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{days}د {hours}س {minutes}ق {seconds}ث"
    
    def format_bytes(self, bytes_value: int) -> str:
        """تنسيق البايتات"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    async def log_command_usage(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               command: str, response_time: float = 0):
        """تسجيل استخدام الأوامر"""
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id if update.effective_chat.type != 'private' else None
            
            # تحديث نشاط المستخدم
            db.update_user_activity(user_id)
            
            # تسجيل الأمر
            db.log_command(user_id, group_id, command, response_time)
            
            # تحديث إحصائيات الأوامر
            self.command_stats[command] = self.command_stats.get(command, 0) + 1
            
        except Exception as e:
            logger.error(f"خطأ في تسجيل استخدام الأمر: {e}")
    
    async def setup_commands(self):
        """إعداد قائمة أوامر البوت"""
        commands = [
            BotCommand("start", "بدء استخدام البوت"),
            BotCommand("help", "عرض المساعدة"),
            BotCommand("ping", "فحص سرعة الاستجابة"),
            BotCommand("time", "الوقت الحالي"),
            BotCommand("weather", "حالة الطقس"),
            BotCommand("dice", "رمي نرد"),
            BotCommand("coin", "رمي عملة"),
            BotCommand("joke", "نكتة عشوائية"),
            BotCommand("quote", "اقتباس ملهم"),
            BotCommand("translate", "ترجمة نص"),
            BotCommand("calc", "آلة حاسبة"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("تم إعداد قائمة أوامر البوت")
    
    async def commands_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, section: int):
        """معالج قوائم الأوامر"""
        text, photo_url = get_commands_menu(section)
        
        try:
            await update.message.reply_photo(
                photo=photo_url,
                caption=text,
                parse_mode='HTML'
            )
        except:
            await update.message.reply_text(text, parse_mode='HTML')
        
        await self.log_command_usage(update, context, f'menu_{section}')
    
    async def handle_arabic_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأوامر العربية"""
        text = update.message.text.strip()
        
        # قاموس الأوامر العربية
        arabic_commands = {
            # أوامر القوائم
            '.الاوامر': lambda u, c: self.commands_menu_handler(u, c, 0),
            '.Menu': lambda u, c: self.commands_menu_handler(u, c, 0),
            '.الاوامر1': lambda u, c: self.commands_menu_handler(u, c, 1),
            '.الاوامر2': lambda u, c: self.commands_menu_handler(u, c, 2),
            '.الاوامر3': lambda u, c: self.commands_menu_handler(u, c, 3),
            '.الاوامر4': lambda u, c: self.commands_menu_handler(u, c, 4),
            '.الاوامر5': lambda u, c: self.commands_menu_handler(u, c, 5),
            '.الاوامر6': lambda u, c: self.commands_menu_handler(u, c, 6),
            '.الاوامر7': lambda u, c: self.commands_menu_handler(u, c, 7),
            '.الاوامر8': lambda u, c: self.commands_menu_handler(u, c, 8),
            
            # الأوامر العادية
            '/مساعدة': self.help_command,
            'مساعدة': self.help_command,
            '.مساعدة': self.help_command,
            '/ايدي': self.my_id_command,
            'ايدي': self.my_id_command,
            '.ايدي': self.my_id_command,
            '/معلوماتي': self.my_info_command,
            'معلوماتي': self.my_info_command,
            '.معلوماتي': self.my_info_command,
            '/بنج': self.ping_command,
            'بنج': self.ping_command,
            '.بنج': self.ping_command,
            '/سيرفر': self.server_info_command,
            'سيرفر': self.server_info_command,
            '.سيرفر': self.server_info_command,
            '/احصائيات_البوت': self.bot_stats_command,
            'احصائيات البوت': self.bot_stats_command,
            '.احصائيات': self.bot_stats_command,
            '/نرد': self.dice_command,
            'نرد': self.dice_command,
            '.نرد': self.dice_command,
            '/عملة': self.coin_command,
            'عملة': self.coin_command,
            '.عملة': self.coin_command,
            '/نكتة': self.joke_command,
            'نكتة': self.joke_command,
            '.نكتة': self.joke_command,
            '/اقتباس': self.quote_command,
            'اقتباس': self.quote_command,
            '.اقتباس': self.quote_command,
            '/وقت': self.time_command,
            'وقت': self.time_command,
            '.وقت': self.time_command,
            '.الوقت': self.time_command,
            '/طقس': self.weather_command,
            '/ترجمة': self.translate_command,
            '/آلة_حاسبة': self.calculator_command,
            'حاسبة': self.calculator_command,
            '.حاسبة': self.calculator_command,
        }
        
        # البحث عن الأمر
        command_func = None
        if text in arabic_commands:
            command_func = arabic_commands[text]
        elif text.startswith('/طقس ') or text.startswith('طقس '):
            # معالجة خاصة لأمر الطقس مع المدينة
            city = text.replace('/طقس ', '').replace('طقس ', '')
            context.args = city.split()
            command_func = self.weather_command
        elif text.startswith('/ترجمة ') or text.startswith('ترجمة '):
            # معالجة خاصة لأمر الترجمة
            parts = text.replace('/ترجمة ', '').replace('ترجمة ', '').split(' ', 1)
            if len(parts) >= 2:
                context.args = [parts[0]] + parts[1].split()
                command_func = self.translate_command
        elif text.startswith('/آلة_حاسبة ') or text.startswith('حاسبة '):
            # معالجة خاصة للحاسبة
            expression = text.replace('/آلة_حاسبة ', '').replace('حاسبة ', '')
            context.args = [expression]
            command_func = self.calculator_command
        
        # تنفيذ الأمر إذا وُجد
        if command_func:
            await command_func(update, context)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأخطاء"""
        logger.error(f"خطأ في البوت: {context.error}")
        
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ حدث خطأ أثناء تنفيذ الأمر. تم تسجيل الخطأ وسيتم إصلاحه قريباً."
                )
            except Exception:
                pass
    
    def run(self):
        """تشغيل البوت"""
        # إنشاء التطبيق
        self.application = Application.builder().token(config.BOT_TOKEN).build()
        
        # إضافة معالجات الأوامر
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("ping", self.ping_command))
        self.application.add_handler(CommandHandler("server", self.server_info_command))
        self.application.add_handler(CommandHandler("stats", self.bot_stats_command))
        self.application.add_handler(CommandHandler("dice", self.dice_command))
        self.application.add_handler(CommandHandler("coin", self.coin_command))
        self.application.add_handler(CommandHandler("joke", self.joke_command))
        self.application.add_handler(CommandHandler("quote", self.quote_command))
        self.application.add_handler(CommandHandler("time", self.time_command))
        self.application.add_handler(CommandHandler("weather", self.weather_command))
        self.application.add_handler(CommandHandler("translate", self.translate_command))
        self.application.add_handler(CommandHandler("calc", self.calculator_command))
        
        # معالج الرسائل للأوامر العربية
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_arabic_commands))
        
        # إضافة معالج الأخطاء
        self.application.add_error_handler(self.error_handler)
        
        logger.info("🚀 تم بدء تشغيل بوت Hina")
        logger.info(f"🌐 واجهة المراقبة متاحة على: http://{config.SERVER_HOST}:5000")
        
        # تشغيل البوت
        self.application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    # إنشاء المجلدات المطلوبة
    for directory in ['logs', 'temp', 'backups']:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # تشغيل البوت
    bot = HinaBot()
    bot.run()

