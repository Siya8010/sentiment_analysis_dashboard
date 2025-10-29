"""
Database Initialization Script
Creates all necessary tables and indexes
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.database_sqlite import Database
except ImportError:
    from core.database import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database with all tables"""
    try:
        logger.info("Initializing database...")
        
        db = Database()
        
        # Tables are created in Database.__init__()
        # Check connection
        if db.check_connection():
            logger.info("✓ Database initialized successfully!")
            logger.info("✓ All tables created")
            logger.info("✓ Indexes created")
            
            # Create default admin user
            create_default_admin(db)
            
            return True
        else:
            logger.error("✗ Database connection failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error initializing database: {str(e)}")
        return False


def create_default_admin(db):
    """Create default admin user"""
    try:
        admin_user = db.create_user(
            email='admin@sentimentdashboard.com',
            password='Admin@123',  # Change this immediately after first login!
            name='System Administrator',
            role='admin',
            gdpr_consent=True
        )
        
        if admin_user['success']:
            logger.info("✓ Default admin user created")
            logger.info("  Email: admin@sentimentdashboard.com")
            logger.info("  Password: Admin@123")
            logger.warning("  ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")
        else:
            logger.info("  Admin user already exists or creation failed")
            
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
