"""
Configuration Service
Manages application configuration using JSON file-based storage
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from threading import Lock

from app.core.config.constants import GlobalProcessingConfig, ParseConfig, ChunkConfig, IndexConfig
from app.core.logger import app_logger as logger

class ConfigService:
    """Service for managing application configuration using JSON files"""
    
    def __init__(self):
        self.config_file = Path("app/config/processing_config.json")
        self._config_cache: Optional[GlobalProcessingConfig] = None
        self._cache_lock = Lock()
        
        # Ensure config directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create default config file if it doesn't exist
        if not self.config_file.exists():
            self._create_default_config()
    
    def _create_default_config(self) -> None:
        """Create default configuration file"""
        try:
            default_config = GlobalProcessingConfig()
            self._save_config(default_config)
            logger.info("Created default configuration file")
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
            raise
    
    def _load_config_from_file(self) -> GlobalProcessingConfig:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return GlobalProcessingConfig.from_dict(config_data)
        except FileNotFoundError:
            logger.warning("Configuration file not found, creating default")
            self._create_default_config()
            return GlobalProcessingConfig()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            # Backup corrupted file and create new default
            backup_path = f"{self.config_file}.backup"
            os.rename(self.config_file, backup_path)
            logger.info(f"Backed up corrupted config to {backup_path}")
            self._create_default_config()
            return GlobalProcessingConfig()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _save_config(self, config: GlobalProcessingConfig) -> None:
        """Save configuration to JSON file"""
        try:
            config_data = config.to_dict()
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = f"{self.config_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            os.remove(self.config_file)
            os.rename(temp_file, self.config_file)
            
            # Invalidate cache
            with self._cache_lock:
                self._config_cache = None
                
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            # Clean up temp file if it exists
            if os.path.exists(f"{self.config_file}.tmp"):
                os.remove(f"{self.config_file}.tmp")
            raise
    
    def get_global_config(self) -> GlobalProcessingConfig:
        """Get current global configuration with caching"""
        with self._cache_lock:
            if self._config_cache is None:
                self._config_cache = self._load_config_from_file()
            return self._config_cache
    
    def update_global_config(self, new_config: GlobalProcessingConfig) -> None:
        """Update global configuration"""
        try:
            self._save_config(new_config)
            logger.info("Global configuration updated successfully")
        except Exception as e:
            logger.error(f"Failed to update global configuration: {e}")
            raise
    
    def get_parse_config(self) -> Dict[str, Any]:
        """Get current parse configuration as dictionary"""
        global_config = self.get_global_config()
        return global_config.parse_config.model_dump()
    
    def get_global_parse_config(self) -> ParseConfig:
        """Get current parse configuration as ParseConfig object"""
        global_config = self.get_global_config()
        return global_config.parse_config
    
    def get_chunk_config(self) -> Dict[str, Any]:
        """Get current chunk configuration as dictionary"""
        global_config = self.get_global_config()
        return global_config.chunk_config.model_dump()
    
    def get_global_chunk_config(self) -> ChunkConfig:
        """Get current chunk configuration as ChunkConfig object"""
        global_config = self.get_global_config()
        return global_config.chunk_config
    
    def get_index_config(self) -> Dict[str, Any]:
        """Get current index configuration as dictionary"""
        global_config = self.get_global_config()
        return global_config.index_config.model_dump()
    
    def get_global_index_config(self) -> IndexConfig:
        """Get current index configuration as IndexConfig object"""
        global_config = self.get_global_config()
        return global_config.index_config
    
    def invalidate_cache(self) -> None:
        """Invalidate configuration cache"""
        with self._cache_lock:
            self._config_cache = None
        logger.info("Configuration cache invalidated")
    
    def reload_config(self) -> GlobalProcessingConfig:
        """Force reload configuration from file"""
        self.invalidate_cache()
        return self.get_global_config()
    
    def backup_config(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of current configuration"""
        if backup_path is None:
            backup_path = f"{self.config_file}.backup"
        
        try:
            import shutil
            shutil.copy2(self.config_file, backup_path)
            logger.info(f"Configuration backed up to {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to backup configuration: {e}")
            raise
    
    def restore_config(self, backup_path: str) -> None:
        """Restore configuration from backup"""
        try:
            import shutil
            shutil.copy2(backup_path, self.config_file)
            self.invalidate_cache()
            logger.info(f"Configuration restored from {backup_path}")
        except Exception as e:
            logger.error(f"Failed to restore configuration: {e}")
            raise

# Global instance
config_service = ConfigService() 