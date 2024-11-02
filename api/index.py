import os
import re
import sinch
import requests
from datetime import datetime, timedelta
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

def log_info(msg):
    print(f"[INFO] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

def log_error(msg):
    print(f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

app = Flask(__name__)

def extract_coordinates(text):
    pattern = r'(-?\d+\.?\d*),\s*(-?\d+\.?\d*)'
    match = re.search(pattern, text)
    
    if match:
        lat, lon = map(float, match.groups())
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    return None

def get_weather_forecast(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,precipitation_probability,windspeed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        "&temperature_unit=fahrenheit"
        "&windspeed_unit=mph"
        "&forecast_days=10"
        "&timezone=auto"
    )
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_error(f"Failed to fetch weather data: {str(e)}")
        return None

def format_hourly_forecast(data):
    now = datetime.utcnow()
    
    hourly = []
    for i in range(48):
        temp = data['hourly']['temperature_2m'][i]
        precip = data['hourly']['precipitation_probability'][i]
        wind = data['hourly']['windspeed_10m'][i]
        
        if i % 3 == 0:
            time = (now + timedelta(hours=i)).strftime("%a %I%p")
            time = time.replace("AM", "am").replace("PM", "pm")
            hourly.append(f"{time}: {temp:.0f}F {precip}% {wind:.0f}mph")
    
    return "Next 48 hours:\n" + "\n".join(hourly)

def format_daily_forecast(data):
    daily = []
    for i in range(10):
        high = data['daily']['temperature_2m_max'][i]
        low = data['daily']['temperature_2m_min'][i]
        precip = data['daily']['precipitation_probability_max'][i]
        
        date = datetime.strptime(data['daily']['time'][i], '%Y-%m-%d').strftime('%a')
        daily.append(f"{date}: {low:.0f}-{high:.0f}F {precip}%")
    
    return "\n10-day forecast:\n" + "\n".join(daily)

def get_sinch_client():
    key_id = os.getenv('SINCH_KEY_ID')
    key_secret = os.getenv('SINCH_KEY_SECRET')
    project_id = os.getenv('SINCH_PROJECT_ID')
    
    log_info(f"Attempting to initialize Sinch client with project_id: {project_id}")
    
    if not all([key_id, key_secret, project_id]):
        missing = [k for k, v in {
            'SINCH_KEY_ID': key_id,
            'SINCH_KEY_SECRET': key_secret,
            'SINCH_PROJECT_ID': project_id
        }.items() if not v]
        log_error(f"Missing environment variables: {missing}")
        raise ValueError(f"Missing required environment variables: {missing}")
    
    return sinch.SinchClient(
        key_id=key_id,
        key_secret=key_secret,
        project_id=project_id
    )

NO_COORDS_MSG = """I couldn't find any coordinates in your message. To get coordinates:
1. Open Google Maps
2. Press and hold on a location
3. Copy the numbers at the bottom
4. Send them here (example: 37.4259011,-122.1576107)"""

@app.route('/sms/receive', methods=['POST'])
def receive_sms():
    try:
        sinch_client = get_sinch_client()
    except Exception as e:
        log_error(f"Failed to initialize Sinch client: {str(e)}")
        return f"Configuration error: {str(e)}", 500

    inbound_message = request.get_json()
    log_info(f"Received inbound message: {inbound_message}")
    
    if all(key in inbound_message for key in ["body", "to", "from"]):
        try:
            coords = extract_coordinates(inbound_message["body"])
            
            if not coords:
                response_text = NO_COORDS_MSG
            else:
                weather_data = get_weather_forecast(*coords)
                if weather_data:
                    hourly = format_hourly_forecast(weather_data)
                    daily = format_daily_forecast(weather_data)
                    response_text = f"{hourly}\n\n{daily}"
                else:
                    response_text = "Sorry, I couldn't fetch the weather data right now. Please try again later."
            
            response = sinch_client.sms.batches.send(
                body=response_text,
                delivery_report="none",
                to=[inbound_message["from"]],
                from_=inbound_message["to"]
            )
            log_info(f"Successfully sent message! Response: {response}")
            return "Inbound message received", 200
        except Exception as e:
            log_error(f"Failed to send SMS: {str(e)}")
            return "Internal server error", 500
    else:
        log_error(f"Received invalid message format. Missing required fields. Message: {inbound_message}")
        return "Invalid data", 400

@app.route('/sms/delivery_report', methods=['POST'])
def delivery_report():
    report = request.get_json()
    log_info(f"Message delivered: {report}")
    return "OK", 200

@app.route('/', methods=['GET'])
def health_check():
    try:
        sinch_client = get_sinch_client()
        return "Configuration OK", 200
    except Exception as e:
        log_error(f"Health check failed: {str(e)}")
        return f"Configuration error: {str(e)}", 500

