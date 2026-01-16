# دليل سريع لتثبيت MongoDB
# MongoDB Quick Start Guide

## المشكلة / Problem

إذا رأيت هذا الخطأ:
```
No connection could be made because the target machine actively refused it
```

هذا يعني أن **MongoDB غير متصل** أو غير مثبت.

If you see this error:
```
No connection could be made because the target machine actively refused it
```

This means **MongoDB is not connected** or not installed.

---

## الحل السريع / Quick Solution

### على Windows / On Windows:

#### الخطوة 1: تثبيت MongoDB / Step 1: Install MongoDB

1. **تحميل MongoDB:**
   - افتح: https://www.mongodb.com/try/download/community
   - اختر: **Windows** → **MSI**
   - اضغط **Download**

2. **تثبيت MongoDB:**
   - شغّل ملف التثبيت الذي تم تحميله
   - اختر **Complete** installation
   - ✅ تأكد من تفعيل **Install MongoDB as a Service**
   - ✅ تأكد من تفعيل **Install MongoDB Compass** (واجهة رسومية)

#### الخطوة 2: تشغيل MongoDB / Step 2: Start MongoDB

**الطريقة 1: استخدام Services (الأسهل)**
1. اضغط `Win + R`
2. اكتب `services.msc` واضغط Enter
3. ابحث عن **MongoDB**
4. اضغط كليك يمين → **Start**

**الطريقة 2: استخدام Command Prompt**
```cmd
# إنشاء مجلد للبيانات
mkdir C:\data\db

# تشغيل MongoDB
"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe" --dbpath C:\data\db
```

#### الخطوة 3: التحقق من الاتصال / Step 3: Verify Connection

افتح Command Prompt جديد واكتب:
```cmd
mongosh
```

إذا ظهرت رسالة ترحيب، فالمشكلة حُلت! ✅

---

## التحقق من التثبيت / Verify Installation

### 1. فحص الخدمة / Check Service

```powershell
# في PowerShell
Get-Service -Name "MongoDB"
```

يجب أن يكون **Status = Running**

### 2. اختبار الاتصال / Test Connection

```cmd
mongosh
```

يجب أن ترى:
```
Current Mongosh Log ID: ...
Connecting to: mongodb://127.0.0.1:27017/?directConnection=true&serverSelectionTimeoutMS=2000
Using MongoDB: ...
Using Mongosh: ...
```

### 3. اختبار من Python / Test from Python

```python
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def test():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    result = await client.admin.command('ping')
    print("✅ MongoDB is connected!")
    client.close()

asyncio.run(test())
```

---

## بعد تثبيت MongoDB / After Installing MongoDB

1. **أعد تشغيل التطبيق:**
   ```powershell
   .\start.ps1
   ```

2. **تحقق من السجلات:**
   - يجب أن ترى: `MongoDB connection test successful`
   - يجب أن ترى: `MongoDB and Beanie initialized successfully`

3. **افتح المتصفح:**
   - http://127.0.0.1:8000/health
   - يجب أن ترى: `"mongodb": {"status": "connected"}`

---

## استكشاف الأخطاء / Troubleshooting

### الخطأ: "MongoDB service not found"
**الحل:** MongoDB غير مثبت. قم بتثبيته من الخطوة 1.

### الخطأ: "Access denied"
**الحل:** شغّل PowerShell أو Command Prompt كـ Administrator.

### الخطأ: "Port 27017 already in use"
**الحل:** MongoDB يعمل بالفعل! المشكلة في مكان آخر.

### الخطأ: "mongosh command not found"
**الحل:** أضف MongoDB إلى PATH:
1. افتح **Environment Variables**
2. أضف إلى PATH: `C:\Program Files\MongoDB\Server\7.0\bin`

---

## بديل: استخدام MongoDB Atlas (سحابي) / Alternative: MongoDB Atlas (Cloud)

إذا كنت لا تريد تثبيت MongoDB محلياً:

1. **سجّل في MongoDB Atlas:** https://www.mongodb.com/cloud/atlas
2. **أنشئ cluster مجاني**
3. **احصل على Connection String**
4. **حدّث ملف `.env`:**
   ```env
   MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/
   MONGODB_DB_NAME=Secure_db
   ```

---

## روابط مفيدة / Useful Links

- **MongoDB Download:** https://www.mongodb.com/try/download/community
- **MongoDB Documentation:** https://docs.mongodb.com/
- **MongoDB Atlas (Cloud):** https://www.mongodb.com/cloud/atlas

---

**آخر تحديث:** 2024
