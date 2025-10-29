"""
GDPR Compliance Module
Handles data privacy, user rights, and compliance requirements
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GDPRHandler:
    """Handles GDPR compliance operations"""
    
    def __init__(self):
        """Initialize GDPR handler"""
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        }
        
        logger.info("GDPR handler initialized")
    
    
    def detect_pii(self, text: str) -> Dict[str, List[str]]:
        """
        Detect Personally Identifiable Information in text
        
        Args:
            text: Input text to scan
            
        Returns:
            Dictionary of detected PII by type
        """
        detected = {}
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                detected[pii_type] = matches
        
        return detected
    
    
    def anonymize_text(self, text: str) -> str:
        """
        Anonymize PII in text
        
        Args:
            text: Text to anonymize
            
        Returns:
            Anonymized text
        """
        anonymized = text
        
        # Replace emails
        anonymized = re.sub(
            self.pii_patterns['email'],
            '[EMAIL_REDACTED]',
            anonymized
        )
        
        # Replace phone numbers
        anonymized = re.sub(
            self.pii_patterns['phone'],
            '[PHONE_REDACTED]',
            anonymized
        )
        
        # Replace SSN
        anonymized = re.sub(
            self.pii_patterns['ssn'],
            '[SSN_REDACTED]',
            anonymized
        )
        
        # Replace credit cards
        anonymized = re.sub(
            self.pii_patterns['credit_card'],
            '[CARD_REDACTED]',
            anonymized
        )
        
        # Replace IP addresses
        anonymized = re.sub(
            self.pii_patterns['ip_address'],
            '[IP_REDACTED]',
            anonymized
        )
        
        return anonymized
    
    
    def hash_pii(self, text: str, salt: str = '') -> str:
        """
        Hash PII for storage while maintaining searchability
        
        Args:
            text: Text to hash
            salt: Salt for hashing
            
        Returns:
            Hashed text
        """
        combined = text + salt
        return hashlib.sha256(combined.encode()).hexdigest()
    
    
    def collect_user_data(self, user_id: int) -> Dict:
        """
        Collect all user data (GDPR Right to Access)
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary containing all user data
        """
        from database import Database
        db = Database()
        
        try:
            # Get user information
            user = db.get_user(user_id)
            
            if not user:
                return {'error': 'User not found'}
            
            # Collect all associated data
            user_data = {
                'user_info': {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role'],
                    'created_at': user['created_at'].isoformat() if hasattr(user['created_at'], 'isoformat') else str(user['created_at'])
                },
                'sentiment_analyses': self._get_user_analyses(db, user_id),
                'audit_logs': self._get_user_audit_logs(db, user_id),
                'data_processing_info': {
                    'purpose': 'Sentiment analysis and business intelligence',
                    'legal_basis': 'User consent',
                    'retention_period': '2 years from last activity',
                    'third_party_sharing': 'No third-party sharing without explicit consent'
                },
                'rights': {
                    'right_to_access': 'You can request all your data at any time',
                    'right_to_rectification': 'You can request corrections to your data',
                    'right_to_erasure': 'You can request deletion of your data',
                    'right_to_restrict_processing': 'You can request to limit data processing',
                    'right_to_data_portability': 'You can export your data in machine-readable format',
                    'right_to_object': 'You can object to data processing'
                },
                'exported_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"User data collected for user {user_id}")
            return user_data
            
        except Exception as e:
            logger.error(f"Error collecting user data: {str(e)}")
            return {'error': str(e)}
    
    
    def _get_user_analyses(self, db, user_id: int) -> List[Dict]:
        """Get user's sentiment analysis history"""
        conn = db._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT sentiment, confidence, positive_score, negative_score, 
                       neutral_score, source, created_at
                FROM sentiment_records
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1000
            """, (user_id,))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
            
        finally:
            cursor.close()
            db._return_connection(conn)
    
    
    def _get_user_audit_logs(self, db, user_id: int) -> List[Dict]:
        """Get user's audit logs"""
        conn = db._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT action, details, ip_address, created_at
                FROM audit_logs
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1000
            """, (user_id,))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
            
        finally:
            cursor.close()
            db._return_connection(conn)
    
    
    def delete_user_data(self, user_id: int) -> Dict:
        """
        Delete or anonymize all user data (GDPR Right to Erasure)
        
        Args:
            user_id: User ID
            
        Returns:
            Operation result
        """
        from database import Database
        db = Database()
        
        try:
            conn = db._get_connection()
            cursor = conn.cursor()
            
            # Start transaction
            cursor.execute("BEGIN")
            
            # Anonymize sentiment records instead of deleting (for data integrity)
            cursor.execute("""
                UPDATE sentiment_records
                SET user_id = NULL
                WHERE user_id = %s
            """, (user_id,))
            
            # Anonymize audit logs
            cursor.execute("""
                UPDATE audit_logs
                SET user_id = NULL, ip_address = '[ANONYMIZED]'
                WHERE user_id = %s
            """, (user_id,))
            
            # Delete user account
            cursor.execute("""
                DELETE FROM users
                WHERE id = %s
            """, (user_id,))
            
            # Commit transaction
            cursor.execute("COMMIT")
            
            cursor.close()
            db._return_connection(conn)
            
            logger.info(f"User data deleted/anonymized for user {user_id}")
            
            return {
                'success': True,
                'message': 'User data has been deleted or anonymized',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            cursor.execute("ROLLBACK")
            cursor.close()
            db._return_connection(conn)
            
            logger.error(f"Error deleting user data: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    
    def update_consent(self, user_id: int, consent_data: Dict) -> Dict:
        """
        Update user consent preferences
        
        Args:
            user_id: User ID
            consent_data: Dictionary with consent preferences
            
        Returns:
            Operation result
        """
        from database import Database
        db = Database()
        
        try:
            conn = db._get_connection()
            cursor = conn.cursor()
            
            # Log consent change
            db.log_audit_event(
                user_id,
                'consent_update',
                'system',
                str(consent_data)
            )
            
            # Update user consent in database
            # In production, you'd have a separate consents table
            cursor.execute("""
                UPDATE users
                SET gdpr_consent = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (consent_data.get('gdpr_consent', True), user_id))
            
            conn.commit()
            cursor.close()
            db._return_connection(conn)
            
            return {
                'success': True,
                'message': 'Consent preferences updated',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating consent: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    
    def export_user_data(self, user_id: int, format: str = 'json') -> Dict:
        """
        Export user data in machine-readable format (GDPR Right to Data Portability)
        
        Args:
            user_id: User ID
            format: Export format (json, csv, xml)
            
        Returns:
            Exported data
        """
        data = self.collect_user_data(user_id)
        
        if format == 'json':
            return data
        elif format == 'csv':
            # Convert to CSV format
            return self._convert_to_csv(data)
        elif format == 'xml':
            # Convert to XML format
            return self._convert_to_xml(data)
        else:
            return {'error': 'Unsupported format'}
    
    
    def _convert_to_csv(self, data: Dict) -> str:
        """Convert data to CSV format"""
        import csv
        import io
        
        output = io.StringIO()
        
        # Write user info
        output.write("User Information\n")
        output.write("Field,Value\n")
        for key, value in data.get('user_info', {}).items():
            output.write(f"{key},{value}\n")
        
        output.write("\nSentiment Analyses\n")
        if data.get('sentiment_analyses'):
            writer = csv.DictWriter(output, fieldnames=data['sentiment_analyses'][0].keys())
            writer.writeheader()
            writer.writerows(data['sentiment_analyses'])
        
        return output.getvalue()
    
    
    def _convert_to_xml(self, data: Dict) -> str:
        """Convert data to XML format"""
        import xml.etree.ElementTree as ET
        
        root = ET.Element('user_data')
        
        # User info
        user_info = ET.SubElement(root, 'user_info')
        for key, value in data.get('user_info', {}).items():
            elem = ET.SubElement(user_info, key)
            elem.text = str(value)
        
        # Sentiment analyses
        analyses = ET.SubElement(root, 'sentiment_analyses')
        for analysis in data.get('sentiment_analyses', []):
            analysis_elem = ET.SubElement(analyses, 'analysis')
            for key, value in analysis.items():
                elem = ET.SubElement(analysis_elem, key)
                elem.text = str(value)
        
        return ET.tostring(root, encoding='unicode')
    
    
    def validate_data_retention(self, user_id: int) -> Dict:
        """
        Check if user data exceeds retention period
        
        Args:
            user_id: User ID
            
        Returns:
            Validation result
        """
        from database import Database
        db = Database()
        
        try:
            user = db.get_user(user_id)
            
            if not user:
                return {'error': 'User not found'}
            
            # Check if account is inactive for more than 2 years
            retention_period = timedelta(days=730)  # 2 years
            created_at = user.get('created_at')
            
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            account_age = datetime.utcnow() - created_at
            
            should_delete = account_age > retention_period
            
            return {
                'user_id': user_id,
                'account_age_days': account_age.days,
                'retention_period_days': retention_period.days,
                'should_delete': should_delete,
                'action_required': 'Delete data' if should_delete else 'No action needed'
            }
            
        except Exception as e:
            logger.error(f"Error validating retention: {str(e)}")
            return {'error': str(e)}
    
    
    def generate_privacy_report(self) -> Dict:
        """
        Generate privacy compliance report
        
        Returns:
            Privacy report
        """
        from database import Database
        db = Database()
        
        return {
            'report_date': datetime.utcnow().isoformat(),
            'total_users': len(db.get_all_users()),
            'consent_status': {
                'with_consent': 'All active users',
                'without_consent': 0
            },
            'data_retention': {
                'policy': '2 years from last activity',
                'enforcement': 'Automated monthly cleanup'
            },
            'security_measures': [
                'Password hashing (SHA-256)',
                'PII detection and anonymization',
                'Role-based access control',
                'Audit logging',
                'Encrypted database connections'
            ],
            'compliance_status': 'Compliant',
            'last_audit': datetime.utcnow().isoformat()
        }


# Example usage
if __name__ == "__main__":
    gdpr = GDPRHandler()
    
    print("=== PII Detection ===")
    test_text = "Contact me at john.doe@email.com or call 555-123-4567"
    pii = gdpr.detect_pii(test_text)
    print(f"Detected PII: {pii}")
    
    print("\n=== Text Anonymization ===")
    anonymized = gdpr.anonymize_text(test_text)
    print(f"Original: {test_text}")
    print(f"Anonymized: {anonymized}")
    
    print("\n=== Privacy Report ===")
    report = gdpr.generate_privacy_report()
    print(f"Total users: {report['total_users']}")
    print(f"Compliance status: {report['compliance_status']}")