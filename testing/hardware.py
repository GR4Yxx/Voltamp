import serial
import time
import random
import threading

# Configuration for the simulated device to write to COM3
SERIAL_PORT = 'COM1'
BAUD_RATE = 9600

# Messages to send
messages = [
    'High temperature',
    'Low temparture',
    'High Light',
    'Low Moisture levels'

]

def simulate_serial_device():
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    while True:
        message = random.choice(messages)
        ser.write((message + '\n').encode('utf-8'))
        print(f"Simulated device sent: {message}")
        time.sleep(random.randint(10, 20))  # Send a message every 1-5 seconds

if __name__ == '__main__':
    threading.Thread(target=simulate_serial_device).start()
