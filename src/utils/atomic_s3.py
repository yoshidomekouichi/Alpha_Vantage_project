"""
Atomic S3 Module

This module provides functionality for atomic updates to S3 objects.
It uses a temporary file + rename pattern to ensure data integrity.
"""

import os
import logging
import time
import uuid
from typing import Dict, Any, Optional, Callable

# Default logger - will be replaced by the configured logger
logger = logging.getLogger(__name__)

class AtomicS3:
    """Handles atomic updates to S3 objects."""
    
    def __init__(self, s3_storage):
        """
        Initialize the atomic S3 handler.
        
        Args:
            s3_storage: An instance of S3Storage
        """
        self.s3 = s3_storage
        self.mock_mode = os.getenv('MOCK_MODE', 'False').lower() == 'true'
        
    def set_logger(self, custom_logger):
        """Set a custom logger for the atomic handler."""
        global logger
        logger = custom_logger
    
    def atomic_update(self, key: str, update_func: Callable, *args, **kwargs) -> bool:
        """
        Perform an atomic update to an S3 object.
        
        Args:
            key: S3 object key (path)
            update_func: Function that performs the update
            *args, **kwargs: Arguments to pass to the update function
            
        Returns:
            Boolean indicating success
        """
        if self.mock_mode:
            logger.info(f"🔍 [MOCK] Performed atomic update to s3://{self.s3.bucket_name}/{key}")
            return True
            
        # Generate a temporary key
        tmp_key = f"{key}.tmp.{uuid.uuid4()}"
        
        try:
            # デバッグ情報を出力
            logger.debug(f"Atomic update: key={key}, tmp_key={tmp_key}")
            
            # Call the update function with the temporary key
            success = update_func(tmp_key, *args, **kwargs)
            
            if not success:
                logger.error(f"❌ Update function failed for temporary object: {tmp_key}")
                return False
            
            # Copy the temporary object to the final key
            copy_source = {'Bucket': str(self.s3.bucket_name), 'Key': str(tmp_key)}
            logger.debug(f"Copying from temporary object: {copy_source}")
            
            self.s3.s3_client.copy_object(
                Bucket=str(self.s3.bucket_name),
                CopySource=copy_source,
                Key=str(key)
            )
            
            # Delete the temporary object
            logger.debug(f"Deleting temporary object: {tmp_key}")
            self.s3.s3_client.delete_object(
                Bucket=str(self.s3.bucket_name),
                Key=str(tmp_key)
            )
            
            logger.info(f"✅ Successfully performed atomic update to s3://{self.s3.bucket_name}/{key}")
            return True
            
        except Exception as e:
            logger.exception(f"❌ Error during atomic update: {e}")
            
            # エラーの詳細情報を出力
            import traceback
            logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
            
            # Try to clean up the temporary object
            try:
                if self.s3.object_exists(tmp_key):
                    logger.debug(f"Cleaning up temporary object after error: {tmp_key}")
                    self.s3.s3_client.delete_object(
                        Bucket=str(self.s3.bucket_name),
                        Key=str(tmp_key)
                    )
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Failed to clean up temporary object: {cleanup_error}")
                
            return False
    
    def atomic_json_update(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Atomically update a JSON object in S3.
        
        Args:
            key: S3 object key (path)
            data: JSON data to save
            
        Returns:
            Boolean indicating success
        """
        # save_jsonメソッドの引数順序が(key, data)なので、dataをkwargsとして渡す
        return self.atomic_update(key, self.s3.save_json, data=data)
    
    def atomic_csv_update(self, key: str, df) -> bool:
        """
        Atomically update a CSV object in S3.
        
        Args:
            key: S3 object key (path)
            df: DataFrame to save
            
        Returns:
            Boolean indicating success
        """
        # save_csvメソッドの引数順序を確認して適切に渡す
        return self.atomic_update(key, self.s3.save_csv, df=df)
    
    def atomic_parquet_update(self, key: str, df) -> bool:
        """
        Atomically update a Parquet object in S3.
        
        Args:
            key: S3 object key (path)
            df: DataFrame to save
            
        Returns:
            Boolean indicating success
        """
        # save_parquetメソッドの引数順序を確認して適切に渡す
        return self.atomic_update(key, self.s3.save_parquet, df=df)
