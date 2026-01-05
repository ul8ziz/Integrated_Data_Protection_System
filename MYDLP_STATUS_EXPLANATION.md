# شرح حالة MyDLP / MyDLP Status Explanation

## المشكلة / Problem
MyDLP يظهر كـ "Disabled" في صفحة System Status.

## السبب / Reason
MyDLP يتم تعطيله تلقائياً إذا:
1. متغير البيئة `MYDLP_ENABLED` غير موجود أو قيمته `false`
2. خدمة MyDLP غير متاحة أو غير مثبتة

## الحل / Solution

### الطريقة 1: تفعيل MyDLP عبر متغير البيئة
أضف أو عدّل في ملف `.env` في مجلد `backend/`:

```env
MYDLP_ENABLED=true
MYDLP_API_URL=http://localhost:8080
MYDLP_API_KEY=your-api-key-here
```

### الطريقة 2: التحقق من الإعدادات الحالية
افتح ملف `backend/app/config.py` وتحقق من:
- القيمة الافتراضية: `MYDLP_ENABLED: bool = os.getenv("MYDLP_ENABLED", "true").lower() == "true"`
- إذا كانت القيمة الافتراضية `"true"`، فـ MyDLP يجب أن يكون مفعّل افتراضياً

### الطريقة 3: إعادة تشغيل الخادم
بعد تعديل الإعدادات، أعد تشغيل خادم FastAPI:
```bash
cd backend
python -m uvicorn app.main:app --reload
```

## ملاحظات / Notes
- MyDLP هو نظام اختياري لمراقبة فقدان البيانات
- إذا لم يكن MyDLP مثبتاً، يمكن استخدام النظام بدون MyDLP (Presidio فقط)
- في وضع التطوير، يمكن تعطيل MyDLP لتسهيل الاختبار

## التحقق من الحالة / Check Status
افتح Developer Tools (F12) → Console وابحث عن:
- `MyDLP service initialized` = مفعّل
- `MyDLP service is disabled` = معطّل

