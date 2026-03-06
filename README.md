# Secure - نظام حماية البيانات المتكامل
# Integrated Data Protection System

نظام متكامل لحماية البيانات الشخصية داخل المؤسسات يجمع بين Microsoft Presidio و MyDLP CE، مع نظام إدارة مستخدمين وصلاحيات متكامل.

An integrated system for protecting personal data within organizations, combining Microsoft Presidio and MyDLP CE, with a complete user management and permission system.

## المميزات / Features

- 🔍 **تحليل النصوص**: اكتشاف البيانات الحساسة تلقائياً باستخدام Presidio
- 📄 **فحص الملفات**: رفع وتحليل الملفات (PDF, DOCX, TXT, XLSX) لاكتشاف البيانات الحساسة
- 🛡️ **منع التسرب**: مراقبة ومنع تسرب البيانات باستخدام MyDLP CE
- 👥 **إدارة المستخدمين**: نظام متكامل لإدارة المستخدمين والصلاحيات (Admin/User)
- 🔐 **المصادقة**: تسجيل دخول آمن، إنشاء حسابات، وموافقة المدراء
- 📊 **لوحة تحكم**: واجهة إدارة كاملة للسياسات والتنبيهات والمستخدمين
- 📧 **مراقبة البريد**: محاكاة واختبار مراقبة البريد الإلكتروني
- 📝 **سجلات**: تسجيل شامل لجميع الأحداث والأنشطة
- 🕐 **وقت الخادم**: عرض التواريخ والأوقات بتنسيق موحد من منطقة زمنية الخادم (الأشعارات، السجلات، سجل العمليات، البريد) — إعداد TIMEZONE في .env
- ⚖️ **الامتثال**: دعم معايير GDPR و HIPAA

## المتطلبات / Requirements

- Python 3.8+
- PostgreSQL 12+ (أو SQLite للاختبار)
- Git

## التثبيت والتشغيل السريع / Quick Start

### الطريقة السهلة (Windows)

```bash
# انقر نقراً مزدوجاً على الملف أو من PowerShell:
.\start.bat

# أو للتشغيل مع مراقبة MyDLP:
.\start_monitor.bat
```

### الطريقة اليدوية / Manual Installation

1. **استنساخ المستودع / Clone Repository**
   ```bash
   git clone https://github.com/username/secure-dlp.git
   cd secure-dlp
   ```

2. **إعداد البيئة / Setup Environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **تثبيت التبعيات / Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   # تثبيت مكتبات المصادقة والملفات
   pip install python-multipart python-jose[cryptography] passlib[bcrypt] email-validator
   ```

4. **تهيئة قاعدة البيانات / Initialize Database**
   ```bash
   python init_db.py
   # سيتم إنشاء مستخدم admin افتراضي:
   # Username: admin
   # Password: admin123
   ```

5. **التشغيل / Run**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

## دليل المستخدم / User Guide

### 1. تسجيل الدخول / Login
- عند فتح النظام، ستظهر شاشة تسجيل الدخول
- **Admin**: الدخول بصلاحيات كاملة (إدارة المستخدمين والسياسات)
- **User**: الدخول بصلاحيات محدودة (فحص الملفات والنصوص)
- **إنشاء حساب**: يمكن للزوار إنشاء حساب جديد (يحتاج موافقة المدير)

### 2. فحص البيانات / Data Analysis
- **File Analysis**: رفع ملفات (PDF, Word, Excel) لفحصها
- **Text Analysis**: كتابة نص مباشرة للفحص السريع

### 3. إدارة المستخدمين (للمدراء فقط)
- عرض قائمة المستخدمين
- الموافقة على طلبات التسجيل الجديدة
- تفعيل/تعطيل الحسابات

### 4. إدارة السياسات (للمدراء فقط)
- إنشاء سياسات حماية جديدة
- تحديد أنواع البيانات المحظورة (Credit Cards, Phones, etc.)
- تحديد الإجراء (Block, Alert, Encrypt)

## API Endpoints

### المصادقة / Authentication
- `POST /api/auth/login` - تسجيل الدخول
- `POST /api/auth/register` - إنشاء حساب جديد

### المستخدمين / Users (Admin)
- `GET /api/users/` - عرض المستخدمين
- `GET /api/users/pending` - طلبات التسجيل المعلقة
- `POST /api/users/{id}/approve` - الموافقة على مستخدم

### التحليل / Analysis
- `POST /api/analyze/` - تحليل نص
- `POST /api/analyze/file` - تحليل ملف

### المراقبة / Monitoring
- `POST /api/monitoring/email` - فحص بريد إلكتروني
- `GET /api/monitoring/status` - حالة النظام

## التقنيات المستخدمة / Technologies

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Frontend**: HTML5, CSS3, JavaScript (Native)
- **AI/NLP**: Microsoft Presidio
- **Database**: PostgreSQL / SQLite
- **Security**: OAuth2, JWT, Bcrypt

## الترخيص / License

هذا المشروع مفتوح المصدر / This project is open source.

---

## استكشاف الأخطاء / Troubleshooting

- **عدم ظهور إشعارات المدير عند التثبيت على جهاز آخر:** راجع [استكشاف إشعارات المدير](docs/TROUBLESHOOTING_ALERTS.md) للتحقق من تسجيل الدخول كـ Admin، تشغيل MongoDB، ووجود سياسات مفعّلة.
