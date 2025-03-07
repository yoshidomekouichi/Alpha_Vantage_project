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
├── src/
│   ├── fetch_daily.py       # Daily batch script
│   ├── fetch_bulk.py        # Historical data fetch script
│   ├── config.py            # Configuration management
│   └── utils/
│       ├── api_client.py    # Alpha Vantage API client
│       ├── data_processing.py # Data validation and transformation
│       ├── storage.py       # S3 storage operations
│       ├── atomic_s3.py     # Atomic S3 updates
│       ├── logging_utils.py # Logging utilities
│       └── alerts.py        # Email and Slack notifications
├── logs/                    # Log files
├── .env                     # Environment variables (create from .env.sample)
├── .env.sample              # Sample environment variables
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
s3://your-bucket/stock-data/
├── SYMBOL/
│   ├── latest.json         # Latest data point
│   ├── full.json           # All historical data
│   ├── metadata.json       # Metadata about the stock data
│   └── daily/
│       ├── YYYY-MM-DD.json # Individual daily data
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
