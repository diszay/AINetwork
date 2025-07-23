"""
Tests for NetArchon Settings Management
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from src.netarchon.config.settings import (
    SettingsManager, NetArchonSettings, DatabaseConfig, LoggingConfig,
    SSHConfig, MonitoringConfig, CircuitBreakerConfig, RetryConfig,
    SettingsError, ConfigFormat
)
from src.netarchon.config.config_loader import ConfigLoader, ConfigLoaderError
from src.netarchon.utils.exceptions import ValidationError


class TestNetArchonSettings:
    """Test NetArchonSettings dataclass."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = NetArchonSettings()
        
        assert settings.environment == "development"
        assert settings.debug is False
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.logging, LoggingConfig)
        assert isinstance(settings.ssh, SSHConfig)
        assert isinstance(settings.monitoring, MonitoringConfig)
        assert isinstance(settings.circuit_breaker, CircuitBreakerConfig)
        assert isinstance(settings.retry, RetryConfig)
        assert settings.custom_settings == {}
    
    def test_settings_to_dict(self):
        """Test converting settings to dictionary."""
        settings = NetArchonSettings(environment="test", debug=True)
        settings_dict = settings.to_dict()
        
        assert settings_dict["environment"] == "test"
        assert settings_dict["debug"] is True
        assert "database" in settings_dict
        assert "logging" in settings_dict
        assert "ssh" in settings_dict
        assert "monitoring" in settings_dict
        assert "circuit_breaker" in settings_dict
        assert "retry" in settings_dict
        assert "custom_settings" in settings_dict
    
    def test_component_configs(self):
        """Test individual component configurations."""
        # Test DatabaseConfig
        db_config = DatabaseConfig(type="postgresql", host="db.example.com", port=5432)
        assert db_config.type == "postgresql"
        assert db_config.host == "db.example.com"
        assert db_config.port == 5432
        
        # Test LoggingConfig
        log_config = LoggingConfig(level="DEBUG", file_path="/var/log/test.log")
        assert log_config.level == "DEBUG"
        assert log_config.file_path == "/var/log/test.log"
        
        # Test SSHConfig
        ssh_config = SSHConfig(default_timeout=60, max_connections=100)
        assert ssh_config.default_timeout == 60
        assert ssh_config.max_connections == 100
        
        # Test MonitoringConfig
        mon_config = MonitoringConfig(collection_interval=30, enable_alerting=False)
        assert mon_config.collection_interval == 30
        assert mon_config.enable_alerting is False
        
        # Test CircuitBreakerConfig
        cb_config = CircuitBreakerConfig(failure_threshold=10, enabled=False)
        assert cb_config.failure_threshold == 10
        assert cb_config.enabled is False
        
        # Test RetryConfig
        retry_config = RetryConfig(max_attempts=5, strategy="linear_backoff")
        assert retry_config.max_attempts == 5
        assert retry_config.strategy == "linear_backoff"


class TestSettingsManager:
    """Test SettingsManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.settings_manager = SettingsManager(config_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_default_settings(self):
        """Test loading default settings when no config files exist."""
        settings = self.settings_manager.load_settings("test")
        
        assert settings.environment == "test"
        assert settings.debug is False
        assert isinstance(settings.database, DatabaseConfig)
        assert len(self.settings_manager.get_loaded_config_files()) == 0
    
    def test_load_settings_from_yaml(self):
        """Test loading settings from YAML file."""
        # Create test config file
        config_content = """
environment: production
debug: true
database:
  type: postgresql
  host: prod-db.example.com
  port: 5432
logging:
  level: ERROR
  file_path: /var/log/netarchon.log
"""
        config_file = Path(self.temp_dir) / "production.yaml"
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        # Load settings
        settings = self.settings_manager.load_settings("production")
        
        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.database.type == "postgresql"
        assert settings.database.host == "prod-db.example.com"
        assert settings.database.port == 5432
        assert settings.logging.level == "ERROR"
        assert settings.logging.file_path == "/var/log/netarchon.log"
        assert len(self.settings_manager.get_loaded_config_files()) == 1
    
    def test_load_settings_from_json(self):
        """Test loading settings from JSON file."""
        # Create test config file
        config_content = {
            "environment": "staging",
            "debug": False,
            "ssh": {
                "default_timeout": 45,
                "max_connections": 75
            },
            "custom_settings": {
                "feature_flag": True
            }
        }
        
        config_file = Path(self.temp_dir) / "staging.json"
        import json
        with open(config_file, 'w') as f:
            json.dump(config_content, f)
        
        # Load settings
        settings = self.settings_manager.load_settings("staging")
        
        assert settings.environment == "staging"
        assert settings.debug is False
        assert settings.ssh.default_timeout == 45
        assert settings.ssh.max_connections == 75
        assert settings.custom_settings["feature_flag"] is True
    
    def test_settings_precedence(self):
        """Test configuration file precedence (default -> environment -> local)."""
        # Create default config
        default_config = """
