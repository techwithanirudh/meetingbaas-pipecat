# Speaking Meeting Bot Documentation

This document provides step-by-step instructions on how to set up and run a Speaking Meeting Bot, which utilizes MeetingBaas's APIs and pipecat's `WebsocketServerTransport` to participate in online meetings as a speaking bot.

## Prerequisites

- Python 3.x installed
- `grpc_tools` for handling gRPC protobuf files
- Ngrok for exposing your local server to the internet

## Getting Started

### Step 1: Set Up the Virtual Environment
To begin, you need to set up a Python virtual environment and install the required dependencies.

```bash
# Create a virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the required dependencies
pip install -r requirements.txt
```

### Step 2: Compile Protocol Buffers
To enable communication with MeetingBaas's API, you need to compile the `frames.proto` file with the `grpc_tools`.

```bash
# Compile the protobuf file
python -m grpc_tools.protoc --proto_path=./ --python_out=./protobufs frames.proto
```

### Step 3: Set Up Environment Variables
You need to provide the necessary credentials for MeetingBaas's API and other 3rd part tools.

```bash
# Copy the example environment file
cp env.example .env
```
Now, open the `.env` file and update it with your credentials.

## Running the Speaking Meeting Bot

Once your setup is complete, follow these steps to run the bot and connect it to an online meeting.

### Step 1: Run the Bot
Run the Python script to start the Speaking Meeting Bot:

```bash
python main.py
```

### Step 2: Set Up Ngrok to Expose Local Server
To allow MeetingBaas to communicate with your bot, you need to expose the local server using Ngrok.

```bash
# Run the Ngrok HTTP tunnel on port 8766
ngrok http 8766
```

Ngrok will provide you with a public URL that can be used by MeetingBaas to communicate with your local bot.

### Step 3: Start the MeetingBaas Bot
The final step is to run the MeetingBaas bot script to connect it with the desired meeting session.

```bash
python scripts/meetingbaas.py
```

Now, visit the meeting URL in your browser to initiate a session and watch your bot actively participate in the meeting!

## Troubleshooting Tips
- Ensure that you have activated the virtual environment before running any Python commands.
- If Ngrok is not running properly, check for any firewall issues that may be blocking its communication.
- Double-check the `.env` file to make sure all necessary credentials are correctly filled in.

## Additional Information
- MeetingBaas allows integration with external bots using APIs that leverage the `WebsocketServerTransport` for real-time communication.
- For more details on the MeetingBaas APIs and functionalities, please refer to the official MeetingBaas documentation.

## Example Usage
After setting up everything, the bot will actively join the meeting and communicate using the MeetingBaas WebSocket API. You can test different bot behaviors by modifying the `meetingbaas.py` script to suit your meeting requirements.

Happy meeting automation!

