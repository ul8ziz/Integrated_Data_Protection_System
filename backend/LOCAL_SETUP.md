# دليل الإعداد المحلي لـ MyDLP
# Local MyDLP Setup Guide

## نظرة عامة / Overview

هذا الدليل يشرح كيفية إعداد MyDLP للعمل محلياً على نفس الجهاز لمراقبة الإيميل والبيانات ومنع التسرب.

This guide explains how to set up MyDLP to run locally on the same machine for email and data monitoring and leakage prevention.

---

## المتطلبات / Requirements

### على Windows:
- Python 3.8+
- SQLite (مضمن مع Python)
- MyDLP CE (اختياري - النظام يعمل في وضع محاكي إذا لم يكن مثبتاً)

### على Linux:
- Python 3.8+
- Erlang/OTP 20+ (لـ MyDLP الفعلي)
- MySQL/MariaDB أو SQLite
- Build tools (gcc, make)

---

## خطوات الإعداد السريع / Quick Setup Steps

### 1. إعداد ملف البيئة / Setup Environment File

إنشاء ملف `.env` في مجلد `backend/`:

```bash
cd backend
```

إنشاء ملف `.env` مع المحتوى التالي:

```env
# Application Settings
APP_NAME=Athier Data Protection System
APP_VERSION=1.0.0
DEBUG=true
SECRET_KEY=change-me-to-secure-key-in-production-please

# Database (Local - SQLite for easy setup)
DATABASE_URL=sqlite:///./test.db

# Encryption
ENCRYPTION_KEY=change-me-to-32-byte-key-in-production-please

# Presidio
PRESIDIO_LANGUAGE=ar
PRESIDIO_SUPPORTED_ENTITIES=PERSON,PHONE_NUMBER,EMAIL_ADDRESS,CREDIT_CARD,ADDRESS,ORGANIZATION

# MyDLP - Localhost Configuration (Running on same machine)
MYDLP_ENABLED=true
MYDLP_API_URL=http://127.0.0.1:8080
MYDLP_API_KEY=

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 2. تهيئة قاعدة البيانات / Initialize Database

```bash
cd backend
python init_db.py
```

### 3. تشغيل النظام / Run the System

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 4. الوصول إلى الواجهة / Access the Interface

افتح المتصفح وانتقل إلى:
```
http://127.0.0.1:8000
```

---

## مراقبة الإيميل / Email Monitoring

### كيفية عملها / How It Works

1. **إرسال بريد للتحليل**:
   - استخدم زر "Test Email" في تبويب Monitoring
   - أو استخدم API مباشرة:

```bash
curl -X POST http://127.0.0.1:8000/api/monitoring/email \
  -H "Content-Type: application/json" \
  -d '{
    "from": "employee@company.com",
    "to": ["external@example.com"],
    "subject": "Customer Data",
    "body": "Phone: 123-456-7890, Email: test@example.com"
  }'
```

2. **النتيجة**:
   - النظام يحلل البريد باستخدام Presidio
   - يكتشف البيانات الحساسة (أرقام الهواتف، البريد الإلكتروني، إلخ)
   - يطبق السياسات النشطة
   - يمنع البريد إذا تم اكتشاف بيانات حساسة
   - ينشئ تنبيهات

### عرض إحصائيات البريد / View Email Statistics

```bash
curl http://127.0.0.1:8000/api/monitoring/email/statistics?days=7
```

### عرض سجلات البريد / View Email Logs

```bash
curl http://127.0.0.1:8000/api/monitoring/email/logs?limit=50
```

---

## منع تسريب البيانات / Data Leakage Prevention

### مراقبة حركة الشبكة / Network Traffic Monitoring

```bash
curl -X POST http://127.0.0.1:8000/api/monitoring/traffic \
  -H "Content-Type: application/json" \
  -d '{
    "source_ip": "127.0.0.1",
    "destination": "external.com",
    "content": "Data to check..."
  }'
```

### تحليل النصوص / Text Analysis

```bash
curl -X POST http://127.0.0.1:8000/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "My phone is 123-456-7890",
    "apply_policies": true
  }'
```

---

## الوضع المحاكي / Simulation Mode

إذا لم يكن MyDLP مثبتاً، النظام يعمل في **وضع محاكي**:

- ✅ جميع طلبات MyDLP تُحاكى محلياً
- ✅ التحليل يعمل باستخدام Presidio
- ✅ لا يوجد منع فعلي للبيانات (لكن التنبيهات تعمل)
- ✅ جميع الوظائف الأخرى تعمل بشكل طبيعي

---

## إعدادات المنافذ / Port Configuration

- **8000**: Athier FastAPI Application
- **8080**: MyDLP Web API (إذا كان مثبتاً)
- **10026**: MyDLP SMTP Proxy (إذا كان مثبتاً)
- **1344**: MyDLP ICAP Server (إذا كان مثبتاً)

---

## اختبار النظام / Testing the System

### اختبار شامل / Comprehensive Test

```bash
cd backend
python test_local_mydlp.py
```

هذا الاختبار يتحقق من:
- ✅ صحة Athier API
- ✅ حالة النظام
- ✅ تحليل النصوص
- ✅ مراقبة الإيميل
- ✅ إحصائيات البريد
- ✅ مراقبة الشبكة

---

## استكشاف الأخطاء / Troubleshooting

### MyDLP غير متاح / MyDLP Not Available

**المشكلة**: رسالة "MyDLP not running on localhost"

**الحل**: 
1. تعطيل MyDLP في `.env`:
   ```
   MYDLP_ENABLED=false
   ```
2. أو تثبيت وتشغيل MyDLP على المنفذ 8080

### خطأ في الاتصال / Connection Error

**المشكلة**: Cannot connect to Athier

**الحل**: 
1. تأكد من أن الخادم يعمل:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. تحقق من أن المنفذ 8000 غير مستخدم

### خطأ في قاعدة البيانات / Database Error

**الحل**: 
```bash
cd backend
python init_db.py
```

---

## ملاحظات مهمة / Important Notes

### الوضع المحلي / Local Mode

- في الوضع المحلي، النظام يراقب فقط نفس الجهاز
- للشبكات الكبيرة، استخدم سيرفر منفصل
- MyDLP في الوضع المحلي يعمل بشكل أسرع (timeout أقل)

### الأمان / Security

- ⚠️ **لا تستخدم** `SECRET_KEY` و `ENCRYPTION_KEY` الافتراضية في الإنتاج
- ⚠️ قم بتغييرها إلى قيم آمنة عشوائية
- ⚠️ لا تشارك ملف `.env` في المستودع

### الأداء / Performance

- SQLite مناسب للاختبار والتطوير
- للاستخدام في الإنتاج، استخدم PostgreSQL
- Presidio قد يستغرق وقتاً أطول عند أول استخدام (تحميل النماذج)

---

## الوثائق الإضافية / Additional Documentation

- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health
- **README.md**: راجع الملف الرئيسي للمشروع

---

## الدعم / Support

إذا واجهت مشاكل:
1. راجع سجلات الأخطاء في `backend/logs/app.log`
2. تحقق من حالة النظام في `/api/monitoring/status`
3. قم بتشغيل `test_local_mydlp.py` للتشخيص

---

**آخر تحديث**: 2024
