"""Production Configuration for Screen Translator v2.0"""
import json
import os
from typing import Dict, Any, Optional

class ProductionConfig:
    """Production configuration management"""
    
    def __init__(self):
        self.config = self._load_default_config()
        self._load_environment_overrides()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default production configuration"""
        return {
            'application': {
                'name': 'ScreenTranslator',
                'version': '2.0',
                'environment': 'production'
            },
            'logging': {
                'level': 'INFO',
                'log_directory': 'logs',
                'max_file_size': '10MB',
                'backup_count': 5
            },
            'performance': {
                'profiling_enabled': True,
                'cache_enabled': True,
                'cache_duration': 300,
                'max_memory_mb': 512
            },
            'monitoring': {
                'health_check_interval': 30,
                'metrics_collection': True,
                'alert_on_errors': True
            },
            'database': {
                'connection_timeout': 30,
                'retry_attempts': 3,
                'pool_size': 10
            },
            'components': {
                'max_complexity': 5,
                'error_retry_count': 3,
                'timeout_seconds': 60
            }
        }
    
    def _load_environment_overrides(self):
        """Load configuration overrides from environment variables"""
        
        # Override from environment variables
        if 'ST_LOG_LEVEL' in os.environ:
            self.config['logging']['level'] = os.environ['ST_LOG_LEVEL']
        
        if 'ST_CACHE_ENABLED' in os.environ:
            self.config['performance']['cache_enabled'] = os.environ['ST_CACHE_ENABLED'].lower() == 'true'
        
        if 'ST_PROFILING_ENABLED' in os.environ:
            self.config['performance']['profiling_enabled'] = os.environ['ST_PROFILING_ENABLED'].lower() == 'true'
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot notation path"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """Set configuration value by dot notation path"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save_to_file(self, filepath: str):
        """Save configuration to file"""
        with open(filepath, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def load_from_file(self, filepath: str):
        """Load configuration from file"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                file_config = json.load(f)
                self._merge_config(self.config, file_config)
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Merge configuration dictionaries recursively"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get_component_config(self, component_name: str) -> Dict[str, Any]:
        """Get configuration specific to a component"""
        base_config = self.config['components'].copy()
        
        # Check for component-specific overrides
        component_key = f'component_{component_name.lower()}'
        if component_key in self.config:
            self._merge_config(base_config, self.config[component_key])
        
        return base_config
    
    def validate_config(self) -> tuple[bool, list]:
        """Validate configuration values"""
        errors = []
        
        # Validate required fields
        required_paths = [
            'application.name',
            'logging.level',
            'performance.cache_enabled',
            'components.max_complexity'
        ]
        
        for path in required_paths:
            if self.get(path) is None:
                errors.append(f"Missing required configuration: {path}")
        
        # Validate values
        if self.get('components.max_complexity', 0) > 10:
            errors.append("Component max_complexity should not exceed 10")
        
        if self.get('performance.max_memory_mb', 0) < 128:
            errors.append("Minimum memory requirement is 128MB")
        
        return len(errors) == 0, errors

# Global configuration instance
config = ProductionConfig()

# Load configuration from file if exists
config_file = '/workspace/config/production.json'
if os.path.exists(config_file):
    config.load_from_file(config_file)
