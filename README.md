# Athier - نظام حماية البيانات المتكامل
# Integrated Data Protection System

نظام متكامل لحماية البيانات الشخصية داخل المؤسسات يجمع بين Microsoft Presidio و MyDLP CE.

An integrated system for protecting personal data within organizations, combining Microsoft Presidio and MyDLP CE.

## المميزات / Features

- 🔍 **تحليل النصوص**: اكتشاف البيانات الحساسة تلقائياً باستخدام Presidio
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
createdb athier_db

# أو باستخدام psql
psql -U postgres
CREATE DATABASE athier_db;
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

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

ثم افتح المتصفح على: `http://localhost:8000`

## الوثائق / Documentation

- API Documentation: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### تحليل النصوص / Text Analysis
- `POST /api/analyze/` - تحليل نص لاكتشاف البيانات الحساسة
- `GET /api/analyze/entities` - الحصول على أنواع الكيانات المدعومة

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
athier/
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
```

## الترخيص / License

هذا المشروع مفتوح المصدر / This project is open source.

## المساهمة / Contributing

نرحب بالمساهمات! يرجى فتح issue أو pull request.

Contributions welcome! Please open an issue or pull request.

