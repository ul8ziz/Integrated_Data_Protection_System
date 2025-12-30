# Secure - نظام حماية البيانات المتكامل
# Integrated Data Protection System

نظام متكامل لحماية البيانات الشخصية داخل المؤسسات يجمع بين Microsoft Presidio و MyDLP CE.

An integrated system for protecting personal data within organizations, combining Microsoft Presidio and MyDLP CE.

## المميزات / Features

- 🔍 **تحليل النصوص**: اكتشاف البيانات الحساسة تلقائياً باستخدام Presidio
- 📄 **فحص الملفات**: رفع وتحليل الملفات (PDF, DOCX, TXT, XLSX) لاكتشاف البيانات الحساسة
- 🛡️ **منع التسرب**: مراقبة ومنع تسرب البيانات باستخدام MyDLP CE
- 📊 **لوحة تحكم**: واجهة إدارة كاملة للسياسات والتنبيهات
- 🔐 **تشفير**: تشفير البيانات الحساسة قبل التخزين
- 📝 **سجلات**: تسجيل شامل لجميع الأحداث والأنشطة
- ⚖️ **الامتثال**: دعم معايير GDPR و HIPAA

## المتطلبات / Requirements

- Python 3.8+
- PostgreSQL 12+
- Git (لتحميل Presidio و MyDLP)

## التثبيت / Installation

### 1. استنساخ المستودعات / Clone Repositories

```bash
# Clone Presidio
git clone https://github.com/microsoft/presidio.git

# Clone MyDLP CE
git clone https://github.com/mydlp/mydlp.git
```

### 2. إعداد البيئة الافتراضية / Setup Virtual Environment

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

### 4. إعداد قاعدة البيانات / Database Setup

```bash
# إنشاء قاعدة البيانات في PostgreSQL
createdb Secure_db

# أو باستخدام psql
psql -U postgres
CREATE DATABASE Secure_db;
```

### 5. إعداد ملف البيئة / Environment Configuration

```bash
# نسخ ملف البيئة
cp .env.example .env

# تعديل القيم حسب الحاجة
# Edit .env file with your settings
```

### 6. تهيئة قاعدة البيانات / Initialize Database

```bash
cd backend
python -c "from app.database import init_db; init_db()"
```

## التشغيل / Running

### الطريقة السهلة (موصى بها) / Easy Way (Recommended)

**Windows:**
```bash
# الطريقة العادية (سيرفر فقط):
.\start.bat

# مع مراقبة MyDLP (نافذتان - سيرفر + مراقبة):
.\start_monitor.bat

# أو من PowerShell:
.\start.ps1
```

**ملاحظة:** `start_monitor.bat` يفتح نافذتين:
- نافذة السيرفر (تظهر سجلات uvicorn)
- نافذة مراقبة MyDLP (تعرض حالة MyDLP والتنبيهات في الوقت الفعلي)

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

الـ script سيقوم تلقائياً بـ:
- ✅ فحص البيئة الافتراضية (venv)
- ✅ إنشاء البيئة إذا لم تكن موجودة
- ✅ تثبيت جميع المكتبات المطلوبة
- ✅ تفعيل البيئة
- ✅ تشغيل السيرفر
- ✅ فتح المتصفح تلقائياً

### الطريقة اليدوية / Manual Way

```bash
# 1. إنشاء وتفعيل البيئة الافتراضية
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 2. تثبيت المكتبات
cd backend
pip install -r requirements.txt
pip install python-multipart  # مطلوب لرفع الملفات

# 3. تشغيل السيرفر
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

ثم افتح المتصفح على: `http://localhost:8000` أو `http://127.0.0.1:8000`

## الوثائق / Documentation

- API Documentation: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### تحليل النصوص / Text Analysis
- `POST /api/analyze/` - تحليل نص لاكتشاف البيانات الحساسة
- `POST /api/analyze/file` - رفع ملف وتحليله لاكتشاف البيانات الحساسة (يدعم PDF, DOCX, TXT, XLSX)
- `GET /api/analyze/entities` - الحصول على أنواع الكيانات المدعومة
- `GET /api/analyze/file/formats` - الحصول على أنواع الملفات المدعومة

### إدارة السياسات / Policy Management
- `GET /api/policies/` - الحصول على جميع السياسات
- `POST /api/policies/` - إنشاء سياسة جديدة
- `GET /api/policies/{id}` - الحصول على سياسة محددة
- `PUT /api/policies/{id}` - تحديث سياسة
- `DELETE /api/policies/{id}` - حذف سياسة

### التنبيهات / Alerts
- `GET /api/alerts/` - الحصول على جميع التنبيهات
- `GET /api/alerts/{id}` - الحصول على تنبيه محدد
- `PUT /api/alerts/{id}` - تحديث حالة التنبيه
- `GET /api/alerts/stats/summary` - إحصائيات التنبيهات

### المراقبة والتقارير / Monitoring & Reports
- `GET /api/monitoring/status` - حالة النظام
- `POST /api/monitoring/traffic` - مراقبة حركة البيانات
- `GET /api/monitoring/reports/summary` - تقرير ملخص
- `GET /api/monitoring/reports/logs` - تقرير السجلات

## هيكل المشروع / Project Structure

```
Secure/
├── presidio/          # Microsoft Presidio (cloned)
├── mydlp/             # MyDLP CE (cloned)
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── models/    # Database models
│   │   ├── services/  # Business logic
│   │   └── schemas/   # Pydantic schemas
│   └── requirements.txt
├── frontend/          # Frontend interface
├── tests/             # Tests
└── docs/              # Documentation
```

## التطوير / Development

### إضافة سياسة جديدة / Adding a New Policy

```python
# Example: Create a policy via API
POST /api/policies/
{
    "name": "Block Credit Cards",
    "entity_types": ["CREDIT_CARD"],
    "action": "block",
    "severity": "high",
    "enabled": true
}
```

### اختبار التحليل / Testing Analysis

```python
# Example: Analyze text
POST /api/analyze/
{
    "text": "My phone number is 123-456-7890",
    "apply_policies": true
}

# Example: Analyze uploaded file
POST /api/analyze/file
FormData:
  - file: (PDF, DOCX, TXT, or XLSX file)
  - apply_policies: true
  - source_user: "user@example.com" (optional)
```

### استخدام واجهة الويب / Using Web Interface

1. افتح المتصفح على `http://localhost:8000`
2. اختر تبويب "Text Analysis"
3. يمكنك:
   - **رفع ملف**: انقر على منطقة رفع الملفات أو اسحب الملف
   - **تحليل نص**: اكتب النص مباشرة في المربع
4. النتائج ستظهر تلقائياً مع تفاصيل البيانات الحساسة المكتشفة

## الترخيص / License

هذا المشروع مفتوح المصدر / This project is open source.

## المساهمة / Contributing

نرحب بالمساهمات! يرجى فتح issue أو pull request.

Contributions welcome! Please open an issue or pull request.

https://mydlp.com/
https://www.packetfence.org/about.html