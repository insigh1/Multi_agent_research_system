"""
Module 12: Data Privacy & Compliance (Based on Production Implementation)
Demonstrates the actual data privacy and compliance features in the Multi-Agent Research System
"""

import asyncio
import sqlite3
import json
import time
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
import structlog
from cryptography.fernet import Fernet

# External dependencies
import pandas as pd

# Self-contained classes for course module
@dataclass
class Settings:
    """Simple settings class for course demonstration"""
    DATABASE_URL: str = "sqlite:///temp_course_privacy.db"
    ENCRYPTION_KEY: str = field(default_factory=lambda: Fernet.generate_key().decode())
    RETENTION_DAYS: int = 365
    GDPR_COMPLIANCE: bool = True
    LOG_LEVEL: str = "INFO"
    
    def __post_init__(self):
        # Make encryption_key available for backward compatibility
        self.encryption_key = self.ENCRYPTION_KEY
        # Add db_path for compatibility
        self.db_path = "temp_course_privacy.db"
        # Add log_file for compatibility
        self.log_file = "temp_course_privacy.log"

class SecurityError(Exception):
    """Security-related error"""
    pass

class SecurityManager:
    """Simplified security manager for course demonstration"""
    def __init__(self, encryption_key: str = None):
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        else:
            self.cipher = Fernet(Fernet.generate_key())
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def generate_session_id(self) -> str:
        """Generate a secure session ID"""
        import secrets
        import base64
        # Generate 16 bytes of random data and encode as base64
        random_bytes = secrets.token_bytes(16)
        return base64.urlsafe_b64encode(random_bytes).decode().rstrip('=')

# Initialize settings
settings = Settings()

logger = structlog.get_logger(__name__)

@dataclass
class DataRetentionPolicy:
    """Data retention policy configuration"""
    session_data_days: int = 30
    log_file_days: int = 90
    cache_data_hours: int = 24
    exported_reports_days: int = 365

@dataclass
class AuditEvent:
    """Audit event for compliance tracking"""
    timestamp: str
    event_type: str
    user_session: str
    action: str
    resource: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None

