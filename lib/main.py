import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import smtplib
import requests
import os
import time
import threading
import json
import sys
import re
from datetime import datetime

# Configuration defaults
DEFAULT_SERIAL_PORT = 'COM4'
BAUD_RATE = 9600
CONFIG_FILE = 'config.json'
DEFAULT_EMAIL_ADDRESS = 'your_email@gmail.com'
DEFAULT_EMAIL_PASSWORD = 'your_app_password'  # Use the app password
DEFAULT_RECIPIENTS = ['recipient1@example.com', 'recipient2@example.com']
DEFAULT_PHONE_NUMBERS = ['+1234567890', '+0987654321']
DEFAULT_TWILIO_SID = 'your_twilio_sid'
DEFAULT_TWILIO_AUTH_TOKEN = 'your_twilio_auth_token'
DEFAULT_TWILIO_PHONE_NUMBER = 'your_twilio_phone_number'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
UNSENT_MESSAGES_FILE = 'unsent_messages.json'

ser = None
file_lock = threading.Lock()

def log_message(message):
    if 'log_text' in globals():
        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, message + '\n')
        log_text.see(tk.END)
        log_text.config(state=tk.DISABLED)
    print(message)

def send_email(subject, body, recipients, email_address, email_password):
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(email_address, email_password)
            message = f'Subject: {subject}\n\n{body}'
            server.sendmail(email_address, recipients, message)
        return True
    except Exception as e:
        log_message(f"Failed to send email: {e}")
        return False

def send_sms(body, phone_numbers, twilio_sid, twilio_auth_token, twilio_phone_number):
    try:
        for number in phone_numbers:
            data = {
                'From': twilio_phone_number,
                'To': number,
                'Body': body
            }
            response = requests.post(
                f'https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json',
                data=data,
                auth=(twilio_sid, twilio_auth_token)
            )
            if response.status_code != 201:
                raise Exception(f"Failed to send SMS to {number}: {response.text}")
        return True
    except Exception as e:
        log_message(f"Failed to send SMS: {e}")
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

def resend_unsent_messages(email_address, email_password, recipients, phone_numbers, twilio_sid, twilio_auth_token, twilio_phone_number):
    with file_lock:
        if os.path.exists(UNSENT_MESSAGES_FILE):
            with open(UNSENT_MESSAGES_FILE, 'r') as file:
                unsent_messages = json.load(file)
            if unsent_messages:
                remaining_messages = []
                for message_info in unsent_messages:
                    message = message_info['message']
                    received_timestamp = message_info['received_timestamp']
                    sent_timestamp = datetime.now()
                    sent_formatted_timestamp = sent_timestamp.strftime("%dth %B, %Y at %H:%M")
                    email_body = f"Message: {message}\nReceived at: {received_timestamp}\nSent at: {sent_formatted_timestamp}\n\nNote: This message was delayed due to network issues."
                    sms_body = f"Msg: {message}\nRecv: {received_timestamp}\nSent: {sent_formatted_timestamp}\nNote: Msg delayed due to network issues."
                    if send_email('Volt Amp Notification', email_body, recipients, email_address, email_password) and send_sms(sms_body, phone_numbers, twilio_sid, twilio_auth_token, twilio_phone_number):
                        message_info['sent_timestamp'] = sent_formatted_timestamp
                        log_message(f"Resent delayed message: {message}")
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

def network_monitor(email_address, email_password, recipients, phone_numbers, twilio_sid, twilio_auth_token, twilio_phone_number):
    while True:
        if check_network():
            resend_unsent_messages(email_address, email_password, recipients, phone_numbers, twilio_sid, twilio_auth_token, twilio_phone_number)
        time.sleep(60)  # Check network connectivity every 60 seconds

