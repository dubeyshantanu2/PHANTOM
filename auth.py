import os
import logging
from dotenv import load_dotenv
from dhanhq import dhanhq

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def get_dhan_client():
    """
    Instantiate and return an authenticated DhanHQ client using a manual Access Token.

    Reads DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN from environment variables.
    The Access Token must be generated manually from the DhanHQ portal and 
    is typically valid for 24 hours.

    Returns:
        dhanhq: An authenticated instance of the Dhan SDK client.

    Raises:
        ValueError: If required credentials are missing.
    """
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")

    if not client_id or not access_token:
        logger.error("DHAN_CLIENT_ID or DHAN_ACCESS_TOKEN missing in environment variables.")
        raise ValueError("Dhan credentials not found. Please provide DHAN_CLIENT_ID and a valid DHAN_ACCESS_TOKEN.")

    try:
        # Initialize the official SDK with the manual access token
        client = dhanhq(client_id, access_token)
        logger.info("DhanHQ client successfully initialized with manual token.")
        
        return client

    except Exception as e:
        logger.error(f"Unexpected error during Dhan client initialization: {e}")
        raise e
