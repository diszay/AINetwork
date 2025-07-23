"""
NetArchon Settings Management

Application configuration and settings management with YAML/JSON support.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum

from ..utils.exceptions import NetArchonError, ValidationError
from ..utils.logger import get_logger


class ConfigFormat(Enum):
    """Configuration file formats."""
    YAML = "yaml"
    JSON = "json"


class SettingsError(NetArchonError):
    """Settings management related errors."""
    pass


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    type: str = "sqlite"
    host: str = "localhost"
    port: int = 5432
    database: str = "netarchon"
    username: str = ""
    password: str = ""
    connection_pool_size: int = 10
    connection_timeout: int = 30


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    format: str = "structured"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True


@dataclass
class SSHConfig:
    """SSH connection configuration settings."""
    default_timeout: int = 30
    max_connections: int = 50
    idle_timeout: int = 300
    retry_attempts: int = 3
    connection_pool_enabled: bool = True


@dataclass
class MonitoringConfig:
    """Monitoring configuration settings."""
    collection_interval: int = 60  # seconds
    storage_backend: str = "memory"
    retention_days: int = 30
    alert_cooldown_minutes: int = 15
    enable_alerting: bool = True


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration settings."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 3
    enabled: bool = True


@dataclass
class RetryConfig:
    """Retry configuration settings."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: str = "exponential_backoff"
    jitter_enabled: bool = True


@dataclass
class NetArchonSettings:
    """Main NetArchon application settings."""
    environment: str = "development"
    debug: bool = False
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ssh: SSHConfig = field(default_factory=SSHConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    
    # Additional settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "database": {
                "type": self.database.type,
                "host": self.database.host,
                "port": self.database.port,
                "database": self.database.database,
                "username": self.database.username,
                "password": self.database.password,
                "connection_pool_size": self.database.connection_pool_size,
                "connection_timeout": self.database.connection_timeout
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file_path": self.logging.file_path,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count,
                "console_output": self.logging.console_output
            },
            "ssh": {
                "default_timeout": self.ssh.default_timeout,
                "max_connections": self.ssh.max_connections,
                "idle_timeout": self.ssh.idle_timeout,
                "retry_attempts": self.ssh.retry_attempts,
                "connection_pool_enabled": self.ssh.connection_pool_enabled
            },
            "monitoring": {
                "collection_interval": self.monitoring.collection_interval,
                "storage_backend": self.monitoring.storage_backend,
                "retention_days": self.monitoring.retention_days,
                "alert_cooldown_minutes": self.monitoring.alert_cooldown_minutes,
                "enable_alerting": self.monitoring.enable_alerting
            },
            "circuit_breaker": {
                "failure_threshold": self.circuit_breaker.failure_threshold,
                "recovery_timeout": self.circuit_breaker.recovery_timeout,
                "success_threshold": self.circuit_breaker.success_threshold,
                "enabled": self.circuit_breaker.enabled
            },
            "retry": {
                "max_attempts": self.retry.max_attempts,
                "base_delay": self.retry.base_delay,
                "max_delay": self.retry.max_delay,
                "strategy": self.retry.strategy,
                "jitter_enabled": self.retry.jitter_enabled
            },
            "custom_settings": self.custom_settings
        }