def start_script(serial_port, email_address, email_password, recipients, phone_numbers, twilio_sid, twilio_auth_token, twilio_phone_number):
    global ser
    ser = serial.Serial(serial_port, BAUD_RATE, timeout=1)
    log_message("Script started")

    def main_loop():
        resend_unsent_messages(email_address, email_password, recipients, phone_numbers, twilio_sid, twilio_auth_token, twilio_phone_number)
        while True:
            if ser.in_waiting > 0:
                message = ser.readline().decode('utf-8').strip()
                message = re.sub(r'at\+cmgs="[^"]*"\r', '', message).strip()
                message = message.rstrip().rstrip('\u001a')

                log_message(f"Received message: {message}")
                received_timestamp = datetime.now()
                rec_formatted_timestamp = received_timestamp.strftime("%dth %B, %Y at %H:%M")
                email_body = f"Message: {message}\nReceived at: {rec_formatted_timestamp}\nSent at: {rec_formatted_timestamp}"
                sms_body = f"Msg: {message}\nRecv: {rec_formatted_timestamp}\nSent: {rec_formatted_timestamp}"
                if not (send_email('Volt Amp Notification', email_body, recipients, email_address, email_password) and send_sms(sms_body, phone_numbers, twilio_sid, twilio_auth_token, twilio_phone_number)):
                    save_unsent_message(message, rec_formatted_timestamp)
                else:
                    sent_timestamp = datetime.now()
                    sent_formatted_timestamp = sent_timestamp.strftime("%dth %B, %Y at %H:%M")
                    log_message(f"Message sent at {sent_formatted_timestamp}, received at {rec_formatted_timestamp}")
            time.sleep(1)

    # Start the network monitor thread
    threading.Thread(target=network_monitor, args=(email_address, email_password, recipients, phone_numbers, twilio_sid, twilio_auth_token, twilio_phone_number), daemon=True).start()
    threading.Thread(target=main_loop, daemon=True).start()

def stop_script():
    global ser
    if ser is not None:
        ser.close()
        ser = None
    log_message("Script stopped")

def save_config():
    serial_port = serial_port_entry.get()
    email_address = email_entry.get()
    email_password = password_entry.get()
    recipients = recipients_entry.get().split(',')
    phone_numbers = phone_numbers_entry.get().split(',')
    twilio_sid = twilio_sid_entry.get()
    twilio_auth_token = twilio_auth_token_entry.get()
    twilio_phone_number = twilio_phone_number_entry.get()
    config = {
        'serial_port': serial_port,
        'email_address': email_address,
        'email_password': email_password,
        'recipients': recipients,
        'phone_numbers': phone_numbers,
        'twilio_sid': twilio_sid,
        'twilio_auth_token': twilio_auth_token,
        'twilio_phone_number': twilio_phone_number
    }
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file, indent=4)
    log_message("Configuration saved")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)
        return config
    return {
        'serial_port': DEFAULT_SERIAL_PORT,
        'email_address': DEFAULT_EMAIL_ADDRESS,
        'email_password': DEFAULT_EMAIL_PASSWORD,
        'recipients': DEFAULT_RECIPIENTS,
        'phone_numbers': DEFAULT_PHONE_NUMBERS,
        'twilio_sid': DEFAULT_TWILIO_SID,
        'twilio_auth_token': DEFAULT_TWILIO_AUTH_TOKEN,
        'twilio_phone_number': DEFAULT_TWILIO_PHONE_NUMBER
    }

def on_start():
    save_config()  # Save configuration before starting the script
    config = load_config()
    start_script(
        config['serial_port'],
        config['email_address'],
        config['email_password'],
        config['recipients'],
        config['phone_numbers'],
        config['twilio_sid'],
        config['twilio_auth_token'],
        config['twilio_phone_number']
    )

def on_stop():
    stop_script()

# Check if the script should run without GUI
if '--nogui' in sys.argv:
    config = load_config()
    start_script(
        config['serial_port'],
        config['email_address'],
        config['email_password'],
        config['recipients'],
        config['phone_numbers'],
        config['twilio_sid'],
        config['twilio_auth_token'],
        config['twilio_phone_number']
    )
    while True:
        time.sleep(1)
