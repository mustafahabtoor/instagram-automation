import requests
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v19.0"

def make_request_with_retry(url, method="POST", params=None, json_data=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=10)
            else:
                response = requests.post(url, params=params, json=json_data, timeout=10)

            if response.status_code == 429: # Rate limit error
                sleep_time = (2 ** attempt)
                logger.warning(f"Rate limited. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
                continue

            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)
    return None

def reply_to_comment(comment_id: str, message: str, access_token: str):
    url = f"{GRAPH_API_URL}/{comment_id}/replies"
    payload = {
        "message": message,
        "access_token": access_token
    }
    response = make_request_with_retry(url, method="POST", json_data=payload)
    if response and response.status_code == 200:
        logger.info(f"Successfully replied to comment {comment_id}")
        return response.json()
    else:
        logger.error(f"Failed to reply to comment: {response.text if response else 'No response'}")
        return None

def send_dm(instagram_business_account_id: str, recipient_id: str, message: str, access_token: str):
    url = f"{GRAPH_API_URL}/{instagram_business_account_id}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "access_token": access_token
    }
    response = make_request_with_retry(url, method="POST", json_data=payload)
    if response and response.status_code == 200:
        logger.info(f"Successfully sent DM to user {recipient_id}")
        return response.json()
    else:
        logger.error(f"Failed to send DM: {response.text if response else 'No response'}")
        return None

def get_post_details(post_id: str, access_token: str):
    url = f"{GRAPH_API_URL}/{post_id}"
    params = {
        "fields": "id,caption,media_url,thumbnail_url",
        "access_token": access_token
    }
    response = make_request_with_retry(url, method="GET", params=params)
    if response and response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to get post details: {response.text if response else 'No response'}")
        return None
