#!/bin/bash
# Agri Bridge - Script الإعداد الأولي

echo "=== إعداد نظام نظام البيع للمجابرة ==="
echo ""

# إنشاء بيئة افتراضية
python3 -m venv venv
source venv/bin/activate

# تثبيت المتطلبات
pip install --upgrade pip
pip install -r requirements.txt

# تطبيق الهجرة
python3 manage.py migrate

# إنشاء المستخدم الإداري
python3 manage.py shell -c "
from accounts.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@agribridge.com', 'admin123', full_name='المدير العام')
    print('تم إنشاء المستخدم الإداري بنجاح')
else:
    print('المستخدم الإداري موجود مسبقاً')
"

echo ""
echo "=== تم الإعداد بنجاح ==="
echo "بيانات تسجيل الدخول: admin / admin123"
echo ""
echo "تشغيل الخادم: python3 manage.py runserver 0.0.0.0:8000"
