#!/usr/bin/env python3
"""
Check AWS S3 Bucket

This script checks the contents of the S3 bucket using AWS CLI.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import Config

def main():
    """Main function."""
    # Load configuration
    config = Config()
    
    # Get S3 bucket and prefixes
    bucket = config.s3_bucket
    mock_prefix = os.getenv('S3_PREFIX', 'stock-data-mock')
    prod_prefix = os.getenv('S3_PREFIX_PROD', 'stock-data-prod')
    
    print(f"Checking S3 bucket: {bucket}")
    print("=" * 50)
    
    # Check mock data
    print(f"Checking mock data (prefix: {mock_prefix}):")
    try:
        result = subprocess.run(
            ["aws", "s3", "ls", f"s3://{bucket}/{mock_prefix}/", "--recursive"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout:
            print("Mock data found:")
            print(result.stdout)
        else:
            print("No mock data found or error occurred.")
            if result.stderr:
                print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error executing AWS CLI command: {e}")
    
    print("=" * 50)
    
    # Check production data
    print(f"Checking production data (prefix: {prod_prefix}):")
    try:
        result = subprocess.run(
            ["aws", "s3", "ls", f"s3://{bucket}/{prod_prefix}/", "--recursive"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout:
            print("Production data found:")
            print(result.stdout)
        else:
            print("No production data found or error occurred.")
            if result.stderr:
                print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error executing AWS CLI command: {e}")
    
    print("=" * 50)
    
    # Check if AWS CLI is configured correctly
    print("Checking AWS CLI configuration:")
    try:
        result = subprocess.run(
            ["aws", "configure", "list"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            print("AWS CLI configuration:")
            print(result.stdout)
        else:
            print("Error checking AWS CLI configuration.")
            if result.stderr:
                print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error executing AWS CLI command: {e}")

if __name__ == "__main__":
    main()