else:
    # Load configuration
    config = load_config()

    # Create the main application window
    root = tk.Tk()
    root.title("Serial Message Processor")

    # Create tabs
    tab_control = ttk.Notebook(root)
    tab1 = ttk.Frame(tab_control)
    tab2 = ttk.Frame(tab_control)
    tab_control.add(tab1, text='Main')
    tab_control.add(tab2, text='Configuration')
    tab_control.pack(expand=1, fill='both')

    # Main tab
    start_button = tk.Button(tab1, text="Start", command=on_start)
    start_button.grid(row=0, column=0, padx=10, pady=10, sticky='ew')

    stop_button = tk.Button(tab1, text="Stop", command=on_stop)
    stop_button.grid(row=0, column=1, padx=10, pady=10, sticky='ew')

    # Log display
    log_text = scrolledtext.ScrolledText(tab1, state=tk.DISABLED, width=80, height=20)
    log_text.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

    # Configuration tab
    # Serial port configuration
    tk.Label(tab2, text="Serial Port:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
    serial_port_entry = tk.Entry(tab2)
    serial_port_entry.grid(row=0, column=1, padx=10, pady=5, sticky='ew')
    serial_port_entry.insert(0, config['serial_port'])

    # Email configuration
    tk.Label(tab2, text="Email Address:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
    email_entry = tk.Entry(tab2)
    email_entry.grid(row=1, column=1, padx=10, pady=5, sticky='ew')
    email_entry.insert(0, config['email_address'])

    tk.Label(tab2, text="Email Password:").grid(row=2, column=0, padx=10, pady=5, sticky='w')
    password_entry = tk.Entry(tab2, show="*")
    password_entry.grid(row=2, column=1, padx=10, pady=5, sticky='ew')
    password_entry.insert(0, config['email_password'])

    # Recipients configuration
    tk.Label(tab2, text="Recipients (comma separated):").grid(row=3, column=0, padx=10, pady=5, sticky='w')
    recipients_entry = tk.Entry(tab2)
    recipients_entry.grid(row=3, column=1, padx=10, pady=5, sticky='ew')
    recipients_entry.insert(0, ','.join(config['recipients']))

    # Phone numbers configuration
    tk.Label(tab2, text="Phone Numbers (comma separated):").grid(row=4, column=0, padx=10, pady=5, sticky='w')
    phone_numbers_entry = tk.Entry(tab2)
    phone_numbers_entry.grid(row=4, column=1, padx=10, pady=5, sticky='ew')
    phone_numbers_entry.insert(0, ','.join(config['phone_numbers']))

    # Twilio configuration
    tk.Label(tab2, text="Twilio SID:").grid(row=5, column=0, padx=10, pady=5, sticky='w')
    twilio_sid_entry = tk.Entry(tab2)
    twilio_sid_entry.grid(row=5, column=1, padx=10, pady=5, sticky='ew')
    twilio_sid_entry.insert(0, config['twilio_sid'])

    tk.Label(tab2, text="Twilio Auth Token:").grid(row=6, column=0, padx=10, pady=5, sticky='w')
    twilio_auth_token_entry = tk.Entry(tab2)
    twilio_auth_token_entry.grid(row=6, column=1, padx=10, pady=5, sticky='ew')
    twilio_auth_token_entry.insert(0, config['twilio_auth_token'])

    tk.Label(tab2, text="Twilio Phone Number:").grid(row=7, column=0, padx=10, pady=5, sticky='w')
    twilio_phone_number_entry = tk.Entry(tab2)
    twilio_phone_number_entry.grid(row=7, column=1, padx=10, pady=5, sticky='ew')
    twilio_phone_number_entry.insert(0, config['twilio_phone_number'])

    # Save button
    save_button = tk.Button(tab2, text="Save Configuration", command=save_config)
    save_button.grid(row=8, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

    # Make the configuration fields expand horizontally
    for i in range(8):
        tab2.grid_rowconfigure(i, weight=1)
        tab2.grid_columnconfigure(1, weight=1)

    # Make the log text box expand
    tab1.grid_rowconfigure(1, weight=1)
    tab1.grid_columnconfigure(0, weight=1)
    tab1.grid_columnconfigure(1, weight=1)

    # Run the main application loop
    root.mainloop()
