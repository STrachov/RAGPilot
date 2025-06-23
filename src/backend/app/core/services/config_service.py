import json
import logging
from typing import Dict, Any, Optional
from sqlmodel import Session, select
from datetime import datetime, timezone

from app.core.config.processing_config import GlobalProcessingConfig, DEFAULT_GLOBAL_CONFIG
from app.core.models.settings import Setting
from app.core.db import engine

logger = logging.getLogger(__name__)

class ConfigService:
    """Service for managing global processing configuration"""
    
    GLOBAL_CONFIG_KEY = "global_processing_config"
    
    def __init__(self):
        self._cached_config: Optional[GlobalProcessingConfig] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL
    
    def get_global_config(self) -> GlobalProcessingConfig:
        """
        Get the current global processing configuration
        
        Returns:
            GlobalProcessingConfig: Current global configuration
        """
        # Check cache first
        if self._is_cache_valid():
            return self._cached_config
        
        # Load from database
        with Session(engine) as session:
            try:
                statement = select(Setting).where(Setting.key == self.GLOBAL_CONFIG_KEY)
                result = session.exec(statement).first()
                
                if result and result.value:
                    config_data = json.loads(result.value) if isinstance(result.value, str) else result.value
                    config = GlobalProcessingConfig.from_dict(config_data)
                else:
                    # Use default configuration if not found
                    config = DEFAULT_GLOBAL_CONFIG
                    # Save default to database
                    self._save_config_to_db(config, session)
                
                # Update cache
                self._cached_config = config
                self._cache_timestamp = datetime.now(timezone.utc)
                
                return config
                
            except Exception as e:
                logger.error(f"Error loading global configuration: {e}")
                # Return default configuration on error
                return DEFAULT_GLOBAL_CONFIG
    
    def update_global_config(self, config: GlobalProcessingConfig) -> bool:
        """
        Update the global processing configuration
        
        Args:
            config: New global configuration
            
        Returns:
            bool: True if update was successful
        """
        with Session(engine) as session:
            try:
                # Validate configuration
                config_dict = config.to_dict()
                
                # Save to database
                success = self._save_config_to_db(config, session)
                
                if success:
                    # Update cache
                    self._cached_config = config
                    self._cache_timestamp = datetime.now(timezone.utc)
                    logger.info("Global processing configuration updated successfully")
                
                return success
                
            except Exception as e:
                logger.error(f"Error updating global configuration: {e}")
                return False
    
    def get_chunk_config(self) -> Dict[str, Any]:
        """Get current chunk configuration as dictionary"""
        global_config = self.get_global_config()
        return global_config.chunk_config.dict()
    
    def get_index_config(self) -> Dict[str, Any]:
        """Get current index configuration as dictionary"""
        global_config = self.get_global_config()
        return global_config.index_config.dict()
    
    def invalidate_cache(self):
        """Invalidate the configuration cache"""
        self._cached_config = None
        self._cache_timestamp = None
    
    def _is_cache_valid(self) -> bool:
        """Check if the cached configuration is still valid"""
        if not self._cached_config or not self._cache_timestamp:
            return False
        
        age = datetime.now(timezone.utc) - self._cache_timestamp
        return age.total_seconds() < self._cache_ttl_seconds
    
    def _save_config_to_db(self, config: GlobalProcessingConfig, session: Session) -> bool:
        """Save configuration to database"""
        try:
            # Check if setting exists
            statement = select(Setting).where(Setting.key == self.GLOBAL_CONFIG_KEY)
            existing = session.exec(statement).first()
            
            config_json = json.dumps(config.to_dict())
            
            if existing:
                # Update existing
                existing.value = config_json
                existing.updated_at = datetime.now(timezone.utc)
                session.add(existing)
            else:
                # Create new - need to create a proper Setting instance
                from app.core.models.settings import SettingType
                new_setting = Setting(
                    key=self.GLOBAL_CONFIG_KEY,
                    value=config_json,
                    type=SettingType.SYSTEM_CONFIG,
                    description="Global processing configuration for chunking and indexing",
                    is_secret=False,
                    is_editable=True,
                    created_at=datetime.now(timezone.utc)
                )
                session.add(new_setting)
            
            session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration to database: {e}")
            session.rollback()
            return False

# Global instance
config_service = ConfigService() 