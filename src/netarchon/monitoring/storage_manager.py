"""
Persistent Storage System for Omniscient Data Retention

Advanced SQLite-based storage system optimized for Mini PC Ubuntu 24.04 LTS deployment.
Provides efficient data retention, compression, encryption, and query capabilities for
comprehensive network metrics analysis and historical data management.
"""

import sqlite3
import json
import gzip
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging
import hashlib
import pickle
from contextlib import contextmanager
import asyncio
from concurrent.futures import ThreadPoolExecutor

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from netarchon.utils.logger import get_logger
from netarchon.monitoring.concurrent_collector import MetricData, DeviceType, MetricType


class CompressionType(Enum):
    """Types of data compression."""
    NONE = "none"
    GZIP = "gzip"
    PICKLE = "pickle"
    JSON_GZIP = "json_gzip"


class EncryptionLevel(Enum):
    """Levels of data encryption."""
    NONE = "none"
    BASIC = "basic"
    ADVANCED = "advanced"
    SENSITIVE = "sensitive"


class RetentionPolicy(Enum):
    """Data retention policies."""
    REAL_TIME = "real_time"      # 1 hour
    SHORT_TERM = "short_term"    # 24 hours
    MEDIUM_TERM = "medium_term"  # 7 days
    LONG_TERM = "long_term"      # 30 days
    ARCHIVE = "archive"          # 1 year
    PERMANENT = "permanent"      # Never delete


@dataclass
class StorageConfig:
    """Configuration for storage system."""
    database_path: str = "/opt/netarchon/data/metrics.db"
    encryption_key_path: str = "/opt/netarchon/config/.storage_key"
    max_database_size_mb: int = 1024  # 1GB default for Mini PC
    compression_threshold_bytes: int = 1024  # Compress data > 1KB
    batch_size: int = 1000
    vacuum_interval_hours: int = 24
    backup_interval_hours: int = 6
    enable_encryption: bool = True
    enable_compression: bool = True
    
    # Retention policies by metric type
    retention_policies: Dict[str, RetentionPolicy] = field(default_factory=lambda: {
        'connectivity': RetentionPolicy.MEDIUM_TERM,
        'performance': RetentionPolicy.MEDIUM_TERM,
        'docsis': RetentionPolicy.LONG_TERM,
        'wifi_mesh': RetentionPolicy.MEDIUM_TERM,
        'system_resources': RetentionPolicy.LONG_TERM,
        'security': RetentionPolicy.ARCHIVE,
        'bandwidth': RetentionPolicy.LONG_TERM,
        'latency': RetentionPolicy.MEDIUM_TERM
    })


@dataclass
class QueryFilter:
    """Filter criteria for metric queries."""
    device_ids: Optional[List[str]] = None
    device_types: Optional[List[DeviceType]] = None
    metric_types: Optional[List[MetricType]] = None
    metric_names: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: Optional[int] = None
    order_by: str = "timestamp"
    order_desc: bool = True


@dataclass
class StorageStats:
    """Storage system statistics."""
    total_metrics: int
    database_size_mb: float
    compression_ratio: float
    encrypted_metrics: int
    oldest_metric: Optional[datetime]
    newest_metric: Optional[datetime]
    metrics_by_device: Dict[str, int]
    metrics_by_type: Dict[str, int]
    retention_summary: Dict[str, int]