class SettingsManager:
    """Manages application settings and configuration."""
    
    def __init__(self, config_dir: str = "config"):
        """Initialize settings manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.logger = get_logger(f"{__name__}.SettingsManager")
        self._settings: Optional[NetArchonSettings] = None
        self._config_files_loaded: List[str] = []
    
    def load_settings(self, 
                     environment: str = "development",
                     config_file: Optional[str] = None) -> NetArchonSettings:
        """Load settings from configuration files.
        
        Args:
            environment: Environment name (development, production, etc.)
            config_file: Specific config file to load (optional)
            
        Returns:
            NetArchonSettings object
            
        Raises:
            SettingsError: If configuration loading fails
        """
        self.logger.info(f"Loading settings for environment: {environment}")
        
        try:
            # Start with default settings
            settings = NetArchonSettings(environment=environment)
            
            # Load configuration files in order of precedence
            config_files = self._get_config_files(environment, config_file)
            
            for config_path in config_files:
                if config_path.exists():
                    self.logger.info(f"Loading configuration from: {config_path}")
                    file_settings = self._load_config_file(config_path)
                    settings = self._merge_settings(settings, file_settings)
                    self._config_files_loaded.append(str(config_path))
                else:
                    self.logger.debug(f"Configuration file not found: {config_path}")
            
            # Apply environment variable overrides
            settings = self._apply_env_overrides(settings)
            
            # Validate settings
            self._validate_settings(settings)
            
            self._settings = settings
            self.logger.info(f"Settings loaded successfully for environment: {environment}")
            
            return settings
            
        except Exception as e:
            error_msg = f"Failed to load settings: {str(e)}"
            self.logger.error(error_msg)
            raise SettingsError(error_msg) from e
    
    def get_settings(self) -> NetArchonSettings:
        """Get current settings.
        
        Returns:
            Current NetArchonSettings object
            
        Raises:
            SettingsError: If settings haven't been loaded
        """
        if self._settings is None:
            raise SettingsError("Settings not loaded. Call load_settings() first.")
        return self._settings
    
    def save_settings(self, 
                     settings: NetArchonSettings,
                     file_path: str,
                     format: ConfigFormat = ConfigFormat.YAML) -> None:
        """Save settings to a configuration file.
        
        Args:
            settings: Settings to save
            file_path: Path to save the configuration file
            format: Configuration file format
            
        Raises:
            SettingsError: If saving fails
        """
        try:
            config_path = Path(file_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            settings_dict = settings.to_dict()
            
            if format == ConfigFormat.YAML:
                with open(config_path, 'w') as f:
                    yaml.dump(settings_dict, f, default_flow_style=False, indent=2)
            elif format == ConfigFormat.JSON:
                with open(config_path, 'w') as f:
                    json.dump(settings_dict, f, indent=2)
            
            self.logger.info(f"Settings saved to: {config_path}")
            
        except Exception as e:
            error_msg = f"Failed to save settings to {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise SettingsError(error_msg) from e
    
    def _get_config_files(self, 
                         environment: str,
                         config_file: Optional[str] = None) -> List[Path]:
        """Get list of configuration files to load in order of precedence.
        
        Args:
            environment: Environment name
            config_file: Specific config file
            
        Returns:
            List of configuration file paths
        """
        config_files = []
        
        if config_file:
            # Load specific file if provided
            config_files.append(Path(config_file))
        else:
            # Load in order of precedence: default -> environment -> local
            config_files.extend([
                self.config_dir / "default.yaml",
                self.config_dir / "default.json",
                self.config_dir / f"{environment}.yaml",
                self.config_dir / f"{environment}.json",
                self.config_dir / "local.yaml",
                self.config_dir / "local.json"
            ])
        
        return config_files
    
    def _load_config_file(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from a file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            SettingsError: If file loading fails
        """
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif config_path.suffix.lower() == '.json':
                    return json.load(f) or {}
                else:
                    raise SettingsError(f"Unsupported configuration file format: {config_path.suffix}")
                    
        except yaml.YAMLError as e:
            raise SettingsError(f"Invalid YAML in {config_path}: {str(e)}")
        except json.JSONDecodeError as e:
            raise SettingsError(f"Invalid JSON in {config_path}: {str(e)}")
        except Exception as e:
            raise SettingsError(f"Failed to load {config_path}: {str(e)}")
    
    def _merge_settings(self, 
                       base_settings: NetArchonSettings,
                       override_dict: Dict[str, Any]) -> NetArchonSettings:
        """Merge configuration dictionary into settings object.
        
        Args:
            base_settings: Base settings object
            override_dict: Configuration dictionary to merge
            
        Returns:
            Merged settings object
        """
        # Create a copy of base settings
        merged = NetArchonSettings(
            environment=override_dict.get("environment", base_settings.environment),
            debug=override_dict.get("debug", base_settings.debug)
        )
        
        # Merge database settings
        if "database" in override_dict:
            db_config = override_dict["database"]
            merged.database = DatabaseConfig(
                type=db_config.get("type", base_settings.database.type),
                host=db_config.get("host", base_settings.database.host),
                port=db_config.get("port", base_settings.database.port),
                database=db_config.get("database", base_settings.database.database),
                username=db_config.get("username", base_settings.database.username),
                password=db_config.get("password", base_settings.database.password),
                connection_pool_size=db_config.get("connection_pool_size", base_settings.database.connection_pool_size),
                connection_timeout=db_config.get("connection_timeout", base_settings.database.connection_timeout)
            )
        else:
            merged.database = base_settings.database
        
        # Merge logging settings
        if "logging" in override_dict:
            log_config = override_dict["logging"]
            merged.logging = LoggingConfig(
                level=log_config.get("level", base_settings.logging.level),
                format=log_config.get("format", base_settings.logging.format),
                file_path=log_config.get("file_path", base_settings.logging.file_path),
                max_file_size=log_config.get("max_file_size", base_settings.logging.max_file_size),
                backup_count=log_config.get("backup_count", base_settings.logging.backup_count),
                console_output=log_config.get("console_output", base_settings.logging.console_output)
            )
        else:
            merged.logging = base_settings.logging
        
        # Merge SSH settings
        if "ssh" in override_dict:
            ssh_config = override_dict["ssh"]
            merged.ssh = SSHConfig(
                default_timeout=ssh_config.get("default_timeout", base_settings.ssh.default_timeout),
                max_connections=ssh_config.get("max_connections", base_settings.ssh.max_connections),
                idle_timeout=ssh_config.get("idle_timeout", base_settings.ssh.idle_timeout),
                retry_attempts=ssh_config.get("retry_attempts", base_settings.ssh.retry_attempts),
                connection_pool_enabled=ssh_config.get("connection_pool_enabled", base_settings.ssh.connection_pool_enabled)
            )
        else:
            merged.ssh = base_settings.ssh
        
        # Merge monitoring settings
        if "monitoring" in override_dict:
            mon_config = override_dict["monitoring"]
            merged.monitoring = MonitoringConfig(
                collection_interval=mon_config.get("collection_interval", base_settings.monitoring.collection_interval),
                storage_backend=mon_config.get("storage_backend", base_settings.monitoring.storage_backend),
                retention_days=mon_config.get("retention_days", base_settings.monitoring.retention_days),
                alert_cooldown_minutes=mon_config.get("alert_cooldown_minutes", base_settings.monitoring.alert_cooldown_minutes),
                enable_alerting=mon_config.get("enable_alerting", base_settings.monitoring.enable_alerting)
            )
        else:
            merged.monitoring = base_settings.monitoring
        
        # Merge circuit breaker settings
        if "circuit_breaker" in override_dict:
            cb_config = override_dict["circuit_breaker"]
            merged.circuit_breaker = CircuitBreakerConfig(
                failure_threshold=cb_config.get("failure_threshold", base_settings.circuit_breaker.failure_threshold),
                recovery_timeout=cb_config.get("recovery_timeout", base_settings.circuit_breaker.recovery_timeout),
                success_threshold=cb_config.get("success_threshold", base_settings.circuit_breaker.success_threshold),
                enabled=cb_config.get("enabled", base_settings.circuit_breaker.enabled)
            )
        else:
            merged.circuit_breaker = base_settings.circuit_breaker
        
        # Merge retry settings
        if "retry" in override_dict:
            retry_config = override_dict["retry"]
            merged.retry = RetryConfig(
                max_attempts=retry_config.get("max_attempts", base_settings.retry.max_attempts),
                base_delay=retry_config.get("base_delay", base_settings.retry.base_delay),
                max_delay=retry_config.get("max_delay", base_settings.retry.max_delay),
                strategy=retry_config.get("strategy", base_settings.retry.strategy),
                jitter_enabled=retry_config.get("jitter_enabled", base_settings.retry.jitter_enabled)
            )
        else:
            merged.retry = base_settings.retry
        
        # Merge custom settings
        merged.custom_settings = {**base_settings.custom_settings, **override_dict.get("custom_settings", {})}
        
        return merged
    
    def _apply_env_overrides(self, settings: NetArchonSettings) -> NetArchonSettings:
        """Apply environment variable overrides to settings.
        
        Args:
            settings: Settings to override
            
        Returns:
            Settings with environment variable overrides applied
        """
        # Environment variable mapping
        env_mappings = {
            "NETARCHON_DEBUG": ("debug", bool),
            "NETARCHON_DB_HOST": ("database.host", str),
            "NETARCHON_DB_PORT": ("database.port", int),
            "NETARCHON_DB_NAME": ("database.database", str),
            "NETARCHON_DB_USER": ("database.username", str),
            "NETARCHON_DB_PASSWORD": ("database.password", str),
            "NETARCHON_LOG_LEVEL": ("logging.level", str),
            "NETARCHON_LOG_FILE": ("logging.file_path", str),
            "NETARCHON_SSH_TIMEOUT": ("ssh.default_timeout", int),
            "NETARCHON_SSH_MAX_CONNECTIONS": ("ssh.max_connections", int)
        }
        
        for env_var, (setting_path, setting_type) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Convert environment variable to appropriate type
                    if setting_type == bool:
                        converted_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif setting_type == int:
                        converted_value = int(env_value)
                    else:
                        converted_value = env_value
                    
                    # Apply the override
                    self._set_nested_setting(settings, setting_path, converted_value)
                    self.logger.debug(f"Applied environment override: {env_var} -> {setting_path}")
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Invalid environment variable {env_var}: {env_value} ({str(e)})")
        
        return settings
    
    def _set_nested_setting(self, settings: NetArchonSettings, path: str, value: Any) -> None:
        """Set a nested setting value using dot notation.
        
        Args:
            settings: Settings object to modify
            path: Dot-separated path to the setting
            value: Value to set
        """
        parts = path.split('.')
        obj = settings
        
        # Navigate to the parent object
        for part in parts[:-1]:
            obj = getattr(obj, part)
        
        # Set the final value
        setattr(obj, parts[-1], value)
    
    def _validate_settings(self, settings: NetArchonSettings) -> None:
        """Validate settings for consistency and correctness.
        
        Args:
            settings: Settings to validate
            
        Raises:
            ValidationError: If settings are invalid
        """
        errors = []
        
        # Validate database settings
        if settings.database.port <= 0 or settings.database.port > 65535:
            errors.append("Database port must be between 1 and 65535")
        
        if settings.database.connection_pool_size <= 0:
            errors.append("Database connection pool size must be positive")
        
        # Validate SSH settings
        if settings.ssh.default_timeout <= 0:
            errors.append("SSH timeout must be positive")
        
        if settings.ssh.max_connections <= 0:
            errors.append("SSH max connections must be positive")
        
        # Validate monitoring settings
        if settings.monitoring.collection_interval <= 0:
            errors.append("Monitoring collection interval must be positive")
        
        # Validate circuit breaker settings
        if settings.circuit_breaker.failure_threshold <= 0:
            errors.append("Circuit breaker failure threshold must be positive")
        
        # Validate retry settings
        if settings.retry.max_attempts <= 0:
            errors.append("Retry max attempts must be positive")
        
        if settings.retry.base_delay <= 0:
            errors.append("Retry base delay must be positive")
        
        if errors:
            raise ValidationError("Settings validation failed: " + "; ".join(errors))
    
    def get_loaded_config_files(self) -> List[str]:
        """Get list of configuration files that were loaded.
        
        Returns:
            List of configuration file paths
        """
        return self._config_files_loaded.copy()


# Global settings manager instance
settings_manager = SettingsManager()