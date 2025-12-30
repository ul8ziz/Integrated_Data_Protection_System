# دليل التثبيت والتشغيل
# Installation and Setup Guide

## المتطلبات الأساسية / Prerequisites

- Python 3.8 أو أحدث
- PostgreSQL 12 أو أحدث
- Git
- pip (مدير حزم Python)

## خطوات التثبيت / Installation Steps

### 1. استنساخ المستودعات / Clone Repositories

```bash
# استنساخ Presidio
git clone https://github.com/microsoft/presidio.git

# استنساخ MyDLP CE
git clone https://github.com/mydlp/mydlp.git
```

### 2. إعداد البيئة الافتراضية / Virtual Environment Setup

```bash
# إنشاء بيئة افتراضية
python -m venv venv

# تفعيل البيئة (Windows)
venv\Scripts\activate

# تفعيل البيئة (Linux/Mac)
source venv/bin/activate
```

### 3. تثبيت التبعيات / Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**ملاحظة**: قد تحتاج إلى تثبيت spacy models:

```bash
python -m spacy download xx_core_web_sm
python -m spacy download en_core_web_sm
```

### 4. إعداد قاعدة البيانات / Database Setup

#### إنشاء قاعدة البيانات:

```bash
# باستخدام psql
psql -U postgres
CREATE DATABASE Secure_db;
CREATE USER Secure_user WITH PASSWORD 'Secure_password';
GRANT ALL PRIVILEGES ON DATABASE Secure_db TO Secure_user;
```

#### أو باستخدام createdb:

```bash
createdb -U postgres Secure_db
```

### 5. إعداد ملف البيئة / Environment Configuration

```bash
# نسخ ملف البيئة
cp .env.example .env

# تعديل القيم في .env
# Edit .env file with your settings:
# - DATABASE_URL
# - ENCRYPTION_KEY (يجب أن يكون 32 بايت)
# - SECRET_KEY
# - إعدادات Presidio و MyDLP
```

### 6. تهيئة قاعدة البيانات / Initialize Database

```bash
cd backend
python init_db.py
```

أو باستخدام Alembic:

```bash
cd backend
alembic upgrade head
```

### 7. تشغيل التطبيق / Run Application

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. الوصول للتطبيق / Access Application

- الواجهة الرئيسية: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## استخدام Docker / Using Docker

### تشغيل باستخدام Docker Compose:

```bash
cd docker
docker-compose up -d
```

هذا سيقوم بـ:
- تشغيل PostgreSQL
- تشغيل تطبيق FastAPI
- إعداد الشبكة والبيئة

### إيقاف الخدمات:

```bash
docker-compose down
```

### عرض السجلات:

```bash
docker-compose logs -f backend
```

## التحقق من التثبيت / Verification

### 1. اختبار API:

```bash
# Health check
curl http://localhost:8000/health

# Get supported entities
curl http://localhost:8000/api/analyze/entities
```

### 2. اختبار التحليل:

```bash
curl -X POST http://localhost:8000/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "My phone number is 123-456-7890",
    "apply_policies": false
  }'
```

## استكشاف الأخطاء / Troubleshooting

### مشكلة: خطأ في الاتصال بقاعدة البيانات

**الحل**: تأكد من:
- PostgreSQL يعمل
- DATABASE_URL صحيح في .env
- المستخدم لديه الصلاحيات

### مشكلة: Presidio لا يعمل

**الحل**: 
```bash
pip install presidio-analyzer presidio-anonymizer
python -m spacy download xx_core_web_sm
```

### مشكلة: MyDLP غير متاح

**الحل**: يمكن تعطيل MyDLP في .env:
```
MYDLP_ENABLED=false
```

النظام سيعمل بدون MyDLP ولكن بدون ميزات منع التسرب.

## التطوير / Development

### تشغيل في وضع التطوير:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### تشغيل الاختبارات:

```bash
pytest tests/
```

### إنشاء migration جديد:

```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## الإنتاج / Production

للإنتاج، يجب:
1. تعطيل DEBUG في .env
2. استخدام SECRET_KEY قوي
3. استخدام ENCRYPTION_KEY قوي (32 بايت)
4. إعداد HTTPS
5. إعداد قاعدة بيانات محمية
6. إعداد backup منتظم

