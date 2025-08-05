# -*- coding: utf-8 -*-
"""
نظام مراقبة البوت والتنبيهات
"""

import psutil
import time
import threading
import logging
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
from telegram import Bot
from database import db
import config

class SystemMonitor:
    def __init__(self, bot_token: str, owner_id: int):
        self.bot = Bot(token=bot_token)
        self.owner_id = owner_id
        self.monitoring_active = True
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 دقائق بين التنبيهات
        
        # عتبات التنبيه
        self.thresholds = {
            'cpu_usage': 80.0,      # %
            'memory_usage': 85.0,   # %
            'disk_usage': 90.0,     # %
            'response_time': 5.0,   # ثواني
            'error_rate': 10        # أخطاء في الدقيقة
        }
        
        self.start_monitoring()
    
    def get_system_stats(self) -> Dict:
        """الحصول على إحصائيات النظام"""
        try:
            # استخدام المعالج
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # استخدام الذاكرة
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # استخدام القرص
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # معلومات الشبكة
            network = psutil.net_io_counters()
            
            # عدد العمليات
            process_count = len(psutil.pids())
            
            # وقت التشغيل
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_usage': cpu_percent,
                'memory_usage': memory_percent,
                'memory_total': memory.total,
                'memory_available': memory.available,
                'disk_usage': disk_percent,
                'disk_total': disk.total,
                'disk_free': disk.free,
                'network_sent': network.bytes_sent,
                'network_recv': network.bytes_recv,
                'process_count': process_count,
                'uptime_seconds': uptime,
                'uptime_formatted': self.format_uptime(uptime)
            }
        except Exception as e:
            logging.error(f"خطأ في الحصول على إحصائيات النظام: {e}")
            return {}
    
    def format_uptime(self, seconds: float) -> str:
        """تنسيق وقت التشغيل"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{days}د {hours}س {minutes}ق"
    
    def check_bot_response_time(self) -> float:
        """فحص سرعة استجابة البوت"""
        try:
            start_time = time.time()
            # محاولة إرسال طلب بسيط للبوت
            response = requests.get(f"https://api.telegram.org/bot{config.BOT_TOKEN}/getMe", timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                return end_time - start_time
            else:
                return -1  # خطأ في الاستجابة
        except Exception as e:
            logging.error(f"خطأ في فحص سرعة الاستجابة: {e}")
            return -1
    
    def check_internet_connectivity(self) -> bool:
        """فحص الاتصال بالإنترنت"""
        try:
            response = requests.get("https://8.8.8.8", timeout=5)
            return True
        except:
            try:
                response = requests.get("https://1.1.1.1", timeout=5)
                return True
            except:
                return False
    
    def should_send_alert(self, alert_type: str) -> bool:
        """التحقق من إمكانية إرسال تنبيه"""
        current_time = time.time()
        last_alert = self.last_alert_time.get(alert_type, 0)
        
        if current_time - last_alert > self.alert_cooldown:
            self.last_alert_time[alert_type] = current_time
            return True
        return False
    
    async def send_alert(self, message: str, alert_type: str = "general"):
        """إرسال تنبيه للمالك"""
        try:
            if self.should_send_alert(alert_type):
                alert_message = f"🚨 **تنبيه النظام** 🚨\n\n{message}\n\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                await self.bot.send_message(chat_id=self.owner_id, text=alert_message, parse_mode='Markdown')
                logging.warning(f"تم إرسال تنبيه: {alert_type}")
        except Exception as e:
            logging.error(f"خطأ في إرسال التنبيه: {e}")
    
    def analyze_system_health(self, stats: Dict) -> List[str]:
        """تحليل صحة النظام"""
        alerts = []
        
        # فحص استخدام المعالج
        if stats.get('cpu_usage', 0) > self.thresholds['cpu_usage']:
            alerts.append(f"⚠️ استخدام المعالج مرتفع: {stats['cpu_usage']:.1f}%")
        
        # فحص استخدام الذاكرة
        if stats.get('memory_usage', 0) > self.thresholds['memory_usage']:
            alerts.append(f"⚠️ استخدام الذاكرة مرتفع: {stats['memory_usage']:.1f}%")
        
        # فحص استخدام القرص
        if stats.get('disk_usage', 0) > self.thresholds['disk_usage']:
            alerts.append(f"⚠️ استخدام القرص مرتفع: {stats['disk_usage']:.1f}%")
        
        return alerts
    
    def monitor_loop(self):
        """حلقة المراقبة الرئيسية"""
        while self.monitoring_active:
            try:
                # الحصول على إحصائيات النظام
                stats = self.get_system_stats()
                
                # فحص سرعة الاستجابة
                response_time = self.check_bot_response_time()
                stats['response_time'] = response_time
                
                # فحص الاتصال بالإنترنت
                internet_connected = self.check_internet_connectivity()
                stats['internet_connected'] = internet_connected
                
                # تحليل صحة النظام
                alerts = self.analyze_system_health(stats)
                
                # فحص سرعة الاستجابة
                if response_time > self.thresholds['response_time']:
                    alerts.append(f"⚠️ سرعة استجابة البوت بطيئة: {response_time:.2f} ثانية")
                elif response_time == -1:
                    alerts.append("❌ البوت لا يستجيب!")
                
                # فحص الاتصال بالإنترنت
                if not internet_connected:
                    alerts.append("❌ لا يوجد اتصال بالإنترنت!")
                
                # إرسال التنبيهات
                if alerts:
                    alert_message = "\n".join(alerts)
                    asyncio.create_task(self.send_alert(alert_message, "system_health"))
                
                # حفظ الإحصائيات في قاعدة البيانات
                db_stats = db.get_stats()
                db.log_system_stats(
                    cpu_usage=stats.get('cpu_usage', 0),
                    memory_usage=stats.get('memory_usage', 0),
                    disk_usage=stats.get('disk_usage', 0),
                    response_time=response_time,
                    active_users=db_stats.get('active_users', 0),
                    total_commands=db_stats.get('total_commands', 0),
                    errors_count=0  # سيتم تحديثه لاحقاً
                )
                
                # حفظ الإحصائيات في ملف JSON للمراقبة الويب
                self.save_stats_for_web(stats)
                
            except Exception as e:
                logging.error(f"خطأ في حلقة المراقبة: {e}")
                asyncio.create_task(self.send_alert(f"خطأ في نظام المراقبة: {str(e)}", "monitoring_error"))
            
            # انتظار 60 ثانية قبل الفحص التالي
            time.sleep(60)
    
    def save_stats_for_web(self, stats: Dict):
        """حفظ الإحصائيات لواجهة الويب"""
        try:
            web_stats = {
                'last_update': datetime.now().isoformat(),
                'system': stats,
                'bot': {
                    'status': 'online' if stats.get('response_time', -1) > 0 else 'offline',
                    'response_time': stats.get('response_time', -1),
                    'uptime': stats.get('uptime_formatted', 'غير معروف')
                },
                'database': db.get_stats()
            }
            
            with open('web_stats.json', 'w', encoding='utf-8') as f:
                json.dump(web_stats, f, ensure_ascii=False, indent=2, default=str)
                
        except Exception as e:
            logging.error(f"خطأ في حفظ إحصائيات الويب: {e}")
    
    def start_monitoring(self):
        """بدء نظام المراقبة"""
        monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()
        logging.info("تم بدء نظام المراقبة")
    
    def stop_monitoring(self):
        """إيقاف نظام المراقبة"""
        self.monitoring_active = False
        logging.info("تم إيقاف نظام المراقبة")
    
    async def send_daily_report(self):
        """إرسال تقرير يومي"""
        try:
            stats = db.get_stats()
            system_stats = self.get_system_stats()
            
            report = f"""📊 **التقرير اليومي للبوت**
            
🔢 **إحصائيات المستخدمين:**
• إجمالي المستخدمين: {stats.get('total_users', 0)}
• المستخدمون النشطون: {stats.get('active_users', 0)}
• إجمالي المجموعات: {stats.get('total_groups', 0)}
• إجمالي الأوامر: {stats.get('total_commands', 0)}

💻 **إحصائيات النظام:**
• استخدام المعالج: {system_stats.get('cpu_usage', 0):.1f}%
• استخدام الذاكرة: {system_stats.get('memory_usage', 0):.1f}%
• استخدام القرص: {system_stats.get('disk_usage', 0):.1f}%
• وقت التشغيل: {system_stats.get('uptime_formatted', 'غير معروف')}

📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            await self.bot.send_message(chat_id=self.owner_id, text=report, parse_mode='Markdown')
            logging.info("تم إرسال التقرير اليومي")
            
        except Exception as e:
            logging.error(f"خطأ في إرسال التقرير اليومي: {e}")

# إنشاء مثيل نظام المراقبة
monitor = SystemMonitor(config.BOT_TOKEN, config.OWNER_ID)