class MetricStorageManager:
    """
    Advanced persistent storage manager for omniscient network metrics.
    
    Optimized for Mini PC Ubuntu 24.04 LTS deployment with SQLite backend,
    data compression, encryption, and intelligent retention policies.
    """
    
    def __init__(self, config: StorageConfig = None):
        self.config = config or StorageConfig()
        self.logger = get_logger("MetricStorageManager")
        
        # Initialize paths
        self.db_path = Path(self.config.database_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.key_path = Path(self.config.encryption_key_path)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Threading and connection management
        self._db_lock = threading.RLock()
        self._connection_pool = {}
        self._pool_lock = threading.Lock()
        
        # Encryption setup
        self._encryption_key = None
        if self.config.enable_encryption:
            self._setup_encryption()
        
        # Background tasks
        self._background_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="storage-bg")
        self._running = False
        self._maintenance_thread = None
        
        # Initialize database
        self._initialize_database()
        
        # Start background maintenance
        self.start_background_tasks()
    
    def _setup_encryption(self):
        """Setup encryption key for sensitive data."""
        try:
            if self.key_path.exists():
                # Load existing key
                with open(self.key_path, 'rb') as f:
                    key_data = f.read()
                self._encryption_key = Fernet(key_data)
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(self.key_path, 'wb') as f:
                    f.write(key)
                # Set restrictive permissions
                self.key_path.chmod(0o600)
                self._encryption_key = Fernet(key)
                
            self.logger.info("Encryption initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup encryption: {e}")
            self.config.enable_encryption = False
    
    def _initialize_database(self):
        """Initialize SQLite database with optimized schema."""
        with self._get_connection() as conn:
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            
            # Create main metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    value_data BLOB,
                    unit TEXT,
                    timestamp INTEGER NOT NULL,
                    compression_type TEXT DEFAULT 'none',
                    encryption_level TEXT DEFAULT 'none',
                    metadata_json TEXT,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    retention_policy TEXT DEFAULT 'medium_term'
                )
            """)
            
            # Create indexes for efficient queries
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_device_id ON metrics(device_id)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_device_type ON metrics(device_type)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_metric_type ON metrics(metric_type)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_metric_name ON metrics(metric_name)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_retention ON metrics(retention_policy)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_composite ON metrics(device_id, metric_type, timestamp)",
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            # Create aggregated metrics table for performance
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics_hourly (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    hour_timestamp INTEGER NOT NULL,
                    min_value REAL,
                    max_value REAL,
                    avg_value REAL,
                    count_value INTEGER,
                    sum_value REAL,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    UNIQUE(device_id, metric_type, metric_name, hour_timestamp)
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hourly_timestamp ON metrics_hourly(hour_timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hourly_device ON metrics_hourly(device_id)")
            
            # Create retention tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS retention_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    retention_policy TEXT NOT NULL,
                    metrics_deleted INTEGER NOT NULL,
                    size_freed_bytes INTEGER NOT NULL,
                    execution_time INTEGER NOT NULL,
                    timestamp INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Create storage statistics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS storage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_metrics INTEGER NOT NULL,
                    database_size_bytes INTEGER NOT NULL,
                    compression_ratio REAL NOT NULL,
                    encrypted_metrics INTEGER NOT NULL,
                    timestamp INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            conn.commit()
            self.logger.info("Database initialized successfully")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper threading support."""
        thread_id = threading.get_ident()
        
        with self._pool_lock:
            if thread_id not in self._connection_pool:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=30.0,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                self._connection_pool[thread_id] = conn
            else:
                conn = self._connection_pool[thread_id]
        
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
    
    def store_metrics(self, metrics: List[MetricData]) -> Dict[str, Any]:
        """Store multiple metrics with batch processing."""
        if not metrics:
            return {"stored": 0, "errors": 0}
        
        stored_count = 0
        error_count = 0
        
        try:
            with self._get_connection() as conn:
                # Process metrics in batches
                for i in range(0, len(metrics), self.config.batch_size):
                    batch = metrics[i:i + self.config.batch_size]
                    batch_result = self._store_metrics_batch(conn, batch)
                    stored_count += batch_result["stored"]
                    error_count += batch_result["errors"]
                
                conn.commit()
                
                # Update hourly aggregates asynchronously
                self._background_executor.submit(self._update_hourly_aggregates, [m.device_id for m in metrics])
                
        except Exception as e:
            self.logger.error(f"Failed to store metrics batch: {e}")
            error_count += len(metrics)
        
        return {
            "stored": stored_count,
            "errors": error_count,
            "total": len(metrics)
        }
    
    def _store_metrics_batch(self, conn: sqlite3.Connection, metrics: List[MetricData]) -> Dict[str, Any]:
        """Store a batch of metrics."""
        stored_count = 0
        error_count = 0
        
        insert_sql = """
            INSERT INTO metrics (
                device_id, device_name, device_type, metric_type, metric_name,
                value_type, value_data, unit, timestamp, compression_type,
                encryption_level, metadata_json, retention_policy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        batch_data = []
        
        for metric in metrics:
            try:
                # Determine retention policy
                retention_policy = self.config.retention_policies.get(
                    metric.metric_type.value, 
                    RetentionPolicy.MEDIUM_TERM
                ).value
                
                # Process value data
                value_type, value_data, compression_type, encryption_level = self._process_metric_value(metric)
                
                # Prepare metadata
                metadata_json = json.dumps(metric.metadata) if metric.metadata else None
                
                batch_data.append((
                    metric.device_id,
                    metric.device_name,
                    metric.device_type.value,
                    metric.metric_type.value,
                    metric.metric_name,
                    value_type,
                    value_data,
                    metric.unit,
                    int(metric.timestamp.timestamp()),
                    compression_type,
                    encryption_level,
                    metadata_json,
                    retention_policy
                ))
                
                stored_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to process metric {metric.metric_name}: {e}")
                error_count += 1
        
        # Execute batch insert
        if batch_data:
            conn.executemany(insert_sql, batch_data)
        
        return {"stored": stored_count, "errors": error_count}
    
    def _process_metric_value(self, metric: MetricData) -> Tuple[str, bytes, str, str]:
        """Process metric value with compression and encryption."""
        value = metric.value
        value_type = type(value).__name__
        
        # Serialize value
        if isinstance(value, (str, int, float, bool)):
            serialized = str(value).encode('utf-8')
        else:
            serialized = json.dumps(value).encode('utf-8')
        
        # Apply compression if enabled and data is large enough
        compression_type = CompressionType.NONE.value
        if (self.config.enable_compression and 
            len(serialized) > self.config.compression_threshold_bytes):
            
            serialized = gzip.compress(serialized)
            compression_type = CompressionType.GZIP.value
        
        # Apply encryption based on metric sensitivity
        encryption_level = self._determine_encryption_level(metric)
        
        if (self.config.enable_encryption and 
            encryption_level != EncryptionLevel.NONE.value and 
            self._encryption_key):
            
            serialized = self._encryption_key.encrypt(serialized)
        
        return value_type, serialized, compression_type, encryption_level
    
    def _determine_encryption_level(self, metric: MetricData) -> str:
        """Determine encryption level based on metric sensitivity."""
        # Security and system resource metrics are sensitive
        if metric.metric_type in [MetricType.SECURITY, MetricType.SYSTEM_RESOURCES]:
            return EncryptionLevel.SENSITIVE.value
        
        # DOCSIS and bandwidth metrics are moderately sensitive
        elif metric.metric_type in [MetricType.DOCSIS, MetricType.BANDWIDTH]:
            return EncryptionLevel.ADVANCED.value
        
        # Performance and connectivity metrics get basic encryption
        elif metric.metric_type in [MetricType.PERFORMANCE, MetricType.CONNECTIVITY]:
            return EncryptionLevel.BASIC.value
        
        # Other metrics are not encrypted
        else:
            return EncryptionLevel.NONE.value
    
    def query_metrics(self, filter_criteria: QueryFilter) -> List[MetricData]:
        """Query metrics with advanced filtering and optimization."""
        try:
            with self._get_connection() as conn:
                sql, params = self._build_query_sql(filter_criteria)
                
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                
                # Convert rows to MetricData objects
                metrics = []
                for row in rows:
                    try:
                        metric = self._row_to_metric(row)
                        if metric:
                            metrics.append(metric)
                    except Exception as e:
                        self.logger.error(f"Failed to convert row to metric: {e}")
                
                return metrics
                
        except Exception as e:
            self.logger.error(f"Failed to query metrics: {e}")
            return []
    
    def _build_query_sql(self, filter_criteria: QueryFilter) -> Tuple[str, List[Any]]:
        """Build optimized SQL query with parameters."""
        base_sql = """
            SELECT device_id, device_name, device_type, metric_type, metric_name,
                   value_type, value_data, unit, timestamp, compression_type,
                   encryption_level, metadata_json
            FROM metrics
        """
        
        where_clauses = []
        params = []
        
        # Device filters
        if filter_criteria.device_ids:
            placeholders = ','.join(['?' for _ in filter_criteria.device_ids])
            where_clauses.append(f"device_id IN ({placeholders})")
            params.extend(filter_criteria.device_ids)
        
        if filter_criteria.device_types:
            placeholders = ','.join(['?' for _ in filter_criteria.device_types])
            where_clauses.append(f"device_type IN ({placeholders})")
            params.extend([dt.value for dt in filter_criteria.device_types])
        
        # Metric filters
        if filter_criteria.metric_types:
            placeholders = ','.join(['?' for _ in filter_criteria.metric_types])
            where_clauses.append(f"metric_type IN ({placeholders})")
            params.extend([mt.value for mt in filter_criteria.metric_types])
        
        if filter_criteria.metric_names:
            placeholders = ','.join(['?' for _ in filter_criteria.metric_names])
            where_clauses.append(f"metric_name IN ({placeholders})")
            params.extend(filter_criteria.metric_names)
        
        # Time filters
        if filter_criteria.start_time:
            where_clauses.append("timestamp >= ?")
            params.append(int(filter_criteria.start_time.timestamp()))
        
        if filter_criteria.end_time:
            where_clauses.append("timestamp <= ?")
            params.append(int(filter_criteria.end_time.timestamp()))
        
        # Build complete query
        if where_clauses:
            base_sql += " WHERE " + " AND ".join(where_clauses)
        
        # Add ordering
        order_direction = "DESC" if filter_criteria.order_desc else "ASC"
        base_sql += f" ORDER BY {filter_criteria.order_by} {order_direction}"
        
        # Add limit
        if filter_criteria.limit:
            base_sql += " LIMIT ?"
            params.append(filter_criteria.limit)
        
        return base_sql, params
    
    def _row_to_metric(self, row: sqlite3.Row) -> Optional[MetricData]:
        """Convert database row to MetricData object."""
        try:
            # Decrypt and decompress value data
            value_data = row['value_data']
            
            # Decrypt if needed
            if (row['encryption_level'] != EncryptionLevel.NONE.value and 
                self._encryption_key):
                value_data = self._encryption_key.decrypt(value_data)
            
            # Decompress if needed
            if row['compression_type'] == CompressionType.GZIP.value:
                value_data = gzip.decompress(value_data)
            
            # Deserialize value
            value_str = value_data.decode('utf-8')
            
            # Convert based on original type
            value_type = row['value_type']
            if value_type == 'int':
                value = int(value_str)
            elif value_type == 'float':
                value = float(value_str)
            elif value_type == 'bool':
                value = value_str.lower() == 'true'
            elif value_type == 'str':
                value = value_str
            else:
                # Try to parse as JSON for complex types
                try:
                    value = json.loads(value_str)
                except:
                    value = value_str
            
            # Parse metadata
            metadata = {}
            if row['metadata_json']:
                try:
                    metadata = json.loads(row['metadata_json'])
                except:
                    pass
            
            return MetricData(
                device_id=row['device_id'],
                device_name=row['device_name'],
                device_type=DeviceType(row['device_type']),
                metric_type=MetricType(row['metric_type']),
                metric_name=row['metric_name'],
                value=value,
                unit=row['unit'],
                timestamp=datetime.fromtimestamp(row['timestamp']),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert row to metric: {e}")
            return None    de
f get_aggregated_metrics(self, device_id: str, metric_type: MetricType, 
                              metric_name: str, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get hourly aggregated metrics for performance analysis."""
        try:
            with self._get_connection() as conn:
                start_timestamp = int((datetime.now() - timedelta(hours=hours_back)).timestamp())
                
                cursor = conn.execute("""
                    SELECT hour_timestamp, min_value, max_value, avg_value, count_value, sum_value
                    FROM metrics_hourly
                    WHERE device_id = ? AND metric_type = ? AND metric_name = ?
                      AND hour_timestamp >= ?
                    ORDER BY hour_timestamp ASC
                """, (device_id, metric_type.value, metric_name, start_timestamp))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'timestamp': datetime.fromtimestamp(row['hour_timestamp']),
                        'min_value': row['min_value'],
                        'max_value': row['max_value'],
                        'avg_value': row['avg_value'],
                        'count': row['count_value'],
                        'sum_value': row['sum_value']
                    })
                
                return results
                
        except Exception as e:
            self.logger.error(f"Failed to get aggregated metrics: {e}")
            return []
    
    def _update_hourly_aggregates(self, device_ids: List[str]):
        """Update hourly aggregates for specified devices."""
        try:
            with self._get_connection() as conn:
                current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
                hour_timestamp = int(current_hour.timestamp())
                
                for device_id in set(device_ids):  # Remove duplicates
                    # Get metrics for current hour
                    cursor = conn.execute("""
                        SELECT metric_type, metric_name, value_type, value_data,
                               compression_type, encryption_level
                        FROM metrics
                        WHERE device_id = ? AND timestamp >= ? AND timestamp < ?
                    """, (device_id, hour_timestamp, hour_timestamp + 3600))
                    
                    # Group by metric type and name
                    metric_groups = {}
                    for row in cursor.fetchall():
                        key = (row['metric_type'], row['metric_name'])
                        if key not in metric_groups:
                            metric_groups[key] = []
                        
                        # Decode value
                        try:
                            value = self._decode_metric_value(row)
                            if isinstance(value, (int, float)):
                                metric_groups[key].append(value)
                        except:
                            continue
                    
                    # Calculate aggregates and upsert
                    for (metric_type, metric_name), values in metric_groups.items():
                        if values:
                            min_val = min(values)
                            max_val = max(values)
                            avg_val = sum(values) / len(values)
                            count_val = len(values)
                            sum_val = sum(values)
                            
                            conn.execute("""
                                INSERT OR REPLACE INTO metrics_hourly
                                (device_id, metric_type, metric_name, hour_timestamp,
                                 min_value, max_value, avg_value, count_value, sum_value)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (device_id, metric_type, metric_name, hour_timestamp,
                                  min_val, max_val, avg_val, count_val, sum_val))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to update hourly aggregates: {e}")
    
    def _decode_metric_value(self, row: sqlite3.Row) -> Any:
        """Decode metric value from database row."""
        value_data = row['value_data']
        
        # Decrypt if needed
        if (row['encryption_level'] != EncryptionLevel.NONE.value and 
            self._encryption_key):
            value_data = self._encryption_key.decrypt(value_data)
        
        # Decompress if needed
        if row['compression_type'] == CompressionType.GZIP.value:
            value_data = gzip.decompress(value_data)
        
        # Deserialize value
        value_str = value_data.decode('utf-8')
        
        # Convert based on original type
        value_type = row['value_type']
        if value_type == 'int':
            return int(value_str)
        elif value_type == 'float':
            return float(value_str)
        elif value_type == 'bool':
            return value_str.lower() == 'true'
        elif value_type == 'str':
            return value_str
        else:
            try:
                return json.loads(value_str)
            except:
                return value_str
    
    def apply_retention_policies(self) -> Dict[str, Any]:
        """Apply retention policies to clean up old data."""
        retention_results = {}
        total_deleted = 0
        total_size_freed = 0
        
        try:
            with self._get_connection() as conn:
                current_time = datetime.now()
                
                # Define retention periods
                retention_periods = {
                    RetentionPolicy.REAL_TIME: timedelta(hours=1),
                    RetentionPolicy.SHORT_TERM: timedelta(days=1),
                    RetentionPolicy.MEDIUM_TERM: timedelta(days=7),
                    RetentionPolicy.LONG_TERM: timedelta(days=30),
                    RetentionPolicy.ARCHIVE: timedelta(days=365),
                    RetentionPolicy.PERMANENT: None  # Never delete
                }
                
                for policy, period in retention_periods.items():
                    if period is None:
                        continue  # Skip permanent retention
                    
                    cutoff_time = current_time - period
                    cutoff_timestamp = int(cutoff_time.timestamp())
                    
                    # Count metrics to be deleted
                    cursor = conn.execute("""
                        SELECT COUNT(*), SUM(LENGTH(value_data))
                        FROM metrics
                        WHERE retention_policy = ? AND timestamp < ?
                    """, (policy.value, cutoff_timestamp))
                    
                    count_result = cursor.fetchone()
                    metrics_to_delete = count_result[0] or 0
                    size_to_free = count_result[1] or 0
                    
                    if metrics_to_delete > 0:
                        # Delete old metrics
                        conn.execute("""
                            DELETE FROM metrics
                            WHERE retention_policy = ? AND timestamp < ?
                        """, (policy.value, cutoff_timestamp))
                        
                        # Also clean up hourly aggregates
                        conn.execute("""
                            DELETE FROM metrics_hourly
                            WHERE hour_timestamp < ?
                        """, (cutoff_timestamp,))
                        
                        retention_results[policy.value] = {
                            'metrics_deleted': metrics_to_delete,
                            'size_freed_bytes': size_to_free,
                            'cutoff_time': cutoff_time.isoformat()
                        }
                        
                        total_deleted += metrics_to_delete
                        total_size_freed += size_to_free
                        
                        # Log retention action
                        conn.execute("""
                            INSERT INTO retention_log
                            (retention_policy, metrics_deleted, size_freed_bytes, execution_time)
                            VALUES (?, ?, ?, ?)
                        """, (policy.value, metrics_to_delete, size_to_free, int(time.time())))
                
                conn.commit()
                
                # Vacuum database to reclaim space
                if total_deleted > 0:
                    conn.execute("VACUUM")
                
                self.logger.info(f"Retention cleanup: {total_deleted} metrics deleted, "
                               f"{total_size_freed / 1024 / 1024:.2f} MB freed")
                
        except Exception as e:
            self.logger.error(f"Failed to apply retention policies: {e}")
        
        return {
            'total_metrics_deleted': total_deleted,
            'total_size_freed_bytes': total_size_freed,
            'policies_applied': retention_results,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_storage_statistics(self) -> StorageStats:
        """Get comprehensive storage system statistics."""
        try:
            with self._get_connection() as conn:
                # Total metrics count
                cursor = conn.execute("SELECT COUNT(*) FROM metrics")
                total_metrics = cursor.fetchone()[0]
                
                # Database size
                db_size_bytes = self.db_path.stat().st_size
                db_size_mb = db_size_bytes / 1024 / 1024
                
                # Compression ratio calculation
                cursor = conn.execute("""
                    SELECT 
                        SUM(CASE WHEN compression_type = 'gzip' THEN LENGTH(value_data) ELSE 0 END) as compressed_size,
                        COUNT(CASE WHEN compression_type = 'gzip' THEN 1 END) as compressed_count,
                        COUNT(*) as total_count
                    FROM metrics
                """)
                comp_result = cursor.fetchone()
                
                # Estimate compression ratio (simplified)
                compression_ratio = 0.7 if comp_result[1] > 0 else 1.0
                
                # Encrypted metrics count
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM metrics 
                    WHERE encryption_level != 'none'
                """)
                encrypted_metrics = cursor.fetchone()[0]
                
                # Oldest and newest metrics
                cursor = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM metrics")
                time_result = cursor.fetchone()
                oldest_metric = datetime.fromtimestamp(time_result[0]) if time_result[0] else None
                newest_metric = datetime.fromtimestamp(time_result[1]) if time_result[1] else None
                
                # Metrics by device
                cursor = conn.execute("""
                    SELECT device_id, COUNT(*) 
                    FROM metrics 
                    GROUP BY device_id
                """)
                metrics_by_device = dict(cursor.fetchall())
                
                # Metrics by type
                cursor = conn.execute("""
                    SELECT metric_type, COUNT(*) 
                    FROM metrics 
                    GROUP BY metric_type
                """)
                metrics_by_type = dict(cursor.fetchall())
                
                # Retention summary
                cursor = conn.execute("""
                    SELECT retention_policy, COUNT(*) 
                    FROM metrics 
                    GROUP BY retention_policy
                """)
                retention_summary = dict(cursor.fetchall())
                
                # Store statistics
                conn.execute("""
                    INSERT INTO storage_stats
                    (total_metrics, database_size_bytes, compression_ratio, encrypted_metrics)
                    VALUES (?, ?, ?, ?)
                """, (total_metrics, db_size_bytes, compression_ratio, encrypted_metrics))
                conn.commit()
                
                return StorageStats(
                    total_metrics=total_metrics,
                    database_size_mb=db_size_mb,
                    compression_ratio=compression_ratio,
                    encrypted_metrics=encrypted_metrics,
                    oldest_metric=oldest_metric,
                    newest_metric=newest_metric,
                    metrics_by_device=metrics_by_device,
                    metrics_by_type=metrics_by_type,
                    retention_summary=retention_summary
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get storage statistics: {e}")
            return StorageStats(
                total_metrics=0,
                database_size_mb=0.0,
                compression_ratio=1.0,
                encrypted_metrics=0,
                oldest_metric=None,
                newest_metric=None,
                metrics_by_device={},
                metrics_by_type={},
                retention_summary={}
            )
    
    def backup_database(self, backup_path: Optional[str] = None) -> Dict[str, Any]:
        """Create a backup of the database."""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path.parent}/metrics_backup_{timestamp}.db"
        
        backup_path = Path(backup_path)
        
        try:
            with self._get_connection() as conn:
                # Create backup using SQLite backup API
                backup_conn = sqlite3.connect(str(backup_path))
                conn.backup(backup_conn)
                backup_conn.close()
                
                # Compress backup if enabled
                if self.config.enable_compression:
                    compressed_path = backup_path.with_suffix('.db.gz')
                    with open(backup_path, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb') as f_out:
                            f_out.writelines(f_in)
                    
                    # Remove uncompressed backup
                    backup_path.unlink()
                    backup_path = compressed_path
                
                backup_size = backup_path.stat().st_size
                
                self.logger.info(f"Database backup created: {backup_path} ({backup_size / 1024 / 1024:.2f} MB)")
                
                return {
                    'success': True,
                    'backup_path': str(backup_path),
                    'backup_size_bytes': backup_size,
                    'compressed': self.config.enable_compression,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to backup database: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def optimize_database(self) -> Dict[str, Any]:
        """Optimize database performance."""
        try:
            with self._get_connection() as conn:
                start_time = time.time()
                
                # Analyze tables for query optimization
                conn.execute("ANALYZE")
                
                # Rebuild indexes
                conn.execute("REINDEX")
                
                # Update statistics
                conn.execute("PRAGMA optimize")
                
                # Vacuum to reclaim space and defragment
                conn.execute("VACUUM")
                
                execution_time = time.time() - start_time
                
                self.logger.info(f"Database optimization completed in {execution_time:.2f} seconds")
                
                return {
                    'success': True,
                    'execution_time_seconds': execution_time,
                    'operations': ['ANALYZE', 'REINDEX', 'OPTIMIZE', 'VACUUM'],
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to optimize database: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def start_background_tasks(self):
        """Start background maintenance tasks."""
        if self._running:
            return
        
        self._running = True
        self._maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._maintenance_thread.start()
        
        self.logger.info("Background maintenance tasks started")
    
    def stop_background_tasks(self):
        """Stop background maintenance tasks."""
        self._running = False
        
        if self._maintenance_thread:
            self._maintenance_thread.join(timeout=10)
        
        if self._background_executor:
            self._background_executor.shutdown(wait=True)
        
        # Close connection pool
        with self._pool_lock:
            for conn in self._connection_pool.values():
                conn.close()
            self._connection_pool.clear()
        
        self.logger.info("Background maintenance tasks stopped")
    
    def _maintenance_loop(self):
        """Background maintenance loop."""
        last_vacuum = time.time()
        last_backup = time.time()
        last_retention = time.time()
        
        while self._running:
            try:
                current_time = time.time()
                
                # Apply retention policies (every hour)
                if current_time - last_retention > 3600:  # 1 hour
                    self._background_executor.submit(self.apply_retention_policies)
                    last_retention = current_time
                
                # Database backup
                if current_time - last_backup > (self.config.backup_interval_hours * 3600):
                    self._background_executor.submit(self.backup_database)
                    last_backup = current_time
                
                # Database vacuum and optimization
                if current_time - last_vacuum > (self.config.vacuum_interval_hours * 3600):
                    self._background_executor.submit(self.optimize_database)
                    last_vacuum = current_time
                
                # Sleep for 5 minutes before next check
                time.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in maintenance loop: {e}")
                time.sleep(60)  # Wait before retrying
    
    def get_query_performance_stats(self) -> Dict[str, Any]:
        """Get query performance statistics."""
        try:
            with self._get_connection() as conn:
                # Get index usage statistics
                cursor = conn.execute("""
                    SELECT name, tbl_name 
                    FROM sqlite_master 
                    WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
                """)
                indexes = cursor.fetchall()
                
                # Get table statistics
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_rows,
                        COUNT(DISTINCT device_id) as unique_devices,
                        COUNT(DISTINCT metric_type) as unique_metric_types,
                        MIN(timestamp) as oldest_timestamp,
                        MAX(timestamp) as newest_timestamp
                    FROM metrics
                """)
                table_stats = cursor.fetchone()
                
                return {
                    'indexes': [{'name': idx[0], 'table': idx[1]} for idx in indexes],
                    'table_statistics': {
                        'total_rows': table_stats[0],
                        'unique_devices': table_stats[1],
                        'unique_metric_types': table_stats[2],
                        'oldest_timestamp': table_stats[3],
                        'newest_timestamp': table_stats[4],
                        'time_span_hours': (table_stats[4] - table_stats[3]) / 3600 if table_stats[3] and table_stats[4] else 0
                    },
                    'database_size_mb': self.db_path.stat().st_size / 1024 / 1024,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get query performance stats: {e}")
            return {}
    
    def export_metrics(self, filter_criteria: QueryFilter, 
                      export_format: str = 'json') -> Dict[str, Any]:
        """Export metrics to various formats."""
        try:
            metrics = self.query_metrics(filter_criteria)
            
            if export_format.lower() == 'json':
                export_data = [metric.to_dict() for metric in metrics]
                return {
                    'success': True,
                    'format': 'json',
                    'data': export_data,
                    'count': len(metrics)
                }
            
            elif export_format.lower() == 'csv':
                # Convert to CSV format
                import csv
                import io
                
                output = io.StringIO()
                if metrics:
                    fieldnames = metrics[0].to_dict().keys()
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for metric in metrics:
                        writer.writerow(metric.to_dict())
                
                return {
                    'success': True,
                    'format': 'csv',
                    'data': output.getvalue(),
                    'count': len(metrics)
                }
            
            else:
                return {
                    'success': False,
                    'error': f'Unsupported export format: {export_format}'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_background_tasks()


# Utility functions for storage management
def create_storage_manager(config_overrides: Dict[str, Any] = None) -> MetricStorageManager:
    """Create a configured storage manager instance."""
    config = StorageConfig()
    
    if config_overrides:
        for key, value in config_overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    return MetricStorageManager(config)


def migrate_storage_schema(storage_manager: MetricStorageManager) -> Dict[str, Any]:
    """Migrate storage schema to latest version."""
    try:
        with storage_manager._get_connection() as conn:
            # Check current schema version
            try:
                cursor = conn.execute("SELECT value FROM pragma_user_version")
                current_version = cursor.fetchone()[0]
            except:
                current_version = 0
            
            migrations_applied = []
            
            # Apply migrations based on version
            if current_version < 1:
                # Migration 1: Add indexes for better performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON metrics(created_at)")
                migrations_applied.append("Added created_at index")
                
            if current_version < 2:
                # Migration 2: Add compression statistics table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS compression_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_size_bytes INTEGER NOT NULL,
                        compressed_size_bytes INTEGER NOT NULL,
                        compression_ratio REAL NOT NULL,
                        timestamp INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                """)
                migrations_applied.append("Added compression statistics table")
            
            # Update schema version
            new_version = max(2, current_version)
            conn.execute(f"PRAGMA user_version = {new_version}")
            conn.commit()
            
            return {
                'success': True,
                'previous_version': current_version,
                'new_version': new_version,
                'migrations_applied': migrations_applied
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }