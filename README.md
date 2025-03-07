# Alpha Vantage Stock Data Pipeline

This project fetches stock price data from the Alpha Vantage API and stores it in AWS S3. It is designed to run as a scheduled batch job to maintain an up-to-date database of stock prices.

## Features

- Fetch daily stock data from Alpha Vantage API
- Fetch historical (bulk) stock data
- Store data in AWS S3 with atomic updates
- Data validation and quality checks
- Configurable logging
- Email and Slack notifications
- Mock mode for testing without API calls
- Debug mode for detailed logging

## Project Structure

```
Alpha_Vantage_project/
├── src/                     # Source code
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   ├── fetch_daily.py       # Daily batch script entry point
│   ├── fetch_bulk.py        # Historical data fetch script entry point
│   ├── api/                 # API client modules
│   │   ├── __init__.py
│   │   └── alpha_vantage/   # Alpha Vantage specific API
│   │       ├── __init__.py
│   │       ├── client.py    # Alpha Vantage API client
│   │       └── models.py    # Data models for API responses
│   ├── core/                # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration utilities
│   │   └── logging.py       # Logging setup
│   ├── data/                # Data processing modules
│   ├── fetch/               # Data fetching modules
│   │   ├── fetch_daily.py   # Daily data fetching implementation
│   │   ├── fetch_history.py # Historical data fetching
│   │   ├── send_email.py    # Email notification for fetch results
│   │   ├── test_fetch.py    # Test utilities for fetching
│   │   └── utils.py         # Utilities for fetch operations
│   ├── notifications/       # Notification modules
│   │   ├── __init__.py
│   │   └── alerts.py        # Alert system implementation
│   ├── scripts/             # Executable scripts
│   │   ├── __init__.py
│   │   ├── fetch_bulk.py    # Script for bulk data fetching
│   │   └── fetch_daily.py   # Script for daily data fetching
│   ├── storage/             # Storage modules
│   │   ├── __init__.py
│   │   ├── atomic.py        # Atomic file operations
│   │   └── s3.py            # S3 storage operations
│   └── utils/               # Utility modules
│       ├── alerts.py        # Alert utilities
│       ├── api_client.py    # Generic API client utilities
│       ├── atomic_s3.py     # Atomic S3 updates
│       ├── data_processing.py # Data validation and transformation
│       ├── logging_utils.py # Logging utilities
│       └── storage.py       # Storage operation utilities
├── configs/                 # Configuration files
│   └── secrets/             # Secret configuration (gitignored)
├── db/                      # Database related files
│   └── docker-compose.yml   # Docker setup for database
├── logs/                    # Log files
├── tests/                   # Test files
│   ├── test_data/           # Test data
│   ├── test_log/            # Test logs
│   └── test_src/            # Test source code
├── Training/                # Training and documentation
├── .env                     # Environment variables (create from .env.sample)
├── .env.sample              # Sample environment variables
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Setup

### Prerequisites

- Python 3.8+
- AWS account with S3 access
- Alpha Vantage API key

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Alpha_Vantage_project
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file from the sample:
   ```bash
   cp .env.sample .env
   ```

4. Edit the `.env` file with your configuration:
   - Add your Alpha Vantage API key
   - Configure your AWS S3 bucket
   - Set up email/Slack notifications if desired

### AWS Configuration

1. Install AWS CLI:
   ```bash
   # macOS
   brew install awscli
   
   # Other platforms
   # Follow instructions at https://aws.amazon.com/cli/
   ```

2. Configure AWS CLI with your credentials:
   ```bash
   aws configure
   ```
   You'll need to provide:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (e.g., ap-northeast-1)
   - Default output format (json recommended)

3. Create an S3 bucket for storing data:
   ```bash
   aws s3api create-bucket \
     --bucket your-bucket-name \
     --region ap-northeast-1 \
     --create-bucket-configuration LocationConstraint=ap-northeast-1
   ```
   Replace `your-bucket-name` with a globally unique bucket name.

4. Configure bucket access permissions:
   ```bash
   # Disable public access blocking (if needed)
   aws s3api put-public-access-block \
     --bucket your-bucket-name \
     --public-access-block-configuration \
     BlockPublicAcls=false,BlockPublicPolicy=false,IgnorePublicAcls=false,RestrictPublicBuckets=false
   
   # Grant S3 full access to your IAM user (if needed)
   aws iam attach-user-policy \
     --user-name your-iam-username \
     --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
   ```

5. Update your `.env` file with the S3 bucket information:
   ```
   AWS_REGION=ap-northeast-1
   S3_BUCKET=your-bucket-name
   S3_PREFIX=stock-data
   ```

## Usage

### Fetch Daily Data

To fetch the latest daily stock data:

```bash
python src/fetch_daily.py
```

This script is designed to be run as a daily cron job or scheduled task.

### Fetch Historical Data

To fetch historical stock data (one-time operation):

```bash
python src/fetch_bulk.py
```

Note: This operation may take some time due to API rate limits.

### Mock Mode

For testing without making actual API calls, set `MOCK_MODE=true` in your `.env` file.

### Debug Mode

For detailed logging, set `DEBUG_MODE=true` in your `.env` file.

## Data Storage

Data is stored in S3 with the following structure:

```
s3://s3-data-uploader-bucket/stock-data/
├── SYMBOL/
│   ├── latest.json         # Latest data point
│   ├── full.json           # All historical data
│   ├── metadata.json       # Metadata about the stock data
│   └── daily/
│       ├── YYYY-MM-DD.json # Individual daily data
```

You can verify the data in the S3 bucket using the AWS CLI:

```bash
# List all objects in the bucket
aws s3 ls s3://s3-data-uploader-bucket/ --recursive

# Download a specific file
aws s3 cp s3://s3-data-uploader-bucket/stock-data/AAPL/latest.json ./
```

## Notifications

The system can send notifications via email and/or Slack:

- Success notifications when data is successfully fetched and stored
- Warning notifications when there are non-critical issues
- Error notifications when there are critical failures

Configure notification settings in the `.env` file.

## AWS Deployment

For production use, this project can be deployed as:

1. An AWS Lambda function triggered by EventBridge (CloudWatch Events)
2. An ECS task running on a schedule
3. An EC2 instance with a cron job

## License

[MIT License](LICENSE)
