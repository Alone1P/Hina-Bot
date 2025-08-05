# -*- coding: utf-8 -*-
"""
نظام تسجيل الدخول عبر تيليجرام للواجهة الويب
"""

import hashlib
import hmac
import time
import json
import secrets
from urllib.parse import parse_qs, unquote
from flask import session, request, redirect, url_for, flash
import config

class TelegramAuth:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    def verify_telegram_auth(self, auth_data):
        """التحقق من صحة بيانات تسجيل الدخول من تيليجرام"""
        try:
            # استخراج البيانات
            check_hash = auth_data.pop('hash', None)
            if not check_hash:
                return False
            
            # إنشاء سلسلة البيانات للتحقق
            data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(auth_data.items())])
            
            # حساب الهاش المتوقع
            secret_key = hashlib.sha256(self.bot_token.encode()).digest()
            calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
            
            # مقارنة الهاش
            if not hmac.compare_digest(calculated_hash, check_hash):
                return False
            
            # التحقق من انتهاء صلاحية البيانات (24 ساعة)
            auth_date = int(auth_data.get('auth_date', 0))
            if time.time() - auth_date > 86400:  # 24 ساعة
                return False
            
            return True
            
        except Exception as e:
            print(f"خطأ في التحقق من تسجيل الدخول: {e}")
            return False
    
    def create_login_url(self, redirect_url=None):
        """إنشاء رابط تسجيل الدخول عبر تيليجرام"""
        bot_username = "ImugarrBot"  # اسم البوت الحقيقي
        
        params = {
            'bot_id': self.bot_token.split(':')[0],
            'origin': request.host_url.rstrip('/'),
            'request_access': 'write'
        }
        
        if redirect_url:
            params['return_to'] = redirect_url
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"https://oauth.telegram.org/auth?{query_string}"
    
    def process_telegram_callback(self, callback_data):
        """معالجة رد تيليجرام بعد تسجيل الدخول"""
        try:
            # التحقق من صحة البيانات
            if not self.verify_telegram_auth(callback_data.copy()):
                return None, "فشل في التحقق من بيانات تسجيل الدخول"
            
            # استخراج بيانات المستخدم
            user_data = {
                'id': int(callback_data.get('id')),
                'first_name': callback_data.get('first_name', ''),
                'last_name': callback_data.get('last_name', ''),
                'username': callback_data.get('username', ''),
                'photo_url': callback_data.get('photo_url', ''),
                'auth_date': int(callback_data.get('auth_date'))
            }
            
            return user_data, None
            
        except Exception as e:
            return None, f"خطأ في معالجة بيانات تسجيل الدخول: {str(e)}"
    
    def create_session(self, user_data):
        """إنشاء جلسة للمستخدم"""
        session['user_id'] = user_data['id']
        session['user_data'] = user_data
        session['login_time'] = time.time()
        session['csrf_token'] = secrets.token_hex(16)
        session.permanent = True
    
    def is_authenticated(self):
        """التحقق من تسجيل دخول المستخدم"""
        if 'user_id' not in session:
            return False
        
        # التحقق من انتهاء صلاحية الجلسة (7 أيام)
        login_time = session.get('login_time', 0)
        if time.time() - login_time > 604800:  # 7 أيام
            session.clear()
            return False
        
        return True
    
    def get_current_user(self):
        """الحصول على بيانات المستخدم الحالي"""
        if not self.is_authenticated():
            return None
        return session.get('user_data')
    
    def is_owner(self):
        """التحقق من كون المستخدم مالك البوت"""
        user = self.get_current_user()
        return user and user['id'] == config.OWNER_ID
    
    def logout(self):
        """تسجيل خروج المستخدم"""
        session.clear()
    
    def require_auth(self, f):
        """ديكوريتر للصفحات التي تتطلب تسجيل دخول"""
        def decorated_function(*args, **kwargs):
            if not self.is_authenticated():
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    
    def require_owner(self, f):
        """ديكوريتر للصفحات التي تتطلب صلاحيات المالك"""
        def decorated_function(*args, **kwargs):
            if not self.is_authenticated():
                return redirect(url_for('login'))
            if not self.is_owner():
                flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function

# إنشاء مثيل نظام التحقق
telegram_auth = TelegramAuth(config.BOT_TOKEN)

