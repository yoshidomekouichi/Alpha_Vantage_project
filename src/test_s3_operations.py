#!/usr/bin/env python3
"""
S3 Operations Test

This script tests S3 read/write operations to ensure they work correctly.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import Config
from src.utils.storage import S3Storage
from src.utils.atomic_s3 import AtomicS3
from src.utils.logging_utils import LoggerManager

def main():
    """Main function."""
    # Load configuration
    config = Config()
    
    # Set environment variables for mock mode and S3 saving
    os.environ['MOCK_MODE'] = 'True'
    os.environ['SAVE_TO_S3'] = 'True'
    
    # Set up logger
    logger_manager = LoggerManager(
        "test_s3_operations",
        log_dir=config.log_dir,
        console_level="INFO",
        file_level="DEBUG",
        is_mock=True
    )
    logger = logger_manager.get_logger()
    
    # Set up S3 storage
    s3_storage = S3Storage(config.s3_bucket, config.s3_region)
    s3_storage.set_logger(logger)
    
    # Set up atomic S3 updates
    atomic_s3 = AtomicS3(s3_storage)
    atomic_s3.set_logger(logger)
    
    # Test data
    test_data = {
        "test_id": "s3-test-001",
        "timestamp": datetime.now().isoformat(),
        "values": [1, 2, 3, 4, 5],
        "nested": {
            "key1": "value1",
            "key2": "value2"
        }
    }
    
    # Test key
    test_key = f"test-data/s3-test-{int(time.time())}.json"
    
    logger.info(f"=== Testing S3 operations ===")
    logger.info(f"Test key: {test_key}")
    logger.info(f"Test data: {json.dumps(test_data, indent=2)}")
    
    # Test 1: Direct save and load
    logger.info("=== Test 1: Direct save and load ===")
    
    # Save data
    logger.info(f"Saving data to {test_key}")
    save_result = s3_storage.save_json(test_data, test_key)
    
    if not save_result:
        logger.error("Failed to save data")
        return
    
    # Load data
    logger.info(f"Loading data from {test_key}")
    loaded_data = s3_storage.load_json(test_key)
    
    if loaded_data is None:
        logger.error("Failed to load data")
        return
    
    logger.info(f"Loaded data: {json.dumps(loaded_data, indent=2)}")
    
    # Check if data is correct (ignoring mock flags)
    is_data_correct = True
    for key, value in test_data.items():
        if key not in loaded_data or loaded_data[key] != value:
            is_data_correct = False
            logger.error(f"Data mismatch for key {key}: expected {value}, got {loaded_data.get(key)}")
    
    if is_data_correct:
        logger.info("✅ Test 1 passed: Data saved and loaded correctly")
    else:
        logger.error("❌ Test 1 failed: Data mismatch")
    
    # Test 2: Atomic update and load
    logger.info("=== Test 2: Atomic update and load ===")
    
    # Update test data
    test_data_2 = test_data.copy()
    test_data_2["test_id"] = "s3-test-002"
    test_data_2["timestamp"] = datetime.now().isoformat()
    
    # Atomic update
    logger.info(f"Atomically updating data at {test_key}")
    update_result = atomic_s3.atomic_json_update(test_key, test_data_2)
    
    if not update_result:
        logger.error("Failed to update data atomically")
        return
    
    # Load data
    logger.info(f"Loading data from {test_key}")
    loaded_data_2 = s3_storage.load_json(test_key)
    
    if loaded_data_2 is None:
        logger.error("Failed to load data after atomic update")
        return
    
    logger.info(f"Loaded data after atomic update: {json.dumps(loaded_data_2, indent=2)}")
    
    # Check if data is correct (ignoring mock flags)
    is_data_correct_2 = True
    for key, value in test_data_2.items():
        if key not in loaded_data_2 or loaded_data_2[key] != value:
            is_data_correct_2 = False
            logger.error(f"Data mismatch for key {key}: expected {value}, got {loaded_data_2.get(key)}")
    
    if is_data_correct_2:
        logger.info("✅ Test 2 passed: Data atomically updated and loaded correctly")
    else:
        logger.error("❌ Test 2 failed: Data mismatch after atomic update")
    
    # Test 3: List objects
    logger.info("=== Test 3: List objects ===")
    
    # List objects
    logger.info(f"Listing objects with prefix 'test-data/'")
    objects = s3_storage.list_objects("test-data/")
    
    logger.info(f"Found {len(objects)} objects:")
    for obj in objects:
        logger.info(f"  - {obj}")
    
    # Check if our test object is in the list
    if test_key in objects:
        logger.info(f"✅ Test 3 passed: Test object {test_key} found in the list")
    else:
        logger.error(f"❌ Test 3 failed: Test object {test_key} not found in the list")
    
    # Test 4: Object exists
    logger.info("=== Test 4: Object exists ===")
    
    # Check if object exists
    logger.info(f"Checking if {test_key} exists")
    exists = s3_storage.object_exists(test_key)
    
    if exists:
        logger.info(f"✅ Test 4 passed: Object {test_key} exists")
    else:
        logger.error(f"❌ Test 4 failed: Object {test_key} does not exist")
    
    logger.info("=== All tests completed ===")

if __name__ == "__main__":
    main()
