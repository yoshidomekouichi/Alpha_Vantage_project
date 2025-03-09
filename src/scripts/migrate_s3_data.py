#!/usr/bin/env python3
"""
S3 Data Migration Script

This script migrates data from old S3 path structures to the new standard
hierarchy structure (V2). It can be used to migrate data from Lambda format
or V1 format to V2 format.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.utils.s3_paths import parse_s3_key, convert_key_format, get_s3_key, get_metadata_key
from src.core.logging import LoggerManager

# Set up logger
logger = logging.getLogger(__name__)


def setup_logging(log_level="INFO"):
    """Set up logging configuration."""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logger_manager = LoggerManager(
        "migrate_s3_data",
        log_dir=str(log_dir),
        console_level=log_level,
        file_level="DEBUG"
    )
    
    return logger_manager.get_logger()


def list_s3_objects(s3_client, bucket, prefix=""):
    """
    List all objects in an S3 bucket with the given prefix.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        prefix: S3 key prefix
        
    Returns:
        List of object keys
    """
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        objects = []
        for page in pages:
            if "Contents" in page:
                objects.extend([obj["Key"] for obj in page["Contents"]])
        
        return objects
    except ClientError as e:
        logger.error(f"Error listing objects in S3: {e}")
        return []


def copy_s3_object(s3_client, bucket, source_key, target_key, dry_run=False):
    """
    Copy an S3 object from source key to target key.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        source_key: Source S3 key
        target_key: Target S3 key
        dry_run: If True, only log the operation without executing it
        
    Returns:
        Boolean indicating success
    """
    try:
        if dry_run:
            logger.info(f"[DRY RUN] Would copy s3://{bucket}/{source_key} to s3://{bucket}/{target_key}")
            return True
        
        s3_client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": source_key},
            Key=target_key
        )
        
        logger.info(f"✅ Copied s3://{bucket}/{source_key} to s3://{bucket}/{target_key}")
        return True
    except ClientError as e:
        logger.error(f"❌ Error copying S3 object: {e}")
        return False


def delete_s3_object(s3_client, bucket, key, dry_run=False):
    """
    Delete an S3 object.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        key: S3 key to delete
        dry_run: If True, only log the operation without executing it
        
    Returns:
        Boolean indicating success
    """
    try:
        if dry_run:
            logger.info(f"[DRY RUN] Would delete s3://{bucket}/{key}")
            return True
        
        s3_client.delete_object(Bucket=bucket, Key=key)
        
        logger.info(f"🗑️ Deleted s3://{bucket}/{key}")
        return True
    except ClientError as e:
        logger.error(f"❌ Error deleting S3 object: {e}")
        return False


def migrate_object(s3_client, bucket, source_key, target_version="v2", data_type="raw", 
                  is_mock=None, delete_source=False, dry_run=False):
    """
    Migrate a single S3 object from source key to target version format.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        source_key: Source S3 key
        target_version: Target version format ('v2')
        data_type: Data type for V2 format ('raw' or 'processed')
        is_mock: Whether to use test environment
        delete_source: Whether to delete the source object after migration
        dry_run: If True, only log the operations without executing them
        
    Returns:
        Tuple of (success, target_key)
    """
    try:
        # Parse the source key
        key_info = parse_s3_key(source_key)
        
        if key_info["version"] == "unknown":
            logger.warning(f"⚠️ Unknown key format: {source_key}")
            return False, None
        
        if key_info["version"] == target_version:
            logger.info(f"ℹ️ Key already in {target_version} format: {source_key}")
            return True, source_key
        
        # Convert to target format
        try:
            target_key = convert_key_format(
                source_key, 
                target_version=target_version,
                data_type=data_type,
                is_mock=is_mock
            )
        except ValueError as e:
            logger.error(f"❌ Error converting key format: {e}")
            return False, None
        
        # Copy the object
        if copy_s3_object(s3_client, bucket, source_key, target_key, dry_run):
            # Delete the source object if requested
            if delete_source:
                if delete_s3_object(s3_client, bucket, source_key, dry_run):
                    return True, target_key
                else:
                    logger.warning(f"⚠️ Failed to delete source object: {source_key}")
                    return True, target_key
            else:
                return True, target_key
        else:
            return False, None
    except Exception as e:
        logger.error(f"❌ Unexpected error migrating object: {e}")
        return False, None


def migrate_objects(s3_client, bucket, prefix="", target_version="v2", data_type="raw",
                   is_mock=None, delete_source=False, dry_run=False):
    """
    Migrate all objects in an S3 bucket with the given prefix.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        prefix: S3 key prefix
        target_version: Target version format ('v2')
        data_type: Data type for V2 format ('raw' or 'processed')
        is_mock: Whether to use test environment
        delete_source: Whether to delete the source objects after migration
        dry_run: If True, only log the operations without executing them
        
    Returns:
        Dictionary with migration statistics
    """
    # List all objects
    objects = list_s3_objects(s3_client, bucket, prefix)
    
    if not objects:
        logger.warning(f"⚠️ No objects found with prefix: {prefix}")
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "migrated_keys": []
        }
    
    logger.info(f"Found {len(objects)} objects with prefix: {prefix}")
    
    # Migrate each object
    success_count = 0
    failed_count = 0
    skipped_count = 0
    migrated_keys = []
    
    for i, source_key in enumerate(objects):
        logger.info(f"[{i+1}/{len(objects)}] Processing: {source_key}")
        
        # Parse the source key
        key_info = parse_s3_key(source_key)
        
        if key_info["version"] == "unknown":
            logger.warning(f"⚠️ Unknown key format, skipping: {source_key}")
            skipped_count += 1
            continue
        
        if key_info["version"] == target_version:
            logger.info(f"ℹ️ Key already in {target_version} format, skipping: {source_key}")
            skipped_count += 1
            continue
        
        # Migrate the object
        success, target_key = migrate_object(
            s3_client, bucket, source_key, target_version, data_type,
            is_mock, delete_source, dry_run
        )
        
        if success:
            success_count += 1
            if target_key != source_key:
                migrated_keys.append((source_key, target_key))
        else:
            failed_count += 1
    
    # Return statistics
    return {
        "total": len(objects),
        "success": success_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "migrated_keys": migrated_keys
    }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Migrate S3 data from old path structures to new ones")
    
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--prefix", default="", help="S3 key prefix")
    parser.add_argument("--region", default="ap-northeast-1", help="AWS region")
    parser.add_argument("--target-version", default="v2", choices=["v2"], help="Target version format")
    parser.add_argument("--data-type", default="raw", choices=["raw", "processed"], help="Data type for V2 format")
    parser.add_argument("--environment", default=None, choices=["test", "prod"], help="Environment (test/prod)")
    parser.add_argument("--delete-source", action="store_true", help="Delete source objects after migration")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't actually migrate)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Log level")
    
    args = parser.parse_args()
    
    # Set up logging
    global logger
    logger = setup_logging(args.log_level)
    
    # Log arguments
    logger.info("=" * 80)
    logger.info("S3 Data Migration")
    logger.info("=" * 80)
    logger.info(f"Bucket: {args.bucket}")
    logger.info(f"Prefix: {args.prefix}")
    logger.info(f"Region: {args.region}")
    logger.info(f"Target Version: {args.target_version}")
    logger.info(f"Data Type: {args.data_type}")
    logger.info(f"Environment: {args.environment}")
    logger.info(f"Delete Source: {args.delete_source}")
    logger.info(f"Dry Run: {args.dry_run}")
    logger.info(f"Log Level: {args.log_level}")
    logger.info("=" * 80)
    
    # Initialize S3 client
    s3_client = boto3.client("s3", region_name=args.region)
    
    # Determine if mock mode
    is_mock = None
    if args.environment:
        is_mock = args.environment == "test"
    
    # Migrate objects
    start_time = datetime.now()
    
    stats = migrate_objects(
        s3_client, args.bucket, args.prefix, args.target_version,
        args.data_type, is_mock, args.delete_source, args.dry_run
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Log statistics
    logger.info("=" * 80)
    logger.info("Migration Statistics")
    logger.info("=" * 80)
    logger.info(f"Total Objects: {stats['total']}")
    logger.info(f"Successfully Migrated: {stats['success']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Skipped: {stats['skipped']}")
    logger.info(f"Duration: {duration:.2f} seconds")
    
    if stats['migrated_keys']:
        logger.info("=" * 80)
        logger.info("Migrated Keys (first 10)")
        logger.info("=" * 80)
        for i, (source, target) in enumerate(stats['migrated_keys'][:10]):
            logger.info(f"{i+1}. {source} -> {target}")
        
        if len(stats['migrated_keys']) > 10:
            logger.info(f"... and {len(stats['migrated_keys']) - 10} more")
    
    logger.info("=" * 80)
    
    # Return exit code
    return 0 if stats['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
