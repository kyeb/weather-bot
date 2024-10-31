import os
import sinch
import logging
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_sinch_client():
    key_id = os.getenv('SINCH_KEY_ID')
    key_secret = os.getenv('SINCH_KEY_SECRET')
    project_id = os.getenv('SINCH_PROJECT_ID')
    
    logger.info(f"Attempting to initialize Sinch client with project_id: {project_id}")
    
    if not all([key_id, key_secret, project_id]):
        missing = [k for k, v in {
            'SINCH_KEY_ID': key_id,
            'SINCH_KEY_SECRET': key_secret,
            'SINCH_PROJECT_ID': project_id
        }.items() if not v]
        logger.error(f"Missing environment variables: {missing}")
        raise ValueError(f"Missing required environment variables: {missing}")
    
    return sinch.SinchClient(
        key_id=key_id,
        key_secret=key_secret,
        project_id=project_id
    )

@app.route('/', methods=['POST'])
def result():
    try:
        sinch_client = get_sinch_client()
    except Exception as e:
        logger.error(f"Failed to initialize Sinch client: {str(e)}")
        return f"Configuration error: {str(e)}", 500

    inbound_message = request.get_json()
    logger.info(f"Received inbound message: {inbound_message}")
    
    if all(key in inbound_message for key in ["body", "to", "from"]):
        try:
            logger.info(f"Sending response to {inbound_message['from']} from {inbound_message['to']}")
            response = sinch_client.sms.batches.send(
                body="Thank you for using the Sinch SDK. You sent: " + inbound_message["body"],
                delivery_report="none",
                to=[inbound_message["from"]],
                from_=inbound_message["to"]
            )
            logger.info(f"Successfully sent message, batch id: {response.id}")
            return "Inbound message received", 200
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return "Internal server error", 500
    else:
        logger.warning(f"Received invalid message format. Missing required fields. Message: {inbound_message}")
        return "Invalid data", 400

@app.route('/', methods=['GET'])
def health_check():
    try:
        sinch_client = get_sinch_client()
        return "Configuration OK", 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return f"Configuration error: {str(e)}", 500
