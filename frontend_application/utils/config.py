import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Constants
SERVING_ENDPOINT_NAME = os.getenv("SERVING_ENDPOINT_NAME")
assert SERVING_ENDPOINT_NAME, "SERVING_ENDPOINT_NAME is not set"

DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
MLFLOW_EXPERIMENT_ID = os.environ.get("MLFLOW_EXPERIMENT_ID", "3668845090573368")  # Default fallback

# API Configuration
API_TIMEOUT = 160
STREAMING_TIMEOUT = 300  # 5 minutes for streaming requests
MAX_CONCURRENT_STREAMS = 10
MAX_QUEUE_SIZE = 100