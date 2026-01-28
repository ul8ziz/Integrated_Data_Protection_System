"""
سيناريو اختبار لنظام حماية البيانات
Test Scenario for Data Protection System

السيناريو:
- الجهاز 1 (السيرفر الرئيسي): يبث الإنترنت ويستضيف النظام
- الجهاز 2 (العميل): يرسل إيميلات أو يفحص بيانات

عند اكتشاف بيانات حساسة، يتم تطبيق السياسات تلقائياً
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class DataProtectionTester:
    """مختبر نظام حماية البيانات"""
    
    def __init__(self, server_url: str, username: str = None, password: str = None):
        """
        تهيئة المختبر
        
        Args:
            server_url: عنوان السيرفر الرئيسي (مثال: http://192.168.1.100:8000)
            username: اسم المستخدم (اختياري)
            password: كلمة المرور (اختياري)
        """
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.token = None
        self.username = username
        self.password = password
        
        if username and password:
            self.login()
    
    def login(self) -> bool:
        """تسجيل الدخول للحصول على token"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/auth/login",
                data={
                    "username": self.username,
                    "password": self.password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                print(f"✓ تم تسجيل الدخول بنجاح: {self.username}")
                return True
            else:
                print(f"✗ فشل تسجيل الدخول: {response.status_code}")
                print(response.text)
                return False
        except Exception as e:
            print(f"✗ خطأ في تسجيل الدخول: {e}")
            return False
    
    def send_email(self, from_email: str, to_emails: list, subject: str, 
                   body: str, source_ip: str = None) -> Dict[str, Any]:
        """
        إرسال إيميل للفحص
        
        Args:
            from_email: عنوان المرسل
            to_emails: قائمة عناوين المستقبلين
            subject: موضوع الإيميل
            body: محتوى الإيميل
            source_ip: IP المصدر (اختياري)
        
        Returns:
            نتيجة التحليل
        """
        print(f"\n{'='*60}")
        print(f"📧 إرسال إيميل للفحص")
        print(f"{'='*60}")
        print(f"من: {from_email}")
        print(f"إلى: {', '.join(to_emails)}")
        print(f"الموضوع: {subject}")
        print(f"المحتوى: {body[:100]}...")
        
        email_data = {
            "from": from_email,
            "to": to_emails if isinstance(to_emails, list) else [to_emails],
            "subject": subject,
            "body": body,
            "source_ip": source_ip or "192.168.1.50",  # IP الجهاز الثاني
            "source_user": from_email
        }
        
        try:
            # استخدام endpoint مراقبة الإيميل
            response = self.session.post(
                f"{self.server_url}/api/monitoring/email",
                json=email_data
            )
            
            if response.status_code == 200:
                result = response.json()
                self._print_email_result(result)
                return result
            else:
                print(f"✗ خطأ في إرسال الإيميل: {response.status_code}")
                print(response.text)
                return {"error": response.text}
                
        except Exception as e:
            print(f"✗ خطأ في إرسال الإيميل: {e}")
            return {"error": str(e)}
    
    def analyze_text(self, text: str, source_ip: str = None, 
                    source_user: str = None) -> Dict[str, Any]:
        """
        فحص نص للبيانات الحساسة
        
        Args:
            text: النص للفحص
            source_ip: IP المصدر (اختياري)
            source_user: المستخدم (اختياري)
        
        Returns:
            نتيجة التحليل
        """
        print(f"\n{'='*60}")
        print(f"🔍 فحص نص للبيانات الحساسة")
        print(f"{'='*60}")
        print(f"النص: {text[:100]}...")
        
        analysis_data = {
            "text": text,
            "apply_policies": True,
            "source_ip": source_ip or "192.168.1.50",
            "source_user": source_user or "test_user",
            "source_device": "client_device"
        }
        
        try:
            response = self.session.post(
                f"{self.server_url}/api/analyze/",
                json=analysis_data
            )
            
            if response.status_code == 200:
                result = response.json()
                self._print_analysis_result(result)
                return result
            else:
                print(f"✗ خطأ في فحص النص: {response.status_code}")
                print(response.text)
                return {"error": response.text}
                
        except Exception as e:
            print(f"✗ خطأ في فحص النص: {e}")
            return {"error": str(e)}
    
    def analyze_file(self, file_path: str, source_ip: str = None,
                    source_user: str = None) -> Dict[str, Any]:
        """
        فحص ملف للبيانات الحساسة
        
        Args:
            file_path: مسار الملف
            source_ip: IP المصدر (اختياري)
            source_user: المستخدم (اختياري)
        
        Returns:
            نتيجة التحليل
        """
        print(f"\n{'='*60}")
        print(f"📄 فحص ملف للبيانات الحساسة")
        print(f"{'='*60}")
        print(f"الملف: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.split('/')[-1], f, 'application/octet-stream')}
                data = {
                    'apply_policies': True,
                    'source_ip': source_ip or "192.168.1.50",
                    'source_user': source_user or "test_user",
                    'source_device': 'client_device'
                }
                
                response = self.session.post(
                    f"{self.server_url}/api/analyze/file",
                    files=files,
                    data=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self._print_analysis_result(result)
                    return result
                else:
                    print(f"✗ خطأ في فحص الملف: {response.status_code}")
                    print(response.text)
                    return {"error": response.text}
                    
        except FileNotFoundError:
            print(f"✗ الملف غير موجود: {file_path}")
            return {"error": "File not found"}
        except Exception as e:
            print(f"✗ خطأ في فحص الملف: {e}")
            return {"error": str(e)}
    
    def check_alerts(self, limit: int = 10) -> Dict[str, Any]:
        """
        فحص التحذيرات الأخيرة
        
        Args:
            limit: عدد التحذيرات المطلوبة
        
        Returns:
            قائمة التحذيرات
        """
        print(f"\n{'='*60}")
        print(f"🚨 فحص التحذيرات الأخيرة")
        print(f"{'='*60}")
        
        try:
            response = self.session.get(
                f"{self.server_url}/api/alerts/",
                params={"limit": limit}
            )
            
            if response.status_code == 200:
                data = response.json()
                alerts = data.get("items", []) if isinstance(data, dict) else data
                
                print(f"عدد التحذيرات: {len(alerts)}")
                for i, alert in enumerate(alerts[:5], 1):
                    print(f"\n{i}. {alert.get('title', 'N/A')}")
                    print(f"   الحالة: {alert.get('status', 'N/A')}")
                    print(f"   الخطورة: {alert.get('severity', 'N/A')}")
                    print(f"   تم المنع: {'نعم' if alert.get('blocked') else 'لا'}")
                    print(f"   الوقت: {alert.get('created_at', 'N/A')}")
                
                return alerts
            else:
                print(f"✗ خطأ في جلب التحذيرات: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"✗ خطأ في فحص التحذيرات: {e}")
            return []
    
    def _print_email_result(self, result: Dict[str, Any]):
        """طباعة نتيجة فحص الإيميل"""
        print(f"\n{'─'*60}")
        print("📊 نتيجة فحص الإيميل:")
        print(f"{'─'*60}")
        print(f"تم اكتشاف بيانات حساسة: {'نعم ✓' if result.get('sensitive_data_detected') else 'لا ✗'}")
        print(f"الإجراء المتخذ: {result.get('action', 'N/A')}")
        print(f"تم المنع: {'نعم ✓' if result.get('blocked') else 'لا ✗'}")
        print(f"تم إنشاء تحذير: {'نعم ✓' if result.get('alert_created') else 'لا ✗'}")
        print(f"الرسالة: {result.get('message', 'N/A')}")
        
        if result.get('detected_entities'):
            print(f"\nالبيانات المكتشفة ({len(result['detected_entities'])}):")
            for entity in result['detected_entities'][:5]:
                print(f"  - {entity.get('entity_type', 'N/A')}: {entity.get('value', 'N/A')[:50]}")
        
        if result.get('applied_policies'):
            print(f"\nالسياسات المطبقة ({len(result['applied_policies'])}):")
            for policy in result['applied_policies']:
                print(f"  - {policy.get('name', 'N/A')}: {policy.get('action', 'N/A')}")
    
    def _print_analysis_result(self, result: Dict[str, Any]):
        """طباعة نتيجة فحص النص/الملف"""
        print(f"\n{'─'*60}")
        print("📊 نتيجة الفحص:")
        print(f"{'─'*60}")
        print(f"تم اكتشاف بيانات حساسة: {'نعم ✓' if result.get('sensitive_data_detected') else 'لا ✗'}")
        print(f"تم المنع: {'نعم ✓' if result.get('blocked') else 'لا ✗'}")
        print(f"تم إنشاء تحذير: {'نعم ✓' if result.get('alert_created') else 'لا ✗'}")
        print(f"تم تطبيق سياسات: {'نعم ✓' if result.get('policies_matched') else 'لا ✗'}")
        
        if result.get('detected_entities'):
            print(f"\nالبيانات المكتشفة ({len(result['detected_entities'])}):")
            for entity in result['detected_entities'][:5]:
                print(f"  - {entity.get('entity_type', 'N/A')}: {entity.get('value', 'N/A')[:50]}")
        
        if result.get('applied_policies'):
            print(f"\nالسياسات المطبقة ({len(result['applied_policies'])}):")
            for policy in result['applied_policies']:
                print(f"  - {policy.get('name', 'N/A')}: {policy.get('action', 'N/A')} ({policy.get('severity', 'N/A')})")
                print(f"    الكيانات المطابقة: {', '.join(policy.get('matched_entities', []))}")
        
        if result.get('actions_taken'):
            print(f"\nالإجراءات المتخذة:")
            for action in result['actions_taken']:
                print(f"  - {action}")


def run_test_scenario(server_url: str, username: str = None, password: str = None):
    """
    تشغيل سيناريو اختبار كامل
    
    Args:
        server_url: عنوان السيرفر الرئيسي
        username: اسم المستخدم (اختياري)
        password: كلمة المرور (اختياري)
    """
    print("="*60)
    print("🧪 سيناريو اختبار نظام حماية البيانات")
    print("="*60)
    print(f"السيرفر: {server_url}")
    print(f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    tester = DataProtectionTester(server_url, username, password)
    
    # السيناريو 1: إرسال إيميل يحتوي على بيانات حساسة
    print("\n\n🎯 السيناريو 1: إرسال إيميل يحتوي على بيانات حساسة")
    tester.send_email(
        from_email="employee@company.com",
        to_emails=["external@example.com"],
        subject="Customer Information",
        body="""
        Dear Customer,
        
        Here is your information:
        - Phone: 123-456-7890
        - Email: customer@example.com
        - Credit Card: 4532-1234-5678-9010
        - Address: 123 Main St, City, State 12345
        
        Best regards,
        Employee
        """
    )
    
    time.sleep(2)
    
    # السيناريو 2: فحص نص يحتوي على بيانات حساسة
    print("\n\n🎯 السيناريو 2: فحص نص يحتوي على بيانات حساسة")
    tester.analyze_text(
        text="""
        Patient Information:
        Name: John Doe
        SSN: 123-45-6789
        Phone: 555-123-4567
        Email: john.doe@email.com
        Medical Record: MR-12345
        """,
        source_user="test_user"
    )
    
    time.sleep(2)
    
    # السيناريو 3: إرسال إيميل بدون بيانات حساسة (يجب السماح)
    print("\n\n🎯 السيناريو 3: إرسال إيميل بدون بيانات حساسة")
    tester.send_email(
        from_email="employee@company.com",
        to_emails=["colleague@company.com"],
        subject="Meeting Reminder",
        body="Hi, don't forget about the meeting tomorrow at 2 PM."
    )
    
    time.sleep(2)
    
    # السيناريو 4: فحص نص يحتوي على سكريبت خبيث
    print("\n\n🎯 السيناريو 4: فحص نص يحتوي على سكريبت خبيث")
    tester.analyze_text(
        text="""
        <script>alert('XSS')</script>
        SELECT * FROM users WHERE 1=1
        eval('malicious code')
        """,
        source_user="test_user"
    )
    
    time.sleep(2)
    
    # فحص التحذيرات
    print("\n\n🎯 فحص التحذيرات الناتجة")
    tester.check_alerts(limit=10)
    
    print("\n\n" + "="*60)
    print("✅ اكتمل السيناريو")
    print("="*60)


if __name__ == "__main__":
    # إعدادات السيرفر
    # غيّر هذا العنوان إلى IP السيرفر الرئيسي
    SERVER_URL = "http://192.168.1.100:8000"  # مثال: IP السيرفر الرئيسي
    
    # إعدادات تسجيل الدخول (اختياري)
    USERNAME = None  # أو "admin"
    PASSWORD = None  # أو "password"
    
    # تشغيل السيناريو
    run_test_scenario(SERVER_URL, USERNAME, PASSWORD)
