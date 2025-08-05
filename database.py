# -*- coding: utf-8 -*-
"""
نظام قاعدة البيانات لبوت Hina-Bot
يدعم SQLite و JSON للنسخ الاحتياطي
"""

import sqlite3
import json
import os
import datetime
import logging
from typing import Dict, List, Any, Optional
import threading
import time

class DatabaseManager:
    def __init__(self, db_path: str = "hina_bot.db", json_backup_path: str = "users_backup.json"):
        self.db_path = db_path
        self.json_backup_path = json_backup_path
        self.lock = threading.Lock()
        self.init_database()
        self.start_auto_backup()
    
    def init_database(self):
        """إنشاء جداول قاعدة البيانات"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # جدول المستخدمين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT DEFAULT 'ar',
                    timezone TEXT DEFAULT 'Asia/Riyadh',
                    is_owner BOOLEAN DEFAULT FALSE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    warnings INTEGER DEFAULT 0,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_commands INTEGER DEFAULT 0,
                    preferences TEXT DEFAULT '{}',
                    shortcuts TEXT DEFAULT '{}'
                )
            ''')
            
            # جدول المجموعات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    group_id INTEGER PRIMARY KEY,
                    title TEXT,
                    type TEXT,
                    description TEXT,
                    invite_link TEXT,
                    member_count INTEGER DEFAULT 0,
                    admin_count INTEGER DEFAULT 0,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    settings TEXT DEFAULT '{}',
                    banned_words TEXT DEFAULT '[]',
                    auto_responses TEXT DEFAULT '{}'
                )
            ''')
            
            # جدول التنبيهات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    reminder_time TIMESTAMP,
                    is_recurring BOOLEAN DEFAULT FALSE,
                    recurrence_pattern TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # جدول الاختصارات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shortcuts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    group_id INTEGER,
                    shortcut TEXT,
                    full_command TEXT,
                    is_global BOOLEAN DEFAULT FALSE,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (group_id) REFERENCES groups (group_id)
                )
            ''')
            
            # جدول السجلات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    group_id INTEGER,
                    command TEXT,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time REAL,
                    status TEXT DEFAULT 'success'
                )
            ''')
            
            # جدول مراقبة النظام
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_monitoring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL,
                    response_time REAL,
                    active_users INTEGER,
                    total_commands INTEGER,
                    errors_count INTEGER
                )
            ''')
            
            conn.commit()
            logging.info("تم إنشاء قاعدة البيانات بنجاح")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                 last_name: str = None, language_code: str = 'ar') -> bool:
        """إضافة مستخدم جديد"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, language_code, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, language_code, datetime.datetime.now()))
                conn.commit()
                self.backup_to_json()
                return True
        except Exception as e:
            logging.error(f"خطأ في إضافة المستخدم: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """الحصول على بيانات مستخدم"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logging.error(f"خطأ في الحصول على بيانات المستخدم: {e}")
            return None
    
    def update_user_activity(self, user_id: int):
        """تحديث آخر نشاط للمستخدم"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET last_activity = ?, total_commands = total_commands + 1
                    WHERE user_id = ?
                ''', (datetime.datetime.now(), user_id))
                conn.commit()
        except Exception as e:
            logging.error(f"خطأ في تحديث نشاط المستخدم: {e}")
    
    def add_group(self, group_id: int, title: str, group_type: str = 'group') -> bool:
        """إضافة مجموعة جديدة"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO groups 
                    (group_id, title, type, last_activity)
                    VALUES (?, ?, ?, ?)
                ''', (group_id, title, group_type, datetime.datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"خطأ في إضافة المجموعة: {e}")
            return False
    
    def log_command(self, user_id: int, group_id: int, command: str, 
                   response_time: float, status: str = 'success'):
        """تسجيل استخدام الأوامر"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO logs 
                    (user_id, group_id, command, response_time, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, group_id, command, response_time, status))
                conn.commit()
        except Exception as e:
            logging.error(f"خطأ في تسجيل الأمر: {e}")
    
    def log_system_stats(self, cpu_usage: float, memory_usage: float, 
                        disk_usage: float, response_time: float, 
                        active_users: int, total_commands: int, errors_count: int):
        """تسجيل إحصائيات النظام"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_monitoring 
                    (cpu_usage, memory_usage, disk_usage, response_time, 
                     active_users, total_commands, errors_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (cpu_usage, memory_usage, disk_usage, response_time, 
                      active_users, total_commands, errors_count))
                conn.commit()
        except Exception as e:
            logging.error(f"خطأ في تسجيل إحصائيات النظام: {e}")
    
    def backup_to_json(self):
        """إنشاء نسخة احتياطية JSON"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # نسخ احتياطي للمستخدمين
                cursor.execute('SELECT * FROM users')
                users = [dict(row) for row in cursor.fetchall()]
                
                # نسخ احتياطي للمجموعات
                cursor.execute('SELECT * FROM groups')
                groups = [dict(row) for row in cursor.fetchall()]
                
                # نسخ احتياطي للتنبيهات
                cursor.execute('SELECT * FROM reminders WHERE is_active = 1')
                reminders = [dict(row) for row in cursor.fetchall()]
                
                backup_data = {
                    'backup_date': datetime.datetime.now().isoformat(),
                    'users': users,
                    'groups': groups,
                    'reminders': reminders,
                    'total_users': len(users),
                    'total_groups': len(groups),
                    'total_reminders': len(reminders)
                }
                
                with open(self.json_backup_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
                
                logging.info(f"تم إنشاء نسخة احتياطية JSON: {self.json_backup_path}")
                
        except Exception as e:
            logging.error(f"خطأ في إنشاء النسخة الاحتياطية JSON: {e}")
    
    def restore_from_json(self, json_file_path: str = None) -> bool:
        """استعادة البيانات من ملف JSON"""
        try:
            file_path = json_file_path or self.json_backup_path
            
            if not os.path.exists(file_path):
                logging.error(f"ملف النسخة الاحتياطية غير موجود: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # استعادة المستخدمين
                for user in backup_data.get('users', []):
                    cursor.execute('''
                        INSERT OR REPLACE INTO users 
                        (user_id, username, first_name, last_name, language_code, 
                         timezone, is_owner, is_admin, is_banned, ban_reason, 
                         warnings, join_date, last_activity, total_commands, 
                         preferences, shortcuts)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (user.get('user_id'), user.get('username'), 
                          user.get('first_name'), user.get('last_name'),
                          user.get('language_code', 'ar'), user.get('timezone', 'Asia/Riyadh'),
                          user.get('is_owner', False), user.get('is_admin', False),
                          user.get('is_banned', False), user.get('ban_reason'),
                          user.get('warnings', 0), user.get('join_date'),
                          user.get('last_activity'), user.get('total_commands', 0),
                          user.get('preferences', '{}'), user.get('shortcuts', '{}')))
                
                conn.commit()
                logging.info("تم استعادة البيانات من JSON بنجاح")
                return True
                
        except Exception as e:
            logging.error(f"خطأ في استعادة البيانات من JSON: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """الحصول على إحصائيات عامة"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # عدد المستخدمين
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                
                # عدد المستخدمين النشطين (آخر 24 ساعة)
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE last_activity > datetime('now', '-1 day')
                ''')
                active_users = cursor.fetchone()[0]
                
                # عدد المجموعات
                cursor.execute('SELECT COUNT(*) FROM groups')
                total_groups = cursor.fetchone()[0]
                
                # إجمالي الأوامر
                cursor.execute('SELECT SUM(total_commands) FROM users')
                total_commands = cursor.fetchone()[0] or 0
                
                # آخر إحصائيات النظام
                cursor.execute('''
                    SELECT * FROM system_monitoring 
                    ORDER BY timestamp DESC LIMIT 1
                ''')
                last_stats = cursor.fetchone()
                
                return {
                    'total_users': total_users,
                    'active_users': active_users,
                    'total_groups': total_groups,
                    'total_commands': total_commands,
                    'last_system_stats': last_stats,
                    'database_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                }
                
        except Exception as e:
            logging.error(f"خطأ في الحصول على الإحصائيات: {e}")
            return {}
    
    def start_auto_backup(self):
        """بدء النسخ الاحتياطي التلقائي"""
        def backup_worker():
            while True:
                time.sleep(3600)  # كل ساعة
                self.backup_to_json()
        
        backup_thread = threading.Thread(target=backup_worker, daemon=True)
        backup_thread.start()
        logging.info("تم بدء النسخ الاحتياطي التلقائي")

# إنشاء مثيل قاعدة البيانات
db = DatabaseManager()

