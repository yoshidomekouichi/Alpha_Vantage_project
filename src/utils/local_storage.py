"""
Local Storage Utility

This module provides a local file system storage implementation that mimics the S3Storage interface.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

class LocalStorage:
    """Local file system storage implementation."""
    
    def __init__(self, base_dir: str):
        """
        Initialize local storage.
        
        Args:
            base_dir: Base directory for local storage
        """
        self.base_dir = Path(base_dir)
        self.logger = logging.getLogger(__name__)
        
        # Create base directory if it doesn't exist
        os.makedirs(self.base_dir, exist_ok=True)
        self.logger.info(f"LocalStorage initialized with base directory: {self.base_dir}")
    
    def set_logger(self, logger):
        """Set a custom logger."""
        self.logger = logger
    
    def put_object(self, key: str, data: Union[str, bytes, Dict], content_type: str = 'application/json') -> bool:
        """
        Store an object in the local file system.
        
        Args:
            key: Object key (path relative to base_dir)
            data: Object data (string, bytes, or dict)
            content_type: Content type (MIME type)
            
        Returns:
            Boolean indicating success
        """
        try:
            # Create full path
            full_path = self.base_dir / key
            
            # Create parent directories if they don't exist
            os.makedirs(full_path.parent, exist_ok=True)
            
            # Convert dict to JSON string if necessary
            if isinstance(data, dict):
                data = json.dumps(data, indent=2)
            
            # Write mode depends on data type
            mode = 'wb' if isinstance(data, bytes) else 'w'
            
            # Write data to file
            with open(full_path, mode) as f:
                f.write(data)
            
            self.logger.debug(f"Successfully wrote object to {full_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write object to {key}: {e}")
            return False
    
    def get_object(self, key: str) -> Optional[Dict]:
        """
        Retrieve an object from the local file system.
        
        Args:
            key: Object key (path relative to base_dir)
            
        Returns:
            Object data as dictionary, or None if not found
        """
        try:
            # Create full path
            full_path = self.base_dir / key
            
            # Check if file exists
            if not full_path.exists():
                self.logger.warning(f"Object not found: {full_path}")
                return None
            
            # Read data from file
            with open(full_path, 'r') as f:
                data = json.load(f)
            
            self.logger.debug(f"Successfully read object from {full_path}")
            return data
        except Exception as e:
            self.logger.error(f"Failed to read object from {key}: {e}")
            return None
    
    def delete_object(self, key: str) -> bool:
        """
        Delete an object from the local file system.
        
        Args:
            key: Object key (path relative to base_dir)
            
        Returns:
            Boolean indicating success
        """
        try:
            # Create full path
            full_path = self.base_dir / key
            
            # Check if file exists
            if not full_path.exists():
                self.logger.warning(f"Object not found for deletion: {full_path}")
                return False
            
            # Delete file
            os.remove(full_path)
            
            self.logger.debug(f"Successfully deleted object: {full_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete object {key}: {e}")
            return False