environment: development
debug: false
database:
  host: default-host
  port: 5432
ssh:
  default_timeout: 30
"""
        with open(Path(self.temp_dir) / "default.yaml", 'w') as f:
            f.write(default_config)
        
        # Create environment config
        env_config = """
environment: test
debug: true
database:
  host: env-host
ssh:
  max_connections: 100
"""
        with open(Path(self.temp_dir) / "test.yaml", 'w') as f:
            f.write(env_config)
        
        # Create local config
        local_config = """
database:
  port: 3306
"""
        with open(Path(self.temp_dir) / "local.yaml", 'w') as f:
            f.write(local_config)
        
        # Load settings
        settings = self.settings_manager.load_settings("test")
        
        # Check precedence: local > environment > default
        assert settings.environment == "test"  # From environment
        assert settings.debug is True  # From environment (overrides default)
        assert settings.database.host == "env-host"  # From environment
        assert settings.database.port == 3306  # From local (overrides default)
        assert settings.ssh.default_timeout == 30  # From default
        assert settings.ssh.max_connections == 100  # From environment
    
    @patch.dict(os.environ, {
        'NETARCHON_DEBUG': 'true',
        'NETARCHON_DB_HOST': 'env-db-host',
        'NETARCHON_DB_PORT': '3306',
        'NETARCHON_LOG_LEVEL': 'WARNING'
    })
    def test_environment_variable_overrides(self):
        """Test environment variable overrides."""
        settings = self.settings_manager.load_settings("test")
        
        assert settings.debug is True
        assert settings.database.host == "env-db-host"
        assert settings.database.port == 3306
        assert settings.logging.level == "WARNING"
    
    def test_save_settings_yaml(self):
        """Test saving settings to YAML file."""
        settings = NetArchonSettings(environment="test", debug=True)
        settings.database.host = "test-host"
        
        output_file = Path(self.temp_dir) / "output.yaml"
        self.settings_manager.save_settings(settings, str(output_file), ConfigFormat.YAML)
        
        assert output_file.exists()
        
        # Verify content
        import yaml
        with open(output_file, 'r') as f:
            saved_config = yaml.safe_load(f)
        
        assert saved_config["environment"] == "test"
        assert saved_config["debug"] is True
        assert saved_config["database"]["host"] == "test-host"
    
    def test_save_settings_json(self):
        """Test saving settings to JSON file."""
        settings = NetArchonSettings(environment="prod", debug=False)
        
        output_file = Path(self.temp_dir) / "output.json"
        self.settings_manager.save_settings(settings, str(output_file), ConfigFormat.JSON)
        
        assert output_file.exists()
        
        # Verify content
        import json
        with open(output_file, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config["environment"] == "prod"
        assert saved_config["debug"] is False
    
    def test_get_settings_before_load(self):
        """Test getting settings before loading raises error."""
        with pytest.raises(SettingsError, match="Settings not loaded"):
            self.settings_manager.get_settings()
    
    def test_invalid_yaml_file(self):
        """Test loading invalid YAML file raises error."""
        # Create invalid YAML file
        config_file = Path(self.temp_dir) / "invalid.yaml"
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(SettingsError, match="Failed to load settings"):
            self.settings_manager.load_settings("invalid")
    
    def test_settings_validation(self):
        """Test settings validation."""
        # Create config with invalid values
        config_content = """
database:
  port: -1
  connection_pool_size: 0
ssh:
  default_timeout: -5
  max_connections: 0