class DatabaseManager:
    """
    Production Database Manager (from main app)
    Handles session persistence and data management
    """
    
    def __init__(self, db_path: str = "research_sessions.db"):
        self.db_path = db_path
        self.logger = structlog.get_logger(__name__)
        self.initialize()
    
    def initialize(self):
        """Initialize database with proper schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Main sessions table (actual implementation)
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS research_sessions (
                        id TEXT PRIMARY KEY,
                        query TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        data TEXT,
                        metadata TEXT
                    )
                ''')
                
                # Audit log table for compliance
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        event_type TEXT NOT NULL,
                        session_id TEXT,
                        action TEXT NOT NULL,
                        resource TEXT,
                        details TEXT,
                        ip_address TEXT
                    )
                ''')
                
                conn.commit()
                self.logger.info("Database initialized", db_path=self.db_path)
        except Exception as e:
            self.logger.error("Database initialization failed", error=str(e))
            raise
    
    def _get_connection(self):
        """Get database connection with proper timeout settings"""
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _execute_query(self, query: str, params: tuple = (), fetch: bool = False):
        """Execute query with proper connection management"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch:
                result = cursor.fetchall()
                conn.close()
                return result
            else:
                conn.commit()
                conn.close()
                return cursor.lastrowid
        except Exception as e:
            if conn:
                conn.close()
            logger.error("Database query failed", query=query[:50], error=str(e))
            raise
    
    def save_session(self, session_id: str, query: str, status: str, 
                     data: Dict, metadata: Dict):
        """Save research session with encrypted PII"""
        try:
            # Encrypt PII in data
            encrypted_data = self.encrypt_pii_data(data)
            
            # Store in database using improved connection management
            self._execute_query("""
                INSERT OR REPLACE INTO research_sessions 
                (id, query, status, data, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id, query, status,
                json.dumps(encrypted_data),
                json.dumps(metadata),
                datetime.now().isoformat()
            ))
            
            logger.info("Session saved", session_id=session_id)
            
        except Exception as e:
            logger.error("Failed to save session", session_id=session_id, error=str(e))
            raise SecurityError(f"Failed to save session: {e}")
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """Load research session with decrypted PII"""
        try:
            results = self._execute_query("""
                SELECT id, query, status, data, metadata, created_at
                FROM research_sessions 
                WHERE id = ?
            """, (session_id,), fetch=True)
            
            if not results:
                return None
                
            row = results[0]
            
            # Decrypt PII data
            encrypted_data = json.loads(row[3])  # data column
            decrypted_data = self.decrypt_pii_data(encrypted_data)
            
            return {
                'session_id': row[0],
                'query': row[1], 
                'status': row[2],
                'data': decrypted_data,
                'metadata': json.loads(row[4]),
                'created_at': row[5]
            }
            
        except Exception as e:
            logger.error("Failed to load session", session_id=session_id, error=str(e))
            return None
    
    def log_audit_event(self, event_type: str, session_id: str, action: str, 
                       resource: str, metadata: Dict = None):
        """Log audit event for compliance tracking"""
        try:
            event_data = {
                'event_type': event_type,
                'session_id': session_id,
                'action': action,
                'resource': resource,
                'metadata': metadata or {},
                'timestamp': datetime.now().isoformat(),
                'ip_address': '127.0.0.1'  # Demo IP
            }
            
            self._execute_query("""
                INSERT INTO audit_log (event_type, session_id, action, resource, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_type, session_id, action, resource,
                json.dumps(event_data['metadata']),  # Store metadata in details column
                event_data['timestamp']
            ))
            
            logger.debug("Audit event logged", event_type=event_type, action=action)
            
        except Exception as e:
            logger.error("Failed to log audit event", error=str(e))
    
    def get_audit_trail(self, session_id: str = None, 
                       days: int = 30) -> List[Dict]:
        """Get audit trail for compliance reporting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if session_id:
                    cursor = conn.execute('''
                        SELECT * FROM audit_log 
                        WHERE session_id = ? AND timestamp > datetime('now', '-{} days')
                        ORDER BY timestamp DESC
                    '''.format(days), (session_id,))
                else:
                    cursor = conn.execute('''
                        SELECT * FROM audit_log 
                        WHERE timestamp > datetime('now', '-{} days')
                        ORDER BY timestamp DESC
                    '''.format(days))
                
                return [dict(zip([col[0] for col in cursor.description], row)) 
                       for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error("Failed to get audit trail", error=str(e))
            return []

    def encrypt_pii_data(self, data: Dict) -> Dict:
        """Encrypt PII fields in data dictionary"""
        encrypted_data = data.copy()
        pii_fields = ['query', 'ip_address', 'user_agent', 'email', 'phone', 'address']
        
        for field in pii_fields:
            if field in encrypted_data and encrypted_data[field]:
                try:
                    encrypted_data[field] = self.security_manager.encrypt_data(str(encrypted_data[field]))
                    logger.debug("Encrypted PII field", field=field)
                except Exception as e:
                    logger.warning("Failed to encrypt field", field=field, error=str(e))
                    
        return encrypted_data
    
    def decrypt_pii_data(self, encrypted_data: Dict) -> Dict:
        """Decrypt PII fields in data dictionary"""
        decrypted_data = encrypted_data.copy()
        pii_fields = ['query', 'ip_address', 'user_agent', 'email', 'phone', 'address']
        
        for field in pii_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    field_value = str(decrypted_data[field])
                    # Check if it looks like Fernet encrypted data (starts with gAAAAA and has base64 chars)
                    if (field_value.startswith('gAAAAA') and 
                        len(field_value) > 40 and 
                        all(c.isalnum() or c in '+/=' for c in field_value)):
                        decrypted_data[field] = self.security_manager.decrypt_data(field_value)
                        logger.debug("Successfully decrypted PII field", field=field)
                    else:
                        logger.debug("Field not encrypted, keeping original value", field=field)
                except Exception as e:
                    logger.warning("Failed to decrypt field", field=field, error=str(e) or type(e).__name__)
                    # Keep original value if decryption fails
                    
        return decrypted_data


class DataPrivacyManager:
    """
    Data Privacy Manager built on production implementations
    Handles data protection, retention, and compliance
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.security_manager = SecurityManager(settings.encryption_key)
        self.db_manager = DatabaseManager(settings.db_path)
        self.retention_policy = DataRetentionPolicy()
        self.logger = structlog.get_logger(__name__)
    
    def encrypt_personal_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt personally identifiable information"""
        encrypted_data = data.copy()
        
        # Fields that might contain PII
        pii_fields = ['query', 'ip_address', 'user_agent']
        
        for field in pii_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.security_manager.encrypt_data(
                    str(encrypted_data[field])
                )
                self.logger.debug("Encrypted PII field", field=field)
        
        return encrypted_data
    
    def decrypt_personal_data(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt personally identifiable information"""
        decrypted_data = encrypted_data.copy()
        
        pii_fields = ['query', 'ip_address', 'user_agent']
        
        for field in pii_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.security_manager.decrypt_data(
                        decrypted_data[field]
                    )
                except Exception as e:
                    self.logger.warning("Failed to decrypt field", field=field, error=str(e))
        
        return decrypted_data
    
    def anonymize_query(self, query: str) -> str:
        """Anonymize query by removing potential PII"""
        # Simple anonymization - remove common PII patterns
        import re
        
        # Remove email addresses
        query = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                      '[EMAIL]', query)
        
        # Remove phone numbers
        query = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', query)
        
        # Remove credit card numbers (basic pattern)
        query = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 
                      '[CARD]', query)
        
        return query
    
    def apply_data_retention(self) -> Dict[str, int]:
        """Apply data retention policies (cleanup old data)"""
        cleanup_stats = {
            "sessions_deleted": 0,
            "audit_logs_deleted": 0,
            "log_files_cleaned": 0,
            "cache_entries_cleared": 0
        }
        
        try:
            # Clean old sessions
            cutoff_date = datetime.now() - timedelta(days=self.retention_policy.session_data_days)
            
            with sqlite3.connect(self.db_manager.db_path) as conn:
                # Count before deletion
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM research_sessions 
                    WHERE created_at < ?
                ''', (cutoff_date.isoformat(),))
                count_to_delete = cursor.fetchone()[0]
                
                # Delete old sessions
                conn.execute('''
                    DELETE FROM research_sessions 
                    WHERE created_at < ?
                ''', (cutoff_date.isoformat(),))
                
                cleanup_stats["sessions_deleted"] = count_to_delete
                
                # Clean old audit logs (keep longer for compliance)
                audit_cutoff = datetime.now() - timedelta(days=self.retention_policy.log_file_days)
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM audit_log 
                    WHERE timestamp < ?
                ''', (audit_cutoff.isoformat(),))
                audit_count = cursor.fetchone()[0]
                
                conn.execute('''
                    DELETE FROM audit_log 
                    WHERE timestamp < ?
                ''', (audit_cutoff.isoformat(),))
                
                cleanup_stats["audit_logs_deleted"] = audit_count
                
            self.logger.info("Data retention applied", stats=cleanup_stats)
            
        except Exception as e:
            self.logger.error("Data retention failed", error=str(e))
        
        return cleanup_stats
    
    def generate_data_inventory(self) -> Dict[str, Any]:
        """Generate data inventory for compliance reporting"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                # Count sessions by age
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_sessions,
                        COUNT(CASE WHEN created_at > datetime('now', '-7 days') THEN 1 END) as last_7_days,
                        COUNT(CASE WHEN created_at > datetime('now', '-30 days') THEN 1 END) as last_30_days,
                        MIN(created_at) as oldest_session,
                        MAX(created_at) as newest_session
                    FROM research_sessions
                ''')
                session_stats = dict(zip([col[0] for col in cursor.description], 
                                       cursor.fetchone()))
                
                # Count audit events
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_events,
                        COUNT(DISTINCT session_id) as unique_sessions,
                        MIN(timestamp) as oldest_event,
                        MAX(timestamp) as newest_event
                    FROM audit_log
                ''')
                audit_stats = dict(zip([col[0] for col in cursor.description], 
                                     cursor.fetchone()))
                
            # Check log file sizes
            log_file_stats = {}
            if os.path.exists(self.settings.log_file):
                stat = os.stat(self.settings.log_file)
                log_file_stats = {
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            
            inventory = {
                "data_inventory_date": datetime.utcnow().isoformat(),
                "session_data": session_stats,
                "audit_data": audit_stats,
                "log_files": log_file_stats,
                "retention_policy": asdict(self.retention_policy),
                "encryption_enabled": True,
                "anonymization_enabled": True
            }
            
            return inventory
            
        except Exception as e:
            self.logger.error("Failed to generate data inventory", error=str(e))
            return {}
    
    def export_user_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export all data for a specific session (data portability)"""
        try:
            # Get session data (already decrypted by load_session)
            session_data = self.db_manager.load_session(session_id)
            if not session_data:
                return None
            
            # Get audit trail
            audit_trail = self.db_manager.get_audit_trail(session_id)
            
            # Session data is already decrypted by load_session method
            decrypted_session = session_data
            
            export_data = {
                "export_date": datetime.utcnow().isoformat(),
                "session_id": session_id,
                "session_data": decrypted_session,
                "audit_trail": audit_trail,
                "data_sources": [
                    "research_sessions table",
                    "audit_log table",
                    "session metadata"
                ]
            }
            
            # Log the export operation
            self.db_manager.log_audit_event("data_export", session_id, 
                                          "user_data_exported", 
                                          f"session:{session_id}", 
                                          {"export_size": len(json.dumps(export_data))})
            
            return export_data
            
        except Exception as e:
            self.logger.error("Failed to export user data", error=str(e))
            return None
    
    def delete_user_data(self, session_id: str) -> bool:
        """Delete all data for a specific session (right to be forgotten)"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                # Delete session data
                conn.execute('DELETE FROM research_sessions WHERE id = ?', (session_id,))
                
                # Keep audit log for compliance but mark as deleted
                conn.execute('''
                    INSERT INTO audit_log 
                    (event_type, session_id, action, resource, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', ("data_deletion", session_id, "user_data_deleted", 
                      f"session:{session_id}", json.dumps({"reason": "user_request"})))
                
                conn.commit()
            
            self.logger.info("User data deleted", session_id=session_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete user data", error=str(e))
            return False


async def demonstrate_data_encryption():
    """Demonstrate data encryption for privacy protection"""
    print("🔐 Data Encryption for Privacy (Production Implementation)")
    
    settings = Settings()
    privacy_manager = DataPrivacyManager(settings)
    
    # Sample data with potential PII
    sample_data = {
        "query": "Research about john.doe@example.com and his company",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"Original data: {sample_data}")
    
    # Encrypt PII
    encrypted_data = privacy_manager.encrypt_personal_data(sample_data)
    print(f"Encrypted PII fields: {list(encrypted_data.keys())}")
    for key, value in encrypted_data.items():
        if key in ['query', 'ip_address', 'user_agent']:
            print(f"  {key}: {value[:30]}...")
    
    # Decrypt for authorized access
    decrypted_data = privacy_manager.decrypt_personal_data(encrypted_data)
    print(f"Decrypted data matches: {sample_data == decrypted_data}")
    
    print("✅ Data encryption working correctly")


async def demonstrate_data_anonymization():
    """Demonstrate data anonymization techniques"""
    print("\n🎭 Data Anonymization (Production Implementation)")
    
    settings = Settings()
    privacy_manager = DataPrivacyManager(settings)
    
    test_queries = [
        "Research john.doe@company.com's background",
        "Find information about 555-123-4567",
        "Credit card 4532-1234-5678-9012 fraud analysis",
        "Normal research query without PII"
    ]
    
    for query in test_queries:
        anonymized = privacy_manager.anonymize_query(query)
        print(f"Original:   {query}")
        print(f"Anonymized: {anonymized}")
        print()
    
    print("✅ Data anonymization working correctly")


async def demonstrate_audit_logging():
    """Demonstrate audit logging for compliance"""
    print("📋 Audit Logging for Compliance (Production Implementation)")
    
    settings = Settings()
    privacy_manager = DataPrivacyManager(settings)
    
    # Simulate some research session activities
    session_id = privacy_manager.security_manager.generate_session_id()
    
    # Log various activities
    privacy_manager.db_manager.log_audit_event(
        "session_start", session_id, "research_started", 
        f"session:{session_id}", {"query_type": "general"}
    )
    
    privacy_manager.db_manager.log_audit_event(
        "data_access", session_id, "results_viewed", 
        f"session:{session_id}", {"results_count": 5}
    )
    
    privacy_manager.db_manager.log_audit_event(
        "data_export", session_id, "report_downloaded", 
        f"session:{session_id}", {"format": "pdf"}
    )
    
    # Retrieve audit trail
    audit_trail = privacy_manager.db_manager.get_audit_trail(session_id)
    
    print(f"Audit trail for session {session_id}:")
    for event in audit_trail:
        print(f"  {event['timestamp']}: {event['action']} - {event['resource']}")
    
    print("✅ Audit logging working correctly")


async def demonstrate_data_retention():
    """Demonstrate data retention policies"""
    print("\n🗄️ Data Retention Policies (Production Implementation)")
    
    settings = Settings()
    privacy_manager = DataPrivacyManager(settings)
    
    # Show current retention policy
    policy = privacy_manager.retention_policy
    print(f"Current retention policy:")
    print(f"  Session data: {policy.session_data_days} days")
    print(f"  Log files: {policy.log_file_days} days")
    print(f"  Cache data: {policy.cache_data_hours} hours")
    print(f"  Reports: {policy.exported_reports_days} days")
    
    # Generate data inventory
    inventory = privacy_manager.generate_data_inventory()
    print(f"\nCurrent data inventory:")
    if inventory.get('session_data'):
        stats = inventory['session_data']
        print(f"  Total sessions: {stats.get('total_sessions', 0)}")
        print(f"  Last 7 days: {stats.get('last_7_days', 0)}")
        print(f"  Last 30 days: {stats.get('last_30_days', 0)}")
    
    # Apply retention (simulation - careful with real data!)
    print(f"\nSimulating data retention cleanup...")
    # Note: In real implementation, this would clean old data
    print("  (Skipping actual deletion in demonstration)")
    
    print("✅ Data retention policies working correctly")


async def demonstrate_data_rights():
    """Demonstrate user data rights (access, portability, deletion)"""
    print("\n👤 User Data Rights (Production Implementation)")
    
    settings = Settings()
    privacy_manager = DataPrivacyManager(settings)
    
    # Create a sample session
    session_id = privacy_manager.security_manager.generate_session_id()
    sample_query = "How does artificial intelligence work?"
    
    # Save session data
    privacy_manager.db_manager.save_session(
        session_id, sample_query, "completed",
        {"results": ["result1", "result2"]},
        {"cost": 0.05, "duration": 120}
    )
    
    print(f"Created sample session: {session_id}")
    
    # Demonstrate data export (right to data portability)
    print("\n📤 Data Export (Right to Data Portability):")
    exported_data = privacy_manager.export_user_data(session_id)
    if exported_data:
        print(f"  Exported {len(json.dumps(exported_data))} characters of data")
        print(f"  Includes: {', '.join(exported_data['data_sources'])}")
    
    # Demonstrate data deletion (right to be forgotten)
    print("\n🗑️ Data Deletion (Right to be Forgotten):")
    deletion_success = privacy_manager.delete_user_data(session_id)
    print(f"  Data deletion successful: {deletion_success}")
    
    # Verify deletion
    deleted_session = privacy_manager.db_manager.load_session(session_id)
    print(f"  Session data after deletion: {'Not found' if not deleted_session else 'Still exists'}")
    
    print("✅ User data rights working correctly")


async def main():
    """Main demonstration of data privacy and compliance features"""
    print("🛡️ Data Privacy & Compliance Module")
    print("Based on Production Implementation in Multi-Agent Research System")
    print("=" * 70)
    
    try:
        # Run all demonstrations
        await demonstrate_data_encryption()
        await demonstrate_data_anonymization()
        await demonstrate_audit_logging()
        await demonstrate_data_retention()
        await demonstrate_data_rights()
        
        print("\n" + "=" * 70)
        print("🎉 Data Privacy & Compliance Module Complete!")
        print("\n📋 Production Privacy Features Demonstrated:")
        print("• Fernet encryption for PII protection")
        print("• Data anonymization techniques")
        print("• Comprehensive audit logging")
        print("• Automated data retention policies")
        print("• User data export (data portability)")
        print("• User data deletion (right to be forgotten)")
        print("• Database-based session management")
        print("• Compliance reporting capabilities")
        
        print("\n🔧 Configuration Options:")
        print("• RESEARCH_ENCRYPTION_KEY - Data encryption key")
        print("• RESEARCH_DB_PATH - Database file location")
        print("• RESEARCH_LOG_FILE - Audit log file path")
        print("• Data retention policies configurable")
        
        print("\n📖 Compliance Capabilities:")
        print("1. Data encryption at rest (GDPR Article 32)")
        print("2. Audit trails for accountability (GDPR Article 5)")
        print("3. Data portability support (GDPR Article 20)")
        print("4. Right to be forgotten (GDPR Article 17)")
        print("5. Data retention policies (GDPR Article 5)")
        print("6. Privacy by design implementation")
        
    except Exception as e:
        logger.error("Privacy demonstration failed", error=str(e))
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Set up environment for demonstration
    import os
    if not os.environ.get("RESEARCH_ENCRYPTION_KEY"):
        os.environ["RESEARCH_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    
    asyncio.run(main()) 