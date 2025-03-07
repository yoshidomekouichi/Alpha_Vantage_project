#!/usr/bin/env python3
"""
Check S3 Bucket Directly

This script checks the contents of the S3 bucket using boto3 directly.
"""

import os
import sys
import json
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
    
    # Import boto3 here to avoid import errors if not installed
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        print("Error: boto3 is not installed. Please install it with 'pip install boto3'.")
        return
    
    # Create S3 client
    try:
        s3_client = boto3.client('s3', region_name=config.s3_region)
    except Exception as e:
        print(f"Error creating S3 client: {e}")
        return
    
    # Check if bucket exists
    try:
        s3_client.head_bucket(Bucket=bucket)
        print(f"Bucket {bucket} exists and is accessible.")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"Bucket {bucket} does not exist.")
        elif error_code == '403':
            print(f"Access to bucket {bucket} is forbidden. Check your credentials.")
        else:
            print(f"Error accessing bucket {bucket}: {e}")
        return
    except Exception as e:
        print(f"Error checking bucket {bucket}: {e}")
        return
    
    # Check mock data
    print(f"\nChecking mock data (prefix: {mock_prefix}):")
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=mock_prefix)
        if 'Contents' in response:
            objects = response['Contents']
            print(f"Found {len(objects)} objects:")
            for obj in objects:
                print(f"  - {obj['Key']} ({obj['Size']} bytes, last modified: {obj['LastModified']})")
                
                # If it's a JSON file, try to get its contents
                if obj['Key'].endswith('.json'):
                    try:
                        obj_response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                        obj_data = json.loads(obj_response['Body'].read().decode('utf-8'))
                        print(f"    Content: {json.dumps(obj_data, indent=2)[:200]}...")
                    except Exception as e:
                        print(f"    Error reading object: {e}")
        else:
            print("No mock data found.")
    except Exception as e:
        print(f"Error listing mock data: {e}")
    
    # Check production data
    print(f"\nChecking production data (prefix: {prod_prefix}):")
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prod_prefix)
        if 'Contents' in response:
            objects = response['Contents']
            print(f"Found {len(objects)} objects:")
            for obj in objects:
                print(f"  - {obj['Key']} ({obj['Size']} bytes, last modified: {obj['LastModified']})")
                
                # If it's a JSON file, try to get its contents
                if obj['Key'].endswith('.json'):
                    try:
                        obj_response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                        obj_data = json.loads(obj_response['Body'].read().decode('utf-8'))
                        print(f"    Content: {json.dumps(obj_data, indent=2)[:200]}...")
                    except Exception as e:
                        print(f"    Error reading object: {e}")
        else:
            print("No production data found.")
    except Exception as e:
        print(f"Error listing production data: {e}")
    
    print("\n" + "=" * 50)
    print("S3 check completed.")

if __name__ == "__main__":
    main()
