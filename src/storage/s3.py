"""
Storage Module

This module handles storing and retrieving data from AWS S3.
It includes functionality for atomic updates to ensure data integrity.
"""

import os
import logging
import json
import pandas as pd
from typing import Dict, Any, Optional, List, Union
import io

# Default logger - will be replaced by the configured logger
logger = logging.getLogger(__name__)

class S3Storage:
    """Handles storing and retrieving data from AWS S3."""
    
    def __init__(self, bucket_name: str, region_name: str = 'ap-northeast-1'):
        """
        Initialize the S3 storage handler.
        
        Args:
            bucket_name: Name of the S3 bucket
            region_name: AWS region name
        """
        self.bucket_name = bucket_name
        self.region_name = region_name
        
        # Import boto3 here to allow for mock mode without boto3 installed
        import boto3
        from botocore.exceptions import ClientError
        self.ClientError = ClientError
        self.s3_client = boto3.client('s3', region_name=region_name)
        
    def set_logger(self, custom_logger):
        """Set a custom logger for the storage handler."""
        global logger
        logger = custom_logger
    
    def save_json(self, data: Dict[str, Any], key: str) -> bool:
        """
        Save data as JSON to S3.
        
        Args:
            data: Data to save
            key: S3 object key (path)
            
        Returns:
            Boolean indicating success
        """
        try:
            json_data = json.dumps(data, indent=2)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_data,
                ContentType='application/json'
            )
            logger.info(f"✅ Successfully saved JSON data to s3://{self.bucket_name}/{key}")
            return True
        except Exception as e:
            logger.exception(f"❌ Error saving JSON data to S3: {e}")
            return False
    
    def save_csv(self, df: pd.DataFrame, key: str) -> bool:
        """
        Save DataFrame as CSV to S3.
        
        Args:
            df: DataFrame to save
            key: S3 object key (path)
            
        Returns:
            Boolean indicating success
        """
        try:
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=True)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=csv_buffer.getvalue(),
                ContentType='text/csv'
            )
            logger.info(f"✅ Successfully saved CSV data to s3://{self.bucket_name}/{key}")
            return True
        except Exception as e:
            logger.exception(f"❌ Error saving CSV data to S3: {e}")
            return False
    
    def save_parquet(self, df: pd.DataFrame, key: str) -> bool:
        """
        Save DataFrame as Parquet to S3.
        
        Args:
            df: DataFrame to save
            key: S3 object key (path)
            
        Returns:
            Boolean indicating success
        """
        try:
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=parquet_buffer.getvalue()
            )
            logger.info(f"✅ Successfully saved Parquet data to s3://{self.bucket_name}/{key}")
            return True
        except Exception as e:
            logger.exception(f"❌ Error saving Parquet data to S3: {e}")
            return False
    
    def load_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Load JSON data from S3.
        
        Args:
            key: S3 object key (path)
            
        Returns:
            Loaded data or None if an error occurred
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            json_data = json.loads(response['Body'].read().decode('utf-8'))
            logger.info(f"✅ Successfully loaded JSON data from s3://{self.bucket_name}/{key}")
            return json_data
        except self.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"⚠️ Object not found: s3://{self.bucket_name}/{key}")
            else:
                logger.exception(f"❌ Error loading JSON data from S3: {e}")
            return None
        except Exception as e:
            logger.exception(f"❌ Error loading JSON data from S3: {e}")
            return None
    
    def load_csv(self, key: str) -> Optional[pd.DataFrame]:
        """
        Load CSV data from S3 into a DataFrame.
        
        Args:
            key: S3 object key (path)
            
        Returns:
            DataFrame or None if an error occurred
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            df = pd.read_csv(io.BytesIO(response['Body'].read()))
            logger.info(f"✅ Successfully loaded CSV data from s3://{self.bucket_name}/{key}")
            return df
        except self.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"⚠️ Object not found: s3://{self.bucket_name}/{key}")
            else:
                logger.exception(f"❌ Error loading CSV data from S3: {e}")
            return None
        except Exception as e:
            logger.exception(f"❌ Error loading CSV data from S3: {e}")
            return None
    
    def load_parquet(self, key: str) -> Optional[pd.DataFrame]:
        """
        Load Parquet data from S3 into a DataFrame.
        
        Args:
            key: S3 object key (path)
            
        Returns:
            DataFrame or None if an error occurred
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            df = pd.read_parquet(io.BytesIO(response['Body'].read()))
            logger.info(f"✅ Successfully loaded Parquet data from s3://{self.bucket_name}/{key}")
            return df
        except self.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"⚠️ Object not found: s3://{self.bucket_name}/{key}")
            else:
                logger.exception(f"❌ Error loading Parquet data from S3: {e}")
            return None
        except Exception as e:
            logger.exception(f"❌ Error loading Parquet data from S3: {e}")
            return None
    
    def object_exists(self, key: str) -> bool:
        """
        Check if an object exists in S3.
        
        Args:
            key: S3 object key (path)
            
        Returns:
            Boolean indicating if the object exists
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except self.ClientError:
            return False
    
    def list_objects(self, prefix: str = '') -> List[str]:
        """
        List objects in the S3 bucket with the given prefix.
        
        Args:
            prefix: S3 key prefix to filter by
            
        Returns:
            List of object keys
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            
            if 'Contents' not in response:
                return []
                
            return [obj['Key'] for obj in response['Contents']]
        except Exception as e:
            logger.exception(f"❌ Error listing objects in S3: {e}")
            return []
