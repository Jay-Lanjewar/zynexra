"""
Database service for Zynexra persistence layer.
Handles SQLite operations with graceful degradation if database is unavailable.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from backend.logger import logger


class DatabaseService:
    """Lightweight database service with optional graceful degradation."""
    
    def __init__(self, db_path: str = "./data/zynexra.db"):
        """Initialize database service.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.available = False
        self._initialized = False
        
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
            self._init_database()
            self.available = True
            logger.info(f"[DB] Database initialized at {db_path}")
        except Exception as e:
            logger.warning(f"[DB] Database initialization failed: {str(e)}. App will work without persistence.")
            self.available = False
    
    def _init_database(self):
        """Initialize database schema if not exists."""
        if self._initialized and self.available:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Audit History Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                issue_count INTEGER DEFAULT 0,
                issues_json TEXT,
                raw_response TEXT,
                mode TEXT DEFAULT 'AUDIT',
                severity_level TEXT
            )
            """)
            
            # Advisory Sessions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS advisory_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                title TEXT,
                messages_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0
            )
            """)
            
            # Redaction History Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS redaction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                redaction_count INTEGER DEFAULT 0,
                entities_json TEXT,
                redacted_text TEXT,
                redaction_types TEXT
            )
            """)
            
            # Create indices for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_filename ON audit_history(filename)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_mode ON audit_history(mode)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_redaction_timestamp ON redaction_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_redaction_filename ON redaction_history(filename)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_advisory_timestamp ON advisory_sessions(timestamp)")
            
            conn.commit()
            self._initialized = True
            logger.info("[DB] Schema initialized successfully")
            
        except Exception as e:
            logger.error(f"[DB] Schema initialization failed: {str(e)}")
            raise
        finally:
            conn.close()
    
    def insert_audit(self, filename: str, issue_count: int, issues: Dict[str, Any], 
                     raw_response: str, mode: str = "AUDIT", severity_level: Optional[str] = None) -> Optional[int]:
        """Insert audit record into database.
        
        Args:
            filename: Name of file analyzed
            issue_count: Number of issues found
            issues: Dictionary of issues
            raw_response: Raw model response
            mode: Audit mode
            severity_level: Severity level of issues
            
        Returns:
            Record ID if successful, None otherwise
        """
        if not self.available:
            return None
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            issues_json = json.dumps(issues) if isinstance(issues, (dict, list)) else str(issues)
            
            cursor.execute("""
            INSERT INTO audit_history 
            (filename, issue_count, issues_json, raw_response, mode, severity_level)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (filename, issue_count, issues_json, raw_response, mode, severity_level))
            
            record_id = cursor.lastrowid
            conn.commit()
            logger.debug(f"[DB] Audit record inserted: id={record_id}, filename={filename}, mode={mode}")
            logger.debug(f"[History] Record persisted -> mode={mode}, id={record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"[DB] Failed to insert audit: {str(e)}")
            return None
        finally:
            conn.close()
    
    def insert_redaction(self, filename: str, redaction_count: int, entities: Dict[str, Any],
                        redacted_text: str, redaction_types: Optional[str] = None) -> Optional[int]:
        """Insert redaction record into database.
        
        Args:
            filename: Name of file redacted
            redaction_count: Number of entities redacted
            entities: Dictionary of redacted entities
            redacted_text: The redacted text
            redaction_types: Types of redactions performed
            
        Returns:
            Record ID if successful, None otherwise
        """
        if not self.available:
            return None
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            entities_json = json.dumps(entities) if isinstance(entities, dict) else str(entities)
            
            cursor.execute("""
            INSERT INTO redaction_history
            (filename, redaction_count, entities_json, redacted_text, redaction_types)
            VALUES (?, ?, ?, ?, ?)
            """, (filename, redaction_count, entities_json, redacted_text, redaction_types))
            
            record_id = cursor.lastrowid
            conn.commit()
            logger.debug(f"[DB] Redaction record inserted: id={record_id}, filename={filename}")
            return record_id
            
        except Exception as e:
            logger.error(f"[DB] Failed to insert redaction: {str(e)}")
            return None
        finally:
            conn.close()
    
    def insert_advisory(self, session_id: str, messages: List[Dict[str, str]], 
                       title: Optional[str] = None) -> Optional[int]:
        """Insert or update advisory session record.
        
        Args:
            session_id: Unique session identifier
            messages: List of messages in session
            title: Optional title for session
            
        Returns:
            Record ID if successful, None otherwise
        """
        if not self.available:
            return None
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            messages_json = json.dumps(messages)
            message_count = len(messages) if isinstance(messages, list) else 0
            
            # Try update first, then insert
            cursor.execute("""
            UPDATE advisory_sessions 
            SET messages_json = ?, message_count = ?, timestamp = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """, (messages_json, message_count, session_id))
            
            if cursor.rowcount == 0:
                cursor.execute("""
                INSERT INTO advisory_sessions
                (session_id, title, messages_json, message_count)
                VALUES (?, ?, ?, ?)
                """, (session_id, title or f"Session {session_id[:8]}", messages_json, message_count))
            
            record_id = cursor.lastrowid
            conn.commit()
            logger.debug(f"[DB] Advisory record saved: session_id={session_id}, message_count={message_count}")
            logger.debug(f"[History] Record persisted -> mode=ADVISORY, session_id={session_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"[DB] Failed to insert advisory: {str(e)}")
            return None
        finally:
            conn.close()
    
    def get_audit_history(self, limit: int = 50, offset: int = 0, 
                          filename: Optional[str] = None, mode: Optional[str] = None,
                          severity: Optional[str] = None, start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve audit history with optional filters.
        
        Args:
            limit: Max records to return
            offset: Pagination offset
            filename: Filter by filename (partial match)
            mode: Filter by mode (AUDIT, REDACTION, ADVISORY)
            severity: Filter by severity level
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            
        Returns:
            List of audit records
        """
        if not self.available:
            return []
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_history WHERE 1=1"
            params = []
            
            # Exclude ADVISORY mode records from audit_history (they belong in advisory_sessions)
            query += " AND mode != 'ADVISORY'"
            
            if filename:
                query += " AND filename LIKE ?"
                params.append(f"%{filename}%")
            if mode:
                query += " AND mode = ?"
                params.append(mode)
            if severity:
                query += " AND severity_level = ?"
                params.append(severity)
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                try:
                    issues = json.loads(row[4]) if row[4] else {}
                except (json.JSONDecodeError, TypeError):
                    issues = {}
                results.append({
                    "id": row[0],
                    "filename": row[1],
                    "timestamp": row[2],
                    "issue_count": row[3],
                    "issues": issues,
                    "raw_response": row[5],
                    "mode": row[6],
                    "severity_level": row[7]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"[DB] Failed to retrieve audit history: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_redaction_history(self, limit: int = 50, offset: int = 0,
                             filename: Optional[str] = None, start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve redaction history with optional filters.
        
        Args:
            limit: Max records to return
            offset: Pagination offset
            filename: Filter by filename (partial match)
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            
        Returns:
            List of redaction records
        """
        if not self.available:
            return []
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM redaction_history WHERE 1=1"
            params = []
            
            if filename:
                query += " AND filename LIKE ?"
                params.append(f"%{filename}%")
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "filename": row[1],
                    "timestamp": row[2],
                    "redaction_count": row[3],
                    "entities": json.loads(row[4]) if row[4] else {},
                    "redacted_text": row[5],
                    "redaction_types": row[6]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"[DB] Failed to retrieve redaction history: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_advisory_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve advisory sessions history.
        
        Args:
            limit: Max records to return
            offset: Pagination offset
            
        Returns:
            List of advisory session records
        """
        if not self.available:
            return []
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT id, session_id, title, messages_json, timestamp, message_count
            FROM advisory_sessions
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "session_id": row[1],
                    "title": row[2],
                    "messages": json.loads(row[3]) if row[3] else [],
                    "timestamp": row[4],
                    "message_count": row[5]
                })
            
            logger.debug(f"[DB] Retrieved {len(results)} advisory sessions")
            logger.debug(f"[History] Workspace fetch -> mode=ADVISORY, count={len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"[DB] Failed to retrieve advisory history: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_record(self, record_type: str, record_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific record by ID.
        
        Args:
            record_type: Type of record ('audit', 'redaction', 'advisory')
            record_id: Record ID
            
        Returns:
            Record dictionary or None if not found
        """
        if not self.available:
            return None
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if record_type == "audit":
                cursor.execute("SELECT * FROM audit_history WHERE id = ?", (record_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "filename": row[1],
                        "timestamp": row[2],
                        "issue_count": row[3],
                        "issues": json.loads(row[4]) if row[4] else {},
                        "raw_response": row[5],
                        "mode": row[6],
                        "severity_level": row[7]
                    }
            elif record_type == "redaction":
                cursor.execute("SELECT * FROM redaction_history WHERE id = ?", (record_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "filename": row[1],
                        "timestamp": row[2],
                        "redaction_count": row[3],
                        "entities": json.loads(row[4]) if row[4] else {},
                        "redacted_text": row[5],
                        "redaction_types": row[6]
                    }
            elif record_type == "advisory":
                cursor.execute("SELECT * FROM advisory_sessions WHERE id = ?", (record_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "session_id": row[1],
                        "title": row[2],
                        "messages": json.loads(row[3]) if row[3] else [],
                        "timestamp": row[4],
                        "message_count": row[5]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"[DB] Failed to retrieve record: {str(e)}")
            return None
        finally:
            conn.close()
    
    def delete_record(self, record_type: str, record_id: int) -> bool:
        """Delete a record by ID.
        
        Args:
            record_type: Type of record ('audit', 'redaction', 'advisory')
            record_id: Record ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        if not self.available:
            return False
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if record_type == "audit":
                cursor.execute("DELETE FROM audit_history WHERE id = ?", (record_id,))
            elif record_type == "redaction":
                cursor.execute("DELETE FROM redaction_history WHERE id = ?", (record_id,))
            elif record_type == "advisory":
                cursor.execute("DELETE FROM advisory_sessions WHERE id = ?", (record_id,))
            else:
                return False
            
            conn.commit()
            deleted = cursor.rowcount > 0
            logger.debug(f"[DB] Record deleted: type={record_type}, id={record_id}, success={deleted}")
            return deleted
            
        except Exception as e:
            logger.error(f"[DB] Failed to delete record: {str(e)}")
            return False
        finally:
            conn.close()
    
    def clear_old_records(self, days_old: int = 90) -> int:
        """Delete records older than specified days (maintenance operation).
        
        Args:
            days_old: Delete records older than this many days
            
        Returns:
            Number of records deleted
        """
        if not self.available:
            return 0
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete old audit records
            cursor.execute("""
            DELETE FROM audit_history
            WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days_old,))
            audit_deleted = cursor.rowcount
            
            # Delete old redaction records
            cursor.execute("""
            DELETE FROM redaction_history
            WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days_old,))
            redaction_deleted = cursor.rowcount
            
            # Delete old advisory records
            cursor.execute("""
            DELETE FROM advisory_sessions
            WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days_old,))
            advisory_deleted = cursor.rowcount
            
            conn.commit()
            total = audit_deleted + redaction_deleted + advisory_deleted
            logger.info(f"[DB] Maintenance cleanup: deleted {total} records older than {days_old} days")
            return total
            
        except Exception as e:
            logger.error(f"[DB] Maintenance cleanup failed: {str(e)}")
            return 0
        finally:
            conn.close()


# Global instance
db_service = DatabaseService()
