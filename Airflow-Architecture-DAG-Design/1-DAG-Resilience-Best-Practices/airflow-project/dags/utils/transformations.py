"""
Transformation utility functions for the API to S3 ETL DAG.
Contains reusable data cleaning and enrichment functions.
"""
from datetime import datetime
from typing import Tuple, List, Dict, Any

import pandas as pd
import numpy as np
import logging


def clean_dataset(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """
    Clean and preprocess the raw dataset from the API.
    
    Args:
        df: DataFrame containing the raw data from the API
        
    Returns:
        Tuple containing:
        - daily_data: List of daily aggregated records
        - hourly_data: List of hourly aggregated records
        - raw_count: Count of records processed
    """
    # Data cleaning and validation
    logging.info(f"Starting data cleaning process for {len(df)} records")
    
    # Handle missing values
    df.dropna(subset=['id', 'timestamp'], inplace=True)
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # Remove rows with invalid timestamps
    df = df[~df['timestamp'].isna()]
    
    # Add additional fields
    df['processed_date'] = datetime.now().strftime('%Y-%m-%d')
    
    # Daily aggregation
    daily_data = df.groupby(df['timestamp'].dt.date).agg({
        'value': ['mean', 'sum', 'count', 'min', 'max', 'std'],
        'id': 'nunique'
    })
    
    # Flatten multi-level columns
    daily_data.columns = ['_'.join(col).strip() for col in daily_data.columns.values]
    daily_data = daily_data.reset_index()
    daily_data.rename(columns={'index': 'date'}, inplace=True)
    
    # Hourly aggregation
    hourly_data = df.groupby([
        df['timestamp'].dt.date, 
        df['timestamp'].dt.hour
    ]).agg({
        'value': ['mean', 'sum', 'count']
    })
    
    # Flatten multi-level columns for hourly data
    hourly_data.columns = ['_'.join(col).strip() for col in hourly_data.columns.values]
    hourly_data = hourly_data.reset_index()
    hourly_data.rename(columns={'level_0': 'date', 'level_1': 'hour'}, inplace=True)
    
    # Convert to records format for JSON serialization
    daily_data_records = daily_data.to_dict(orient='records')
    hourly_data_records = hourly_data.to_dict(orient='records')
    
    logging.info(f"Cleaning complete. Produced {len(daily_data_records)} daily records and {len(hourly_data_records)} hourly records.")
    
    return daily_data_records, hourly_data_records, len(df)


def enrich_dataset(daily_data: List[Dict[str, Any]], raw_count: int) -> List[Dict[str, Any]]:
    """
    Enrich the daily dataset with additional metrics and context.
    
    Args:
        daily_data: List of daily aggregated records
        raw_count: Count of raw records processed
        
    Returns:
        List of enriched daily records
    """
    logging.info(f"Enriching {len(daily_data)} daily records")
    
    # Convert to DataFrame for processing
    df = pd.DataFrame(daily_data)
    
    if not df.empty:
        # Add enrichment fields
        df['total_records'] = raw_count
        df['avg_records_per_day'] = raw_count / len(df)
        df['processing_timestamp'] = datetime.now().isoformat()
        
        # Calculate moving averages if enough data points
        if len(df) >= 3:
            df['value_mean_3day_ma'] = df['value_mean'].rolling(window=3, min_periods=1).mean()
        
        # Add day of week
        if 'date' in df.columns:
            df['day_of_week'] = pd.to_datetime(df['date']).dt.day_name()
            
        # Flag outliers (values more than 3 std devs from mean)
        if 'value_mean' in df.columns and 'value_std' in df.columns:
            mean_value = df['value_mean'].mean()
            std_value = df['value_std'].mean()
            df['is_outlier'] = np.abs(df['value_mean'] - mean_value) > (3 * std_value)
            
    logging.info(f"Enrichment complete with {len(df.columns)} attributes")
    return df.to_dict(orient='records')