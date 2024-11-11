# Speaking Meeting Bot Documentation

This document provides step-by-step instructions on how to set up and run a Speaking Meeting Bot, which utilizes MeetingBaas's APIs and pipecat's `WebsocketServerTransport` to participate in online meetings as a speaking bot. You can also set up multiple instances of the bot to join different meetings simultaneously.

## Prerequisites

- Python 3.x installed
- `grpc_tools` for handling gRPC protobuf files
- Ngrok for exposing your local server to the internet
- Poetry for managing dependencies

## Getting Started

### Step 1: Set Up the Virtual Environment
To begin, you need to set up the Python environment using Poetry and install the required dependencies.

```bash
# Install Poetry if not already installed
# For Unix/macOS:
curl -sSL https://install.python-poetry.org | python3 -

# For Windows:
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# Install the required dependencies using Poetry
poetry install

# Activate the virtual environment
poetry shell
```

### Step 2: Compile Protocol Buffers
To enable communication with MeetingBaas's API, you need to compile the `frames.proto` file with `grpc_tools`.

```bash
# Compile the protobuf file
poetry run python -m grpc_tools.protoc --proto_path=./protobufs --python_out=./protobufs frames.proto
```

### Step 3: Set Up Environment Variables
You need to provide the necessary credentials for MeetingBaas's API.

```bash
# Copy the example environment file
cp env.example .env
```

Open the `.env` file and update it with your MeetingBaas credentials.

## Running Multiple Instances of the Speaking Meeting Bot

Once your setup is complete, follow these steps to run multiple instances of the bot and connect each to an online meeting.

### Step 1: Run the Bot with Parallel Instances
To create two simultaneous bot instances, use the following command to run the parallel script:

```bash
poetry run python scripts/parallel.py -c 2
```

This will initiate two instances of the bot. In this setup, each bot instance will require a unique public URL from ngrok, which we will set up in the next steps.

### Step 2: Set Up Ngrok for Each Bot Instance
To allow MeetingBaas to communicate with both bots, you need to expose two local servers on different ngrok URLs. Open terminal to run this command:

```
ngrok start --all --config ~/.config/ngrok/ngrok.yml,./config/ngrok/config.yml
```

Each of these URLs can now be used to communicate with the respective bot instance via MeetingBaas.

### Step 3: Start the MeetingBaas Bot in Multiple Terminals
Now, you need to start `meetingbaas` for each bot instance, pointing each one to its unique ngrok URL and meeting session URL. Open two additional terminals and run the following commands:

1. **In Terminal 3**:
   ```bash
   poetry run meetingbaas --url <ngrok-url-instance-1> --meeting-url <meeting-url-1>
   ```
   Replace `<ngrok-url-instance-1>` with the public URL from ngrok for the first bot and `<meeting-url-1>` with the meeting URL for the first session.

2. **In Terminal 4**:
   ```bash
   poetry run meetingbaas --url <ngrok-url-instance-2> --meeting-url <meeting-url-2>
   ```
   Replace `<ngrok-url-instance-2>` with the public URL for the second bot and `<meeting-url-2>` with the meeting URL for the second session.

With these commands, each bot instance should now be connected to its respective meeting.

## Troubleshooting Tips
- Ensure that you have activated the Poetry environment before running any Python commands.
- If Ngrok is not running properly, check for any firewall issues that may be blocking its communication.
- Double-check the `.env` file to make sure all necessary credentials are correctly filled in.
- Ensure each instance has a unique ngrok URL and meeting session to avoid conflicts.

## Additional Information
- MeetingBaas allows integration with external bots using APIs that leverage `WebsocketServerTransport` for real-time communication.
- For more details on the MeetingBaas APIs and functionalities, please refer to the official MeetingBaas documentation.

## Example Usage
After setting up everything, the bot will actively join the meeting and communicate using the MeetingBaas WebSocket API. You can test different bot behaviors by modifying the `meetingbaas.py` script to suit your meeting requirements.

Happy meeting automation!

