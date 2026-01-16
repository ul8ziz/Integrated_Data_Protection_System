"""
Script to create default policy on first startup
يتم تشغيل هذا السكريبت مرة واحدة فقط عند بدء المشروع
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database_mongo import init_mongodb, is_initialized
from app.models_mongo.policies import Policy
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def create_default_policy():
    """
    Create default policy if it doesn't exist
    يتم إنشاء السياسة الأساسية فقط إذا لم تكن موجودة
    """
    try:
        # Check if MongoDB is initialized
        if not is_initialized():
            logger.info("MongoDB not initialized, initializing...")
            await init_mongodb()
        
        if not is_initialized():
            logger.error("Failed to initialize MongoDB. Cannot create default policy.")
            return False
        
        # Check if default policy already exists
        default_policy_name = "السياسة الأساسية - Default Policy"
        existing_policy = await Policy.find_one({"name": default_policy_name})
        
        if existing_policy:
            logger.info("Default policy already exists: %s", default_policy_name)
            logger.info("Policy ID: %s", str(existing_policy.id))
            return False  # Policy already exists, no need to create
        
        # Create default policy
        logger.info("Creating default policy...")
        
        default_policy = Policy(
            name=default_policy_name,
            description="سياسة أساسية لحماية البيانات الشخصية - Default policy for personal data protection. This policy monitors and alerts on sensitive information including personal names, phone numbers, email addresses, and credit card numbers.",
            entity_types=[
                "PERSON",           # الأسماء الشخصية
                "PHONE_NUMBER",     # أرقام الهواتف
                "EMAIL_ADDRESS",    # عناوين البريد الإلكتروني
                "CREDIT_CARD",      # أرقام البطاقات الائتمانية
                "ADDRESS",          # العناوين
                "ORGANIZATION"      # أسماء المنظمات
            ],
            action="alert",        # إرسال تنبيه عند اكتشاف البيانات الحساسة
            severity="high",       # مستوى الخطورة: عالي
            enabled=True,          # مفعّل
            apply_to_network=True,  # تطبيق على حركة الشبكة
            apply_to_devices=True,  # تطبيق على نقل البيانات من الأجهزة
            apply_to_storage=True,  # تطبيق على عمليات التخزين
            gdpr_compliant=True,    # متوافق مع GDPR
            hipaa_compliant=False,  # غير متوافق مع HIPAA (يمكن تغييره)
            created_by="system",   # تم الإنشاء بواسطة النظام
            created_at=datetime.utcnow()
        )
        
        await default_policy.insert()
        
        logger.info(f"✅ Default policy created successfully!")
        logger.info(f"   Policy ID: {default_policy.id}")
        logger.info(f"   Policy Name: {default_policy.name}")
        logger.info(f"   Entity Types: {', '.join(default_policy.entity_types)}")
        logger.info(f"   Action: {default_policy.action}")
        logger.info(f"   Severity: {default_policy.severity}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating default policy: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main function to run the script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("=" * 60)
    logger.info("Creating default policy...")
    logger.info("=" * 60)
    
    success = await create_default_policy()
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ Default policy created successfully!")
        logger.info("=" * 60)
    else:
        logger.info("=" * 60)
        logger.info("ℹ️  Default policy already exists or creation skipped")
        logger.info("=" * 60)
    
    # Close MongoDB connection
    from app.database_mongo import close_mongodb
    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
