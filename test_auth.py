import logging
from auth import get_dhan_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_authentication():
    """
    Test the Dhan authentication flow.
    
    This script will:
    1. Attempt to initialize the Dhan client using a manual Access Token.
    2. Fetch the user profile to verify the access token is valid.
    """
    try:
        logger.info("Starting Dhan authentication test...")
        client = get_dhan_client()
        
        logger.info("Fetching fund limits to verify session...")
        response = client.get_fund_limits()
        
        if response.get('status') == 'success' or 'data' in response:
            logger.info("Successfully authenticated!")
            # Note: Dhan response for fund limits usually contains a 'data' object
            data = response.get('data', {})
            logger.info(f"Available Balance: {data.get('availablerequestedlimit', 'N/A')}")
        else:
            logger.error(f"Authentication failed or session invalid. Response: {response}")
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        logger.info("\nTip: Make sure you have updated your .env file with actual DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN.")

if __name__ == "__main__":
    test_authentication()
