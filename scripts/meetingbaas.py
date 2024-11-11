import requests
import os
import uuid
import time
import signal
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("MEETING_BAAS_API_KEY")


def get_user_input():
    while True:
        meeting_url = input(
            "Enter the meeting URL (must start with https://): "
        ).strip()
        if meeting_url.startswith("https://"):
            break
        print("Invalid URL. Please start with https://")

    while True:
        ngrok_url = input("Enter the ngrok URL (must start with https://): ").strip()
        if ngrok_url.startswith("https://"):
            # Convert https:// to wss://
            ngrok_wss = "wss://" + ngrok_url[8:]
            break
        print("Invalid URL. Please start with https://")

    return meeting_url, ngrok_wss


def signal_handler(signum, frame):
    print("\nCtrl+C detected. Cleaning up...")
    if hasattr(signal_handler, "current_bot_id") and signal_handler.current_bot_id:
        delete_bot(signal_handler.current_bot_id)
    print("Bot cleaned up. Exiting...")
    exit(0)


# Set up bot configuration
def create_bot(meeting_url, ngrok_wss):
    url = "https://api.meetingbaas.com/bots"
    headers = {
        "Content-Type": "application/json",
        "x-meeting-baas-api-key": API_KEY,
    }

    # Generate a unique deduplication key for each bot instance
    deduplication_key = str(uuid.uuid4())
    config = {
        "meeting_url": meeting_url,
        "bot_name": "Speaking AI Chatbot",
        "recording_mode": "speaker_view",
        "bot_image": "https://utfs.io/f/N2K2zOxB65CxoosE8GXptM1saLXVc7b5jd62hE9Gq3gZPTKF",
        "entry_message": "I'm ready, you can talk to start chatting!",
        "reserved": False,
        "speech_to_text": {"provider": "Default"},
        "automatic_leave": {
            "waiting_room_timeout": 600  # 10 minutes in seconds
        },
        "deduplication_key": deduplication_key,
        "streaming": {"input": ngrok_wss, "output": ngrok_wss},
    }

    response = requests.post(url, json=config, headers=headers)

    if response.status_code == 200:
        bot_id = response.json().get("bot_id")
        print(f"Bot created successfully with bot_id: {bot_id}")
        return bot_id
    else:
        print("Failed to create bot:", response.json())
        return None


def delete_bot(bot_id):
    delete_url = f"https://api.meetingbaas.com/bots/{bot_id}"
    headers = {
        "Content-Type": "application/json",
        "x-meeting-baas-api-key": API_KEY,
    }
    response = requests.delete(delete_url, headers=headers)

    if response.status_code == 200:
        print(f"Bot with bot_id {bot_id} deleted successfully.")
    else:
        print("Failed to delete bot:", response.json())


def main():
    # Register the signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Get initial URLs
    meeting_url, ngrok_wss = get_user_input()

    while True:
        try:
            # Step 1: Create the bot
            bot_id = create_bot(meeting_url, ngrok_wss)

            # Store the current bot_id in the signal handler
            signal_handler.current_bot_id = bot_id

            # Check if bot was created successfully
            if not bot_id:
                print("Bot creation failed. Retrying...")
                time.sleep(5)  # Wait a bit before retrying
                continue

            # Wait for user input to respawn bot
            print("\nPress Enter to respawn bot with same URLs")
            print("Press 'n' + Enter to input new URLs")
            print("Press Ctrl+C to exit")

            user_choice = input().strip().lower()

            # Delete the current bot
            delete_bot(bot_id)
            signal_handler.current_bot_id = None

            # Check if user wants to input new URLs
            if user_choice == "n":
                meeting_url, ngrok_wss = get_user_input()

        except Exception as e:
            print(f"An error occurred: {e}")
            if (
                hasattr(signal_handler, "current_bot_id")
                and signal_handler.current_bot_id
            ):
                delete_bot(signal_handler.current_bot_id)
                signal_handler.current_bot_id = None
            time.sleep(5)


if __name__ == "__main__":
    main()
