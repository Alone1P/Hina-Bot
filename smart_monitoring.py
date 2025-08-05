# -*- coding: utf-8 -*-
"""
نظام المراقبة الذكي لبوت Hina
يتضمن مراقبة البنج، تنبيهات الإغلاق، ونظام البث الذكي
"""

import asyncio
import json
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import config

logger = logging.getLogger(__name__)

class SmartMonitoring:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.start_time = time.time()
        self.ping_history = []
        self.restart_count_today = 0
        self.last_restart_date = datetime.now().date()
        self.broadcast_count_today = 0
        self.monitoring_active = True
        
        # إعدادات المراقبة
        self.ping_threshold_warning = 1000  # 1 ثانية
        self.ping_threshold_critical = 3000  # 3 ثواني
        self.memory_threshold = 90  # 90%
        self.cpu_threshold = 95  # 95%
        
        # تحميل البيانات المحفوظة
        self.load_monitoring_data()
        
    def load_monitoring_data(self):
        """تحميل بيانات المراقبة المحفوظة"""
        try:
            with open('monitoring_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            today = datetime.now().date().isoformat()
            if data.get('date') == today:
                self.restart_count_today = data.get('restart_count', 0)
                self.broadcast_count_today = data.get('broadcast_count', 0)
            else:
                # يوم جديد، إعادة تعيين العدادات
                self.restart_count_today = 0
                self.broadcast_count_today = 0
                
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("لا توجد بيانات مراقبة سابقة، بدء جديد")
    
    def save_monitoring_data(self):
        """حفظ بيانات المراقبة"""
        try:
            data = {
                'date': datetime.now().date().isoformat(),
                'restart_count': self.restart_count_today,
                'broadcast_count': self.broadcast_count_today,
                'last_save': datetime.now().isoformat()
            }
            
            with open('monitoring_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"خطأ في حفظ بيانات المراقبة: {e}")
    
    def get_uptime(self):
        """الحصول على مدة التشغيل"""
        uptime_seconds = time.time() - self.start_time
        
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        if days > 0:
            return f"{days} يوم، {hours} ساعة، {minutes} دقيقة"
        elif hours > 0:
            return f"{hours} ساعة، {minutes} دقيقة"
        else:
            return f"{minutes} دقيقة"
    
    async def measure_ping(self):
        """قياس البنج (زمن الاستجابة)"""
        try:
            start_time = time.time()
            
            # محاولة إرسال طلب بسيط للتحقق من الاستجابة
            await self.bot.application.bot.get_me()
            
            ping_time = (time.time() - start_time) * 1000  # بالمللي ثانية
            
            # إضافة للتاريخ
            self.ping_history.append({
                'time': datetime.now(),
                'ping': ping_time
            })
            
            # الاحتفاظ بآخر 100 قياس فقط
            if len(self.ping_history) > 100:
                self.ping_history.pop(0)
            
            return ping_time
            
        except Exception as e:
            logger.error(f"خطأ في قياس البنج: {e}")
            return 9999  # قيمة عالية تدل على مشكلة
    
    async def check_system_health(self):
        """فحص صحة النظام"""
        try:
            # فحص الذاكرة
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # فحص المعالج
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # فحص القرص
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # فحص البنج
            ping = await self.measure_ping()
            
            health_status = {
                'memory_percent': memory_percent,
                'cpu_percent': cpu_percent,
                'disk_percent': disk_percent,
                'ping': ping,
                'uptime': self.get_uptime(),
                'timestamp': datetime.now()
            }
            
            # تحديد مستوى الخطر
            if (memory_percent > self.memory_threshold or 
                cpu_percent > self.cpu_threshold or 
                ping > self.ping_threshold_critical):
                health_status['level'] = 'critical'
            elif ping > self.ping_threshold_warning:
                health_status['level'] = 'warning'
            else:
                health_status['level'] = 'good'
            
            return health_status
            
        except Exception as e:
            logger.error(f"خطأ في فحص صحة النظام: {e}")
            return {'level': 'error', 'error': str(e)}
    
    async def send_warning_notification(self, health_status):
        """إرسال تنبيه تحذيري"""
        try:
            warning_text = f"""
🚨 **تحذير من نظام المراقبة**

⚠️ **مستوى الخطر:** {health_status['level'].upper()}
⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}
🕐 **مدة التشغيل:** {health_status['uptime']}

📊 **حالة النظام:**
• الذاكرة: {health_status['memory_percent']:.1f}%
• المعالج: {health_status['cpu_percent']:.1f}%
• البنج: {health_status['ping']:.0f}ms

⚡ **الإجراء المطلوب:**
قد يحتاج البوت لإعادة تشغيل قريباً لضمان الأداء الأمثل.
            """
            
            # إرسال للمالك
            await self.bot.application.bot.send_message(
                chat_id=config.OWNER_ID,
                text=warning_text,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"خطأ في إرسال التنبيه: {e}")
    
    async def send_shutdown_notification(self, reason="غير محدد"):
        """إرسال تنبيه قبل الإغلاق"""
        try:
            shutdown_text = f"""
🔴 **تنبيه إغلاق البوت**

⏰ **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🕐 **مدة التشغيل:** {self.get_uptime()}
📊 **عدد إعادات التشغيل اليوم:** {self.restart_count_today}

🔍 **سبب الإغلاق:** {reason}

⚡ **ملاحظة:** سيتم إعادة تشغيل البوت تلقائياً إن أمكن.
            """
            
            # إرسال للمالك
            await self.bot.application.bot.send_message(
                chat_id=config.OWNER_ID,
                text=shutdown_text,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"خطأ في إرسال تنبيه الإغلاق: {e}")
    
    def calculate_broadcast_count(self):
        """حساب عدد البثات المطلوبة بناءً على عدد إعادات التشغيل"""
        if self.restart_count_today <= 3:
            return 1
        elif self.restart_count_today <= 6:
            return 2
        elif self.restart_count_today <= 10:
            return 3
        else:
            return min(4, self.restart_count_today // 4)  # حد أقصى 4 بثات
    
    async def send_startup_broadcast(self):
        """إرسال بث عند بدء التشغيل"""
        try:
            # تحديث عداد إعادة التشغيل
            today = datetime.now().date()
            if self.last_restart_date != today:
                self.restart_count_today = 0
                self.broadcast_count_today = 0
                self.last_restart_date = today
            
            self.restart_count_today += 1
            
            # حساب عدد البثات المطلوبة
            required_broadcasts = self.calculate_broadcast_count()
            
            # التحقق من الحاجة للبث
            if self.broadcast_count_today >= required_broadcasts:
                logger.info(f"تم تجاوز حد البثات اليومي ({required_broadcasts})")
                return
            
            self.broadcast_count_today += 1
            
            startup_text = f"""
✅ **البوت عاد للعمل!**

🚀 **حالة التشغيل:** نشط ويعمل بكفاءة
⏰ **وقت العودة:** {datetime.now().strftime('%H:%M:%S')}
📊 **إعادة التشغيل رقم:** {self.restart_count_today} اليوم
🔄 **البث رقم:** {self.broadcast_count_today} من {required_broadcasts}

🎯 **جاهز لاستقبال الأوامر!**
اكتب `.الاوامر` لعرض القائمة الرئيسية.

˼👨‍💻┊الـمـطـوࢪ˹ ⟣⊰ 『 @{config.OWNER_USERNAME} 』
            """
            
            # الحصول على قائمة المستخدمين والمجموعات من قاعدة البيانات
            from database import DatabaseManager
            db = DatabaseManager()
            
            # إرسال للمستخدمين النشطين
            active_users = db.get_active_users(days=7)  # المستخدمين النشطين في آخر 7 أيام
            
            sent_count = 0
            for user in active_users:
                try:
                    await self.bot.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=startup_text,
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                    
                    # تأخير بسيط لتجنب حدود التيليجرام
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.debug(f"فشل إرسال البث للمستخدم {user['user_id']}: {e}")
            
            # حفظ البيانات
            self.save_monitoring_data()
            
            logger.info(f"تم إرسال بث البدء إلى {sent_count} مستخدم")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال بث البدء: {e}")
    
    async def start_monitoring(self):
        """بدء نظام المراقبة"""
        logger.info("🔍 بدء نظام المراقبة الذكي")
        
        # إرسال بث البدء
        await self.send_startup_broadcast()
        
        while self.monitoring_active:
            try:
                # فحص صحة النظام
                health_status = await self.check_system_health()
                
                # إرسال تنبيهات حسب الحاجة
                if health_status.get('level') == 'critical':
                    await self.send_warning_notification(health_status)
                    logger.warning("⚠️ حالة النظام حرجة!")
                    
                elif health_status.get('level') == 'warning':
                    logger.warning("⚠️ تحذير: ارتفاع في البنج")
                
                # انتظار دقيقة واحدة قبل الفحص التالي
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"خطأ في حلقة المراقبة: {e}")
                await asyncio.sleep(60)
    
    async def stop_monitoring(self, reason="إيقاف يدوي"):
        """إيقاف نظام المراقبة"""
        self.monitoring_active = False
        await self.send_shutdown_notification(reason)
        self.save_monitoring_data()
        logger.info("🔴 تم إيقاف نظام المراقبة")
    
    def get_monitoring_stats(self):
        """الحصول على إحصائيات المراقبة"""
        if not self.ping_history:
            return "لا توجد بيانات مراقبة متاحة"
        
        recent_pings = [p['ping'] for p in self.ping_history[-10:]]
        avg_ping = sum(recent_pings) / len(recent_pings)
        
        stats_text = f"""
📊 **إحصائيات المراقبة**

⏱️ **متوسط البنج:** {avg_ping:.0f}ms
🔄 **إعادات التشغيل اليوم:** {self.restart_count_today}
📢 **البثات المرسلة اليوم:** {self.broadcast_count_today}
🕐 **مدة التشغيل الحالية:** {self.get_uptime()}

📈 **آخر 5 قياسات بنج:**
        """
        
        for ping_data in self.ping_history[-5:]:
            stats_text += f"• {ping_data['time'].strftime('%H:%M')} - {ping_data['ping']:.0f}ms\n"
        
        return stats_text

