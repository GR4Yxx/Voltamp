import serial
import smtplib
import requests
import os
import time
import threading
import json
from datetime import datetime

# Configuration
SERIAL_PORT = 'COM2'  # Replace with your serial port
BAUD_RATE = 9600
RECIPIENTS = ['xpjosh10@gmail.com']
PHONE_NUMBERS = ['+919920081996']
UNSENT_MESSAGES_FILE = 'unsent_messages.txt'
EMAIL_SUBJECT='Message from sensor'


#Twilio and Gmail Setup
EMAIL_ADDRESS = os.environ['EMAIL_ID']
EMAIL_PASSWORD = os.environ['EMAIL_PASSKEY']
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMS_API_URL = os.environ['SMS_API_URL']
SMS_API_AUTH = (os.environ['SMS_API_AUTH'], os.environ['AUTH_TOKEN'])



# Initialize serial connection
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

# Create a lock for thread-safe file access
file_lock = threading.Lock()

def send_email(subject, body, recipients):
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            message = f'Subject: {subject}\n\n{body}'
            server.sendmail(EMAIL_ADDRESS, recipients, message)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_sms(body, phone_numbers):
    try:
        for number in phone_numbers:
            data = {
                'From': os.environ['TWILIO_PHONE'],
                'To': number,
                'Body': body
            }
            response = requests.post(SMS_API_URL, data=data, auth=SMS_API_AUTH)
            if response.status_code != 201:
                raise Exception(f"Failed to send SMS to {number}: {response.text}")
        return True
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return False

def save_unsent_message(message, received_timestamp):
    with file_lock:
        unsent_message = {
            'message': message,
            'received_timestamp': received_timestamp,
            'sent_timestamp': None
        }
        if os.path.exists(UNSENT_MESSAGES_FILE):
            with open(UNSENT_MESSAGES_FILE, 'r') as file:
                unsent_messages = json.load(file)
        else:
            unsent_messages = []
        unsent_messages.append(unsent_message)
        with open(UNSENT_MESSAGES_FILE, 'w') as file:
            json.dump(unsent_messages, file, indent=4)

def resend_unsent_messages():
    with file_lock:
        if os.path.exists(UNSENT_MESSAGES_FILE):
            with open(UNSENT_MESSAGES_FILE, 'r') as file:
                unsent_messages = json.load(file)
            if unsent_messages:
                remaining_messages = []
                for message_info in unsent_messages:
                    message = message_info['message']
                    if send_email('Unsent Serial Message', message, RECIPIENTS) and send_sms(message, PHONE_NUMBERS):
                        message_info['sent_timestamp'] = datetime.now().isoformat()
                    else:
                        remaining_messages.append(message_info)
                with open(UNSENT_MESSAGES_FILE, 'w') as file:
                    json.dump(remaining_messages, file, indent=4)

def check_network():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# This functions checks for internet, and sends unsent messages if available.
def network_monitor():
    while True:
        if check_network():
            resend_unsent_messages()
        time.sleep(60)  # Check network connectivity every 60 seconds

def main():
    # Start network monitor thread
    threading.Thread(target=network_monitor, daemon=True).start()

    # First try to resend messages.
    resend_unsent_messages()
    while True:
        # Starts checking for serial.
        if ser.in_waiting > 0:
            message = ser.readline().decode('utf-8').strip()
            received_timestamp = datetime.now().isoformat()
            print(f"[{received_timestamp}]Received message: {message}")
            if not (send_email('Volt Amp Notification', message, RECIPIENTS) and send_sms(message, PHONE_NUMBERS)):
                save_unsent_message(message, received_timestamp)
            else:
                sent_timestamp = datetime.now().isoformat()
                print(f"Message sent at {sent_timestamp}, received at {received_timestamp}")
        time.sleep(1)

if __name__ == '__main__':
    main()