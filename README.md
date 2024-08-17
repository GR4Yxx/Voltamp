# Serial Message Handler for Medical Machines

## Overview

This project is designed to read serial messages from COM ports, typically sent by medical machines, using the `pySerial` library. The messages are then forwarded via SMS using Twilio and email via Gmail. The project includes fault tolerance features to ensure that messages are not lost if the network goes down; messages are queued and automatically sent when the connection is restored.

## Features

- **Serial Communication**: Reads messages from COM ports using `pySerial`.
- **Twilio Integration**: Sends messages as SMS via Twilio.
- **Gmail Integration**: Sends messages as emails via Gmail.
- **Customizable Recipients**: Easily configure the recipients for SMS and email notifications.
- **Fault Tolerance**: Messages are saved to a queue if the network is down and sent automatically when the network is restored.

## Prerequisites

- Python 3.x
- `pySerial` library
- Twilio account with API credentials
- Gmail account with App Password for secure sending
- Internet connection for sending messages

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/serial-message-handler.git
   cd serial-message-handler
