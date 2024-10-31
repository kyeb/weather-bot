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

sinch_client = sinch.SinchClient(
    key_id=os.getenv('SINCH_KEY_ID'),
    key_secret=os.getenv('SINCH_KEY_SECRET'),
    project_id=os.getenv('SINCH_PROJECT_ID')
)

@app.route('/', methods=['POST'])
def result():
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

