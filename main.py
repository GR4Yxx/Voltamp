import serial
import smtplib
import requests
import os
import time

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

def save_unsent_message(message):
    with open(UNSENT_MESSAGES_FILE, 'a') as file:
        file.write(message + '\n')

def resend_unsent_messages():
    if os.path.exists(UNSENT_MESSAGES_FILE):
        with open(UNSENT_MESSAGES_FILE, 'r') as file:
            unsent_messages = file.readlines()
        if unsent_messages:
            for message in unsent_messages:
                message = message.strip()
                if send_email('Unsent Serial Message', message, RECIPIENTS) and send_sms(message, PHONE_NUMBERS):
                    unsent_messages.remove(message + '\n')
        with open(UNSENT_MESSAGES_FILE, 'w') as file:
            file.writelines(unsent_messages)

if __name__ == '__main__':
    resend_unsent_messages()
    while True:
        if ser.in_waiting > 0:
            message = ser.readline().decode('utf-8').strip()
            print(f"Received message: {message}")
            if not (send_email(EMAIL_SUBJECT, message, RECIPIENTS) and send_sms(message, PHONE_NUMBERS)):
                save_unsent_message(message)
        time.sleep(1)
