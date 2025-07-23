"""
NetArchon Configuration Loader

Utilities for loading and managing configuration files.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from ..utils.exceptions import NetArchonError
from ..utils.logger import get_logger


class ConfigLoaderError(NetArchonError):
    """Configuration loader related errors."""
    pass


class ConfigLoader:
    """Loads configuration from various sources and formats."""
    
    def __init__(self, search_paths: Optional[List[str]] = None):
        """Initialize configuration loader.
        
        Args:
            search_paths: List of directories to search for config files
        """
        self.search_paths = search_paths or ["config", ".", os.path.expanduser("~/.netarchon")]
        self.logger = get_logger(f"{__name__}.ConfigLoader")
    
    def load_config(self, 
                   config_name: str,
                   required: bool = False) -> Dict[str, Any]:
        """Load configuration from file.
        
        Args:
            config_name: Name of configuration file (without extension)
            required: Whether the configuration file is required
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigLoaderError: If required config file is not found or invalid
        """
        config_file = self.find_config_file(config_name)
        
        if not config_file:
            if required:
                raise ConfigLoaderError(f"Required configuration file '{config_name}' not found in search paths: {self.search_paths}")
            else:
                self.logger.debug(f"Optional configuration file '{config_name}' not found")
                return {}
        
        return self.load_config_file(config_file)
    
    def find_config_file(self, config_name: str) -> Optional[Path]:
        """Find configuration file in search paths.
        
        Args:
            config_name: Name of configuration file (without extension)
            
        Returns:
            Path to configuration file if found, None otherwise
        """
        # Supported extensions in order of preference
        extensions = ['.yaml', '.yml', '.json']
        
        for search_path in self.search_paths:
            search_dir = Path(search_path)
            if not search_dir.exists():
                continue
                
            for ext in extensions:
                config_file = search_dir / f"{config_name}{ext}"
                if config_file.exists() and config_file.is_file():
                    self.logger.debug(f"Found configuration file: {config_file}")
                    return config_file
        
        return None
    
    def load_config_file(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from specific file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigLoaderError: If file cannot be loaded or parsed
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise ConfigLoaderError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    config = json.load(f)
                else:
                    raise ConfigLoaderError(f"Unsupported configuration file format: {config_path.suffix}")
            
            # Handle empty files
            if config is None:
                config = {}
            
            self.logger.info(f"Loaded configuration from: {config_path}")
            return config
            
        except yaml.YAMLError as e:
            raise ConfigLoaderError(f"Invalid YAML in {config_path}: {str(e)}")
        except json.JSONDecodeError as e:
            raise ConfigLoaderError(f"Invalid JSON in {config_path}: {str(e)}")
        except Exception as e:
            raise ConfigLoaderError(f"Failed to load configuration from {config_path}: {str(e)}")
    
    def save_config_file(self, 
                        config: Dict[str, Any],
                        config_path: Union[str, Path],
                        format: str = "yaml") -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration dictionary to save
            config_path: Path where to save the configuration
            format: File format ('yaml' or 'json')
            
        Raises:
            ConfigLoaderError: If file cannot be saved
        """
        config_path = Path(config_path)
        
        try:
            # Create directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                if format.lower() in ['yaml', 'yml']:
                    yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
                elif format.lower() == 'json':
                    json.dump(config, f, indent=2, sort_keys=False)
                else:
                    raise ConfigLoaderError(f"Unsupported format: {format}")
            
            self.logger.info(f"Saved configuration to: {config_path}")
            
        except Exception as e:
            raise ConfigLoaderError(f"Failed to save configuration to {config_path}: {str(e)}")
    
    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries.
        
        Args:
            *configs: Configuration dictionaries to merge
            
        Returns:
            Merged configuration dictionary
        """
        merged = {}
        
        for config in configs:
            if config:
                merged = self._deep_merge(merged, config)
        
        return merged
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def validate_config_structure(self, 
                                 config: Dict[str, Any],
                                 required_keys: List[str],
                                 optional_keys: Optional[List[str]] = None) -> List[str]:
        """Validate configuration structure.
        
        Args:
            config: Configuration dictionary to validate
            required_keys: List of required keys
            optional_keys: List of optional keys
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        optional_keys = optional_keys or []
        
        # Check for required keys
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required configuration key: {key}")
        
        # Check for unknown keys
        all_valid_keys = set(required_keys + optional_keys)
        for key in config.keys():
            if key not in all_valid_keys:
                errors.append(f"Unknown configuration key: {key}")
        
        return errors
    
    def get_config_template(self) -> Dict[str, Any]:
        """Get a template configuration with default values.
        
        Returns:
            Template configuration dictionary
        """
        return {
            "environment": "development",
            "debug": False,
            "database": {
                "type": "sqlite",
                "host": "localhost",
                "port": 5432,
                "database": "netarchon",
                "username": "",
                "password": "",
                "connection_pool_size": 10,
                "connection_timeout": 30
            },
            "logging": {
                "level": "INFO",
                "format": "structured",
                "file_path": None,
                "max_file_size": 10485760,  # 10MB
                "backup_count": 5,
                "console_output": True
            },
            "ssh": {
                "default_timeout": 30,
                "max_connections": 50,
                "idle_timeout": 300,
                "retry_attempts": 3,
                "connection_pool_enabled": True
            },
            "monitoring": {
                "collection_interval": 60,
                "storage_backend": "memory",
                "retention_days": 30,
                "alert_cooldown_minutes": 15,
                "enable_alerting": True
            },
            "circuit_breaker": {
                "failure_threshold": 5,
                "recovery_timeout": 60,
                "success_threshold": 3,
                "enabled": True
            },
            "retry": {
                "max_attempts": 3,
                "base_delay": 1.0,
                "max_delay": 60.0,
                "strategy": "exponential_backoff",
                "jitter_enabled": True
            },
            "custom_settings": {}
        }
    
    def create_default_config_files(self, config_dir: str = "config") -> List[str]:
        """Create default configuration files.
        
        Args:
            config_dir: Directory to create configuration files in
            
        Returns:
            List of created configuration file paths
        """
        config_path = Path(config_dir)
        config_path.mkdir(parents=True, exist_ok=True)
        
        created_files = []
        
        # Create default.yaml
        default_config = self.get_config_template()
        default_file = config_path / "default.yaml"
        self.save_config_file(default_config, default_file, "yaml")
        created_files.append(str(default_file))
        
        # Create development.yaml
        dev_config = {
            "environment": "development",
            "debug": True,
            "logging": {
                "level": "DEBUG",
                "console_output": True
            },
            "database": {
                "type": "sqlite",
                "database": "netarchon_dev.db"
            }
        }
        dev_file = config_path / "development.yaml"
        self.save_config_file(dev_config, dev_file, "yaml")
        created_files.append(str(dev_file))
        
        # Create production.yaml
        prod_config = {
            "environment": "production",
            "debug": False,
            "logging": {
                "level": "INFO",
                "file_path": "/var/log/netarchon/netarchon.log"
            },
            "database": {
                "type": "postgresql",
                "host": "localhost",
                "database": "netarchon_prod"
            },
            "ssh": {
                "max_connections": 100
            }
        }
        prod_file = config_path / "production.yaml"
        self.save_config_file(prod_config, prod_file, "yaml")
        created_files.append(str(prod_file))
        
        self.logger.info(f"Created default configuration files: {created_files}")
        return created_files


# Global config loader instance
config_loader = ConfigLoader()