#!/bin/bash

set -e

echo "🚀 بدء نشر Farmar Agir..."
echo "================================"

cd /home/administrator/farmar-agir

echo "📥 سحب آخر تحديثات Git..."
git pull origin main

echo "🔍 فحص Django..."
source venv/bin/activate
python manage.py check

echo "🗃️ إنشاء migrations..."
python manage.py makemigrations

echo "📦 تطبيق migrations..."
python manage.py migrate

echo "🎨 جمع الملفات الثابتة..."
python manage.py collectstatic --noinput

echo "🔄 إعادة تشغيل Gunicorn..."
sudo systemctl restart farmar_agir

echo "🌐 إعادة تحميل Nginx..."
sudo systemctl reload nginx

echo "================================"
echo "✅ تم النشر بنجاح!"
echo "🌍 https://alqissy-qat.dev313.site