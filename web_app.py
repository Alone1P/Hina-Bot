# -*- coding: utf-8 -*-
"""
التطبيق الويب الرئيسي لبوت Hina مع نظام تسجيل الدخول
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
import json
import os
from datetime import datetime, timedelta
import threading
import time
from database import db
from web_auth import telegram_auth
import config

app = Flask(__name__)
app.secret_key = config.BOT_TOKEN  # استخدام توكن البوت كمفتاح سري
app.permanent_session_lifetime = timedelta(days=7)

def load_web_stats():
    """تحميل إحصائيات الويب"""
    try:
        if os.path.exists('web_stats.json'):
            with open('web_stats.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"خطأ في تحميل إحصائيات الويب: {e}")
    
    return {
        'last_update': datetime.now().isoformat(),
        'system': {},
        'bot': {'status': 'unknown'},
        'database': {}
    }

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    if telegram_auth.is_authenticated():
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login')
def login():
    """صفحة تسجيل الدخول"""
    if telegram_auth.is_authenticated():
        return redirect(url_for('dashboard'))
    
    login_url = telegram_auth.create_login_url(redirect_url=url_for('auth_callback', _external=True))
    return render_template('login.html', login_url=login_url)

@app.route('/auth/callback')
def auth_callback():
    """معالجة رد تيليجرام بعد تسجيل الدخول"""
    # الحصول على بيانات تسجيل الدخول من الاستعلام
    auth_data = {}
    for key in ['id', 'first_name', 'last_name', 'username', 'photo_url', 'auth_date', 'hash']:
        if key in request.args:
            auth_data[key] = request.args.get(key)
    
    # معالجة بيانات تسجيل الدخول
    user_data, error = telegram_auth.process_telegram_callback(auth_data)
    
    if error:
        flash(f'خطأ في تسجيل الدخول: {error}', 'error')
        return redirect(url_for('login'))
    
    # إنشاء جلسة للمستخدم
    telegram_auth.create_session(user_data)
    
    # إضافة/تحديث المستخدم في قاعدة البيانات
    db.add_user(
        user_id=user_data['id'],
        username=user_data['username'],
        first_name=user_data['first_name'],
        last_name=user_data['last_name']
    )
    
    flash('تم تسجيل الدخول بنجاح!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    """تسجيل الخروج"""
    telegram_auth.logout()
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@telegram_auth.require_auth
def dashboard():
    """لوحة التحكم الرئيسية"""
    user = telegram_auth.get_current_user()
    user_data = db.get_user(user['id'])
    stats = load_web_stats()
    
    # إحصائيات المستخدم
    user_stats = {
        'total_commands': user_data.get('total_commands', 0) if user_data else 0,
        'join_date': user_data.get('join_date') if user_data else None,
        'last_activity': user_data.get('last_activity') if user_data else None,
        'warnings': user_data.get('warnings', 0) if user_data else 0
    }
    
    return render_template('dashboard.html', 
                         user=user, 
                         user_stats=user_stats,
                         system_stats=stats,
                         is_owner=telegram_auth.is_owner())

@app.route('/profile')
@telegram_auth.require_auth
def profile():
    """صفحة الملف الشخصي"""
    user = telegram_auth.get_current_user()
    user_data = db.get_user(user['id'])
    
    return render_template('profile.html', user=user, user_data=user_data)

@app.route('/admin')
@telegram_auth.require_owner
def admin():
    """لوحة إدارة البوت (للمالك فقط)"""
    stats = db.get_stats()
    system_stats = load_web_stats()
    
    return render_template('admin.html', 
                         stats=stats, 
                         system_stats=system_stats)

@app.route('/monitor')
def monitor():
    """صفحة مراقبة البوت العامة"""
    stats = load_web_stats()
    return render_template('monitor.html', stats=stats)

# API Routes
@app.route('/api/stats')
def api_stats():
    """API للحصول على الإحصائيات"""
    stats = load_web_stats()
    return jsonify(stats)

@app.route('/api/user/stats')
@telegram_auth.require_auth
def api_user_stats():
    """API لإحصائيات المستخدم"""
    user = telegram_auth.get_current_user()
    user_data = db.get_user(user['id'])
    
    if not user_data:
        return jsonify({'error': 'المستخدم غير موجود'}), 404
    
    return jsonify({
        'user_id': user_data['user_id'],
        'total_commands': user_data['total_commands'],
        'join_date': user_data['join_date'],
        'last_activity': user_data['last_activity'],
        'warnings': user_data['warnings'],
        'is_admin': user_data['is_admin'],
        'is_owner': user_data['is_owner']
    })

@app.route('/api/health')
def api_health():
    """فحص صحة البوت"""
    stats = load_web_stats()
    
    health_status = {
        'status': 'healthy',
        'checks': {
            'bot_online': stats['bot']['status'] == 'online',
            'response_time_ok': stats['bot'].get('response_time', -1) < 5.0,
            'cpu_ok': stats['system'].get('cpu_usage', 0) < 80,
            'memory_ok': stats['system'].get('memory_usage', 0) < 85,
            'disk_ok': stats['system'].get('disk_usage', 0) < 90
        }
    }
    
    # تحديد الحالة العامة
    if not all(health_status['checks'].values()):
        health_status['status'] = 'warning'
    
    if not health_status['checks']['bot_online']:
        health_status['status'] = 'critical'
    
    return jsonify(health_status)

@app.route('/api/admin/users')
@telegram_auth.require_owner
def api_admin_users():
    """API لقائمة المستخدمين (للمالك فقط)"""
    try:
        # هنا يمكن إضافة استعلام لجلب قائمة المستخدمين
        # للآن سنعيد بيانات تجريبية
        return jsonify({
            'users': [],
            'total': 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_templates():
    """إنشاء قوالب HTML"""
    template_dir = 'templates'
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    # قالب الصفحة الرئيسية
    index_html = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بوت Hina - الصفحة الرئيسية</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .hero-section { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 100px 0; }
        .feature-card { transition: transform 0.3s ease; }
        .feature-card:hover { transform: translateY(-5px); }
    </style>
</head>
<body>
    <div class="hero-section text-center">
        <div class="container">
            <h1 class="display-4 mb-4">🤖 مرحباً بك في بوت Hina</h1>
            <p class="lead mb-4">بوت تيليجرام شامل مع مئات الأوامر المفيدة</p>
            <a href="{{ url_for('login') }}" class="btn btn-light btn-lg">تسجيل الدخول عبر تيليجرام</a>
        </div>
    </div>
    
    <div class="container my-5">
        <div class="row">
            <div class="col-md-4 mb-4">
                <div class="card feature-card h-100">
                    <div class="card-body text-center">
                        <h5 class="card-title">🎮 الترفيه والألعاب</h5>
                        <p class="card-text">ألعاب ممتعة ونكت وأنشطة ترفيهية</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4 mb-4">
                <div class="card feature-card h-100">
                    <div class="card-body text-center">
                        <h5 class="card-title">🛠️ أدوات مساعدة</h5>
                        <p class="card-text">ترجمة، طقس، حاسبة، وأدوات مفيدة</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4 mb-4">
                <div class="card feature-card h-100">
                    <div class="card-body text-center">
                        <h5 class="card-title">👥 إدارة المجموعات</h5>
                        <p class="card-text">أدوات شاملة لإدارة مجموعات تيليجرام</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <footer class="bg-dark text-white text-center py-3">
        <p>&copy; 2025 بوت Hina - تم التطوير بواسطة @Alone1P</p>
    </footer>
</body>
</html>'''
    
    # قالب تسجيل الدخول
    login_html = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول - بوت Hina</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .login-card { max-width: 400px; margin: 100px auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card login-card">
            <div class="card-body text-center p-5">
                <h2 class="mb-4">🤖 تسجيل الدخول</h2>
                <p class="text-muted mb-4">سجل دخولك باستخدام حساب تيليجرام للوصول إلى لوحة التحكم الشخصية</p>
                
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                <script async src="https://telegram.org/js/telegram-widget.js?22" 
                        data-telegram-login="HinaBotBot" 
                        data-size="large" 
                        data-auth-url="{{ url_for('auth_callback', _external=True) }}" 
                        data-request-access="write">
                </script>
                
                <div class="mt-4">
                    <a href="{{ url_for('index') }}" class="btn btn-outline-secondary">العودة للرئيسية</a>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>'''
    
    # حفظ القوالب
    with open(os.path.join(template_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    with open(os.path.join(template_dir, 'login.html'), 'w', encoding='utf-8') as f:
        f.write(login_html)

def start_web_app():
    """بدء التطبيق الويب"""
    create_templates()
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    start_web_app()

