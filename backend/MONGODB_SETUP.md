# دليل إعداد MongoDB
# MongoDB Setup Guide

## نظرة عامة / Overview

تم تحويل المشروع لاستخدام MongoDB بدلاً من PostgreSQL/SQLite. هذا الدليل يشرح كيفية إعداد MongoDB.

The project has been converted to use MongoDB instead of PostgreSQL/SQLite. This guide explains how to set up MongoDB.

---

## المتطلبات / Requirements

### تثبيت MongoDB / Install MongoDB

#### على Windows:
1. قم بتحميل MongoDB من: https://www.mongodb.com/try/download/community
2. قم بتثبيت MongoDB Community Server
3. تأكد من تشغيل خدمة MongoDB (MongoDB Service)

#### على Linux:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y mongodb

# أو استخدام MongoDB official repository
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org

# تشغيل MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

#### على macOS:
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

---

## إعداد ملف البيئة / Environment Setup

إنشاء ملف `.env` في مجلد `backend/`:

```env
# Application Settings
APP_NAME=Secure Data Protection System
APP_VERSION=1.0.0
DEBUG=true
SECRET_KEY=change-me-to-secure-key-in-production-please

# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=Secure_db

# Encryption
ENCRYPTION_KEY=change-me-to-32-byte-key-in-production-please

# Presidio
PRESIDIO_LANGUAGE=ar
PRESIDIO_SUPPORTED_ENTITIES=PERSON,PHONE_NUMBER,EMAIL_ADDRESS,CREDIT_CARD,ADDRESS,ORGANIZATION

# MyDLP
MYDLP_ENABLED=true
MYDLP_API_URL=http://127.0.0.1:8080
MYDLP_API_KEY=

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

---

## تثبيت المكتبات المطلوبة / Install Required Libraries

```bash
cd backend
pip install -r requirements.txt
```

المكتبات المطلوبة:
- `motor>=3.3.2` - Async MongoDB driver
- `beanie>=1.23.6` - ODM for MongoDB
- `pymongo>=4.6.1` - MongoDB driver

---

## تشغيل النظام / Run the System

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

عند بدء التشغيل، سيقوم النظام تلقائياً:
- الاتصال بـ MongoDB
- إنشاء المجموعات (Collections) المطلوبة
- إنشاء مستخدم admin افتراضي (username: admin, password: admin123)

---

## التحقق من الاتصال / Verify Connection

### 1. التحقق من حالة MongoDB:
```bash
# Windows
# افتح Services وابحث عن MongoDB

# Linux
sudo systemctl status mongod

# macOS
brew services list
```

### 2. الاتصال بـ MongoDB Shell:
```bash
mongosh
```

### 3. التحقق من قاعدة البيانات:
```javascript
use Secure_db
show collections
db.users.find()
```

---

## الفرق بين SQL و MongoDB / Differences from SQL

### 1. معرفات (IDs):
- **SQL**: أرقام صحيحة (1, 2, 3...)
- **MongoDB**: ObjectId (سلاسل نصية مثل "507f1f77bcf86cd799439011")

### 2. الاستعلامات (Queries):
- **SQL**: `db.query(User).filter(User.status == "active")`
- **MongoDB**: `await User.find(User.status == UserStatus.ACTIVE)`

### 3. الحفظ (Save):
- **SQL**: `db.add(user); db.commit()`
- **MongoDB**: `await user.insert()` أو `await user.save()`

---

## استكشاف الأخطاء / Troubleshooting

### خطأ: "Connection refused"
**الحل**: تأكد من أن MongoDB يعمل:
```bash
# Windows: افتح Services
# Linux: sudo systemctl start mongod
# macOS: brew services start mongodb-community
```

### خطأ: "Database not found"
**الحل**: هذا طبيعي. MongoDB ينشئ قاعدة البيانات تلقائياً عند أول استخدام.

### خطأ: "Module not found: beanie"
**الحل**: قم بتثبيت المكتبات:
```bash
pip install -r requirements.txt
```

---

## ملاحظات مهمة / Important Notes

1. **البيانات القديمة**: إذا كان لديك بيانات في SQLite/PostgreSQL، ستحتاج إلى نقلها يدوياً إلى MongoDB.

2. **الأمان**: في الإنتاج، استخدم:
   - كلمة مرور قوية لـ MongoDB
   - تشفير الاتصال (TLS/SSL)
   - المصادقة (Authentication)

3. **النسخ الاحتياطي**: قم بعمل نسخ احتياطية منتظمة لقاعدة البيانات:
```bash
mongodump --db Secure_db --out /backup/path
```

---

## الوثائق الإضافية / Additional Documentation

- **MongoDB Documentation**: https://docs.mongodb.com/
- **Beanie Documentation**: https://beanie-odm.dev/
- **Motor Documentation**: https://motor.readthedocs.io/

---

**آخر تحديث**: 2024
