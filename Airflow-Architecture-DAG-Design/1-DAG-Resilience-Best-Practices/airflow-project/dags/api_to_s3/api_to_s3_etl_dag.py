"""
API to S3 ETL DAG
----------------
This DAG extracts data from an API, transforms it, and loads it to S3.
It demonstrates task separation, resilience patterns, and Airflow best practices.
"""
from datetime import datetime, timedelta
from typing import Dict, Any

from airflow import DAG
from airflow.decorators import task, task_group
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.utils.task_group import TaskGroup

import json
import logging
import pandas as pd
from pathlib import Path
import tempfile

# Import utility functions
from api_to_s3.utils.transformations import clean_dataset, enrich_dataset

# Default arguments for the DAG
default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email': ['alerts@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=60),
    'execution_timeout': timedelta(minutes=120),
}

# Environment variables
API_BASE_URL = Variable.get("api_base_url", default_var="https://api.example.com/data")
API_KEY = Variable.get("api_key", default_var="dummy_key")
S3_BUCKET = Variable.get("s3_bucket", default_var="data-lake-bucket")

with DAG(
    'api_to_s3_etl',
    default_args=default_args,
    description='Extract data from API, transform, and load to S3',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    start_date=datetime(2025, 5, 1),
    catchup=False,
    tags=['api', 's3', 'etl'],
    max_active_runs=1,
    doc_md=__doc__,
) as dag:
    
    # Check if API endpoint is available
    check_api_availability = HttpSensor(
        task_id='check_api_availability',
        http_conn_id='api_connection',
        endpoint='/health',
        request_params={},
        response_check=lambda response: response.status_code == 200,
        poke_interval=60,  # Check every minute
        timeout=600,  # Time out after 10 minutes
        mode='reschedule',  # Release worker slot between checks
    )
    
    # Extract data from API
    extract_data = SimpleHttpOperator(
        task_id='extract_data',
        http_conn_id='api_connection',
        endpoint='/data',
        method='GET',
        headers={"Authorization": f"Bearer {API_KEY}"},
        response_filter=lambda response: json.loads(response.text),
        log_response=True,
        retry_limit=5,
        retry_delay=timedelta(minutes=2),
    )
    
    @task_group(group_id='transform_data_group')
    def transform_data_tasks():
        """Group of tasks handling data transformation"""
        
        @task(
            retry_delay=timedelta(minutes=2),
            retries=3,
            multiple_outputs=True
        )
        def clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
            """Clean and validate the raw data"""
            logging.info(f"Cleaning data with {len(data['records'])} records")
            
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(data['records'])
            
            # Use the imported cleaning function
            daily_data, hourly_data, raw_count = clean_dataset(df)
            
            return {
                'daily_data': daily_data,
                'hourly_data': hourly_data,
                'raw_count': raw_count
            }
        
        @task(retries=2)
        def enrich_data(daily_data: list, raw_count: int) -> list:
            """Add additional metrics and context to the data"""
            logging.info(f"Enriching {len(daily_data)} daily records")
            
            # Use the imported enrichment function
            enriched_data = enrich_dataset(daily_data, raw_count)
            
            return enriched_data
        
        # Define the task dependencies within the group
        cleaned_data = clean_data(extract_data.output)
        enriched_daily_data = enrich_data(
            cleaned_data['daily_data'], 
            cleaned_data['raw_count']
        )
        
        # Return the outputs from the task group
        return {
            'daily_data': enriched_daily_data,
            'hourly_data': cleaned_data['hourly_data'],
            'raw_count': cleaned_data['raw_count']
        }
    
    # Execute the transform task group
    transform_result = transform_data_tasks()
    
    @task_group(group_id='load_to_s3_group')
    def load_to_s3_tasks(daily_data, hourly_data, raw_count):
        """Group of tasks handling data loading to S3"""
        
        @task(retries=5, retry_delay=timedelta(minutes=2))
        def upload_daily_data(data: list) -> str:
            """Upload daily aggregated data to S3"""
            execution_date = '{{ ds }}'
            s3_path = f"daily/{execution_date}/daily_metrics.json"
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
                json.dump(data, f)
                f.flush()
                
                # Upload to S3
                s3_hook = S3Hook(aws_conn_id='aws_default')
                s3_hook.load_file(
                    filename=f.name,
                    key=s3_path,
                    bucket_name=S3_BUCKET,
                    replace=True
                )
            
            return s3_path
        
        @task(retries=5, retry_delay=timedelta(minutes=2))
        def upload_hourly_data(data: list) -> str:
            """Upload hourly aggregated data to S3"""
            execution_date = '{{ ds }}'
            s3_path = f"hourly/{execution_date}/hourly_metrics.json"
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
                json.dump(data, f)
                f.flush()
                
                # Upload to S3
                s3_hook = S3Hook(aws_conn_id='aws_default')
                s3_hook.load_file(
                    filename=f.name,
                    key=s3_path,
                    bucket_name=S3_BUCKET,
                    replace=True
                )
            
            return s3_path
            
        @task(retries=3)
        def log_etl_metrics(daily_path: str, hourly_path: str, count: int) -> None:
            """Log metrics about the ETL process for monitoring"""
            logging.info(f"ETL process completed successfully")
            logging.info(f"Processed {count} records")
            logging.info(f"Daily data uploaded to: s3://{S3_BUCKET}/{daily_path}")
            logging.info(f"Hourly data uploaded to: s3://{S3_BUCKET}/{hourly_path}")
            
            # This could also send metrics to a monitoring system
            # or update a metadata table
        
        # Upload tasks
        daily_s3_path = upload_daily_data(daily_data)
        hourly_s3_path = upload_hourly_data(hourly_data)
        
        # Log metrics task
        log_etl_metrics(daily_s3_path, hourly_s3_path, raw_count)
    
    # Execute the loading task group
    load_data = load_to_s3_tasks(
        transform_result['daily_data'],
        transform_result['hourly_data'],
        transform_result['raw_count']
    )
    
    # Define the final DAG structure
    check_api_availability >> extract_data >> transform_result >> load_data