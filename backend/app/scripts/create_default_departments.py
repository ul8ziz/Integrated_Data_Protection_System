"""
Script to create default departments on first startup
يتم تشغيل هذا السكريبت عند بدء المشروع لإنشاء الأقسام الافتراضية
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database_mongo import init_mongodb, is_initialized
from app.models_mongo.departments import Department
from app.utils.datetime_utils import get_current_time
import logging

logger = logging.getLogger(__name__)

DEFAULT_DEPARTMENTS = [
    {"name": "تقنية المعلومات", "description": "قسم تقنية المعلومات - IT Department"},
    {"name": "الموارد البشرية", "description": "قسم الموارد البشرية - Human Resources"},
    {"name": "المبيعات", "description": "قسم المبيعات - Sales Department"},
]


async def create_default_departments():
    """
    Create default departments if they don't exist.
    يتم إنشاء الأقسام الافتراضية فقط إذا لم تكن موجودة.
    """
    try:
        if not is_initialized():
            logger.info("MongoDB not initialized, initializing...")
            await init_mongodb()

        if not is_initialized():
            logger.error("Failed to initialize MongoDB. Cannot create default departments.")
            return False

        created_count = 0
        for dept_data in DEFAULT_DEPARTMENTS:
            existing = await Department.find_one({"name": dept_data["name"]})
            if existing:
                logger.info("Department already exists: %s", dept_data["name"])
                continue
            dept = Department(
                name=dept_data["name"],
                description=dept_data.get("description"),
                created_at=get_current_time(),
            )
            await dept.insert()
            created_count += 1
            logger.info("Created default department: %s (id=%s)", dept.name, dept.id)

        if created_count > 0:
            logger.info("Default departments created: %s new", created_count)
        return True
    except Exception as e:
        logger.error("Error creating default departments: %s", e)
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main function to run the script"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("=" * 60)
    logger.info("Creating default departments...")
    logger.info("=" * 60)
    await create_default_departments()
    from app.database_mongo import close_mongodb
    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
