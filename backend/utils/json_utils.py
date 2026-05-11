# backend/utils/json_utils.py
"""
JSON serialization utilities for handling pandas DataFrames and other data types
that may contain NaN values or other non-JSON-serializable values.
"""

import json
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Union
from decimal import Decimal
from datetime import datetime, date

class SafeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles NaN, infinity, and other problematic values"""
    
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)):
            if np.isnan(obj):
                return None
            elif np.isinf(obj):
                return None
            else:
                return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif pd.isna(obj):
            return None
        return super().default(obj)

def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize an object to JSON, handling NaN and other problematic values"""
    return json.dumps(obj, cls=SafeJSONEncoder, **kwargs)

def clean_dataframe_for_json(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean a pandas DataFrame to make it JSON serializable.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Cleaned DataFrame with NaN values replaced with None
    """
    df_clean = df.copy()
    
    # Replace NaN values with None (which becomes null in JSON)
    df_clean = df_clean.replace({np.nan: None})
    
    # Replace infinite values with None
    df_clean = df_clean.replace({np.inf: None, -np.inf: None})
    
    # Handle datetime columns
    for col in df_clean.columns:
        if df_clean[col].dtype == 'datetime64[ns]':
            df_clean[col] = df_clean[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        elif 'datetime' in str(df_clean[col].dtype):
            df_clean[col] = df_clean[col].astype(str)
    
    # Convert any remaining problematic numeric types
    for col in df_clean.columns:
        if df_clean[col].dtype in ['float64', 'float32']:
            # Check for any remaining NaN or inf values
            df_clean[col] = df_clean[col].replace({np.nan: None, np.inf: None, -np.inf: None})
    
    return df_clean

def dataframe_to_dict_safe(df: pd.DataFrame, orient: str = 'records') -> List[Dict[str, Any]]:
    """
    Convert DataFrame to dictionary list safely, handling NaN values.
    
    Args:
        df: Input DataFrame
        orient: Orientation for conversion ('records' is most common)
        
    Returns:
        List of dictionaries representing DataFrame rows
    """
    df_clean = clean_dataframe_for_json(df)
    return df_clean.to_dict(orient=orient)




"""
JSON serialization utilities for handling pandas DataFrames and other data types
that may contain NaN values or other non-JSON-serializable values.
"""

import json
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Union
from decimal import Decimal
from datetime import datetime, date

class SafeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles NaN, infinity, and other problematic values"""
    
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)):
            if np.isnan(obj):
                return None
            elif np.isinf(obj):
                return None
            else:
                return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif pd.isna(obj):
            return None
        return super().default(obj)

def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize an object to JSON, handling NaN and other problematic values"""
    return json.dumps(obj, cls=SafeJSONEncoder, **kwargs)

def clean_dataframe_for_json(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean a pandas DataFrame to make it JSON serializable.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Cleaned DataFrame with NaN values replaced with None
    """
    df_clean = df.copy()
    
    # Replace NaN values with None (which becomes null in JSON)
    df_clean = df_clean.replace({np.nan: None})
    
    # Replace infinite values with None
    df_clean = df_clean.replace({np.inf: None, -np.inf: None})
    
    # Handle datetime columns
    for col in df_clean.columns:
        if df_clean[col].dtype == 'datetime64[ns]':
            df_clean[col] = df_clean[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        elif 'datetime' in str(df_clean[col].dtype):
            df_clean[col] = df_clean[col].astype(str)
    
    # Convert any remaining problematic numeric types
    for col in df_clean.columns:
        if df_clean[col].dtype in ['float64', 'float32']:
            # Check for any remaining NaN or inf values
            df_clean[col] = df_clean[col].replace({np.nan: None, np.inf: None, -np.inf: None})
    
    return df_clean

def dataframe_to_dict_safe(df: pd.DataFrame, orient: str = 'records') -> List[Dict[str, Any]]:
    """
    Convert DataFrame to dictionary list safely, handling NaN values.
    
    Args:
        df: Input DataFrame
        orient: Orientation for conversion ('records' is most common)
        
    Returns:
        List of dictionaries representing DataFrame rows
    """
    df_clean = clean_dataframe_for_json(df)
    return df_clean.to_dict(orient=orient)