"""
        config_file = Path(self.temp_dir) / "invalid.yaml"
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        with pytest.raises(SettingsError, match="Settings validation failed"):
            self.settings_manager.load_settings("invalid")


class TestConfigLoader:
    """Test ConfigLoader functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_loader = ConfigLoader(search_paths=[self.temp_dir])
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_yaml_config(self):
        """Test loading YAML configuration."""
        config_content = """
key1: value1
key2:
  nested_key: nested_value
key3: 123
"""
        config_file = Path(self.temp_dir) / "test.yaml"
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        config = self.config_loader.load_config("test")
        
        assert config["key1"] == "value1"
        assert config["key2"]["nested_key"] == "nested_value"
        assert config["key3"] == 123
    
    def test_load_json_config(self):
        """Test loading JSON configuration."""
        config_content = {
            "key1": "value1",
            "key2": {"nested_key": "nested_value"},
            "key3": 123
        }
        
        config_file = Path(self.temp_dir) / "test.json"
        import json
        with open(config_file, 'w') as f:
            json.dump(config_content, f)
        
        config = self.config_loader.load_config("test")
        
        assert config["key1"] == "value1"
        assert config["key2"]["nested_key"] == "nested_value"
        assert config["key3"] == 123
    
    def test_config_file_precedence(self):
        """Test configuration file format precedence (YAML > JSON)."""
        # Create both YAML and JSON files
        yaml_file = Path(self.temp_dir) / "test.yaml"
        with open(yaml_file, 'w') as f:
            f.write("source: yaml\n")
        
        json_file = Path(self.temp_dir) / "test.json"
        import json
        with open(json_file, 'w') as f:
            json.dump({"source": "json"}, f)
        
        config = self.config_loader.load_config("test")
        
        # YAML should take precedence
        assert config["source"] == "yaml"
    
    def test_load_nonexistent_optional_config(self):
        """Test loading non-existent optional configuration."""
        config = self.config_loader.load_config("nonexistent", required=False)
        assert config == {}
    
    def test_load_nonexistent_required_config(self):
        """Test loading non-existent required configuration raises error."""
        with pytest.raises(ConfigLoaderError, match="Required configuration file 'nonexistent' not found"):
            self.config_loader.load_config("nonexistent", required=True)
    
    def test_merge_configs(self):
        """Test merging multiple configurations."""
        config1 = {
            "key1": "value1",
            "nested": {"a": 1, "b": 2}
        }
        
        config2 = {
            "key2": "value2",
            "nested": {"b": 3, "c": 4}
        }
        
        merged = self.config_loader.merge_configs(config1, config2)
        
        assert merged["key1"] == "value1"
        assert merged["key2"] == "value2"
        assert merged["nested"]["a"] == 1
        assert merged["nested"]["b"] == 3  # Override from config2
        assert merged["nested"]["c"] == 4
    
    def test_validate_config_structure(self):
        """Test configuration structure validation."""
        config = {
            "required_key": "value",
            "optional_key": "value",
            "unknown_key": "value"
        }
        
        errors = self.config_loader.validate_config_structure(
            config,
            required_keys=["required_key", "missing_key"],
            optional_keys=["optional_key"]
        )
        
        assert len(errors) == 2
        assert "Missing required configuration key: missing_key" in errors
        assert "Unknown configuration key: unknown_key" in errors
    
    def test_create_default_config_files(self):
        """Test creating default configuration files."""
        created_files = self.config_loader.create_default_config_files(self.temp_dir)
        
        assert len(created_files) == 3
        assert any("default.yaml" in f for f in created_files)
        assert any("development.yaml" in f for f in created_files)
        assert any("production.yaml" in f for f in created_files)
        
        # Verify files exist and contain valid YAML
        for file_path in created_files:
            assert Path(file_path).exists()
            
            import yaml
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
                assert isinstance(config, dict)
                assert len(config) > 0
    
    def test_get_config_template(self):
        """Test getting configuration template."""
        template = self.config_loader.get_config_template()
        
        assert isinstance(template, dict)
        assert "environment" in template
        assert "database" in template
        assert "logging" in template
        assert "ssh" in template
        assert "monitoring" in template
        assert "circuit_breaker" in template
        assert "retry" in template
        
        # Verify nested structure
        assert isinstance(template["database"], dict)
        assert "type" in template["database"]
        assert "host" in template["database"]
    
    def test_save_and_load_roundtrip(self):
        """Test saving and loading configuration roundtrip."""
        original_config = {
            "test_key": "test_value",
            "nested": {
                "number": 42,
                "boolean": True
            }
        }
        
        config_file = Path(self.temp_dir) / "roundtrip.yaml"
        self.config_loader.save_config_file(original_config, config_file, "yaml")
        
        loaded_config = self.config_loader.load_config_file(config_file)
        
        assert loaded_config == original_config