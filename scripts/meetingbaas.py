import requests
import os
import uuid
import time
import signal
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("MEETING_BAAS_API_KEY")

def validate_url(url, url_type):
    """Validates the URL format, ensuring it starts with https://"""
    while not url.startswith("https://"):
        url = input(f"Enter the {url_type} (must start with https://): ").strip()
        if url.startswith("https://"):
            break
        print("Invalid URL. Please start with https://")
    return url

def get_user_input(meeting_url, ngrok_url):
    meeting_url = validate_url(meeting_url, "meeting URL")
    ngrok_url = validate_url(ngrok_url, "ngrok URL")
    ngrok_wss = "wss://" + ngrok_url[8:]
    return meeting_url, ngrok_wss

def signal_handler(signum, frame):
    print("\nCtrl+C detected. Cleaning up...")
    if hasattr(signal_handler, "current_bot_id") and signal_handler.current_bot_id:
        delete_bot(signal_handler.current_bot_id)
    print("Bot cleaned up. Exiting...")
    exit(0)

# Set up bot configuration
def create_bot(meeting_url, ngrok_wss, bot_name, bot_image):
    url = "https://api.meetingbaas.com/bots"
    headers = {
        "Content-Type": "application/json",
        "x-meeting-baas-api-key": API_KEY,
    }

    deduplication_key = str(uuid.uuid4())
    config = {
        "meeting_url": meeting_url,
        "bot_name": bot_name,
        "recording_mode": "speaker_view",
        "bot_image": bot_image,
        "entry_message": "I'm ready, you can talk to start chatting!",
        "reserved": False,
        "speech_to_text": {"provider": "Default"},
        "automatic_leave": {"waiting_room_timeout": 600},
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
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(description="Meeting BaaS Bot")
    parser.add_argument("--meeting-url", required=True, help="The meeting URL (must start with https://)")
    parser.add_argument("--ngrok-url", required=True, help="The ngrok URL (must start with https://)")
    parser.add_argument("--bot-name", required=False, default="Teacher", help="The name of the bot which is going to join the meeting.")
    parser.add_argument("--bot-image", required=False, default="https://utfs.io/f/dvmZj7IPboXItfgbYN3fapy07gFYwMHGebAkQB43UCtNx1JZ", help="The image of the bot which is going to join the meeting.")

    args = parser.parse_args()

    meeting_url, ngrok_wss = get_user_input(args.meeting_url, args.ngrok_url)

    while True:
        try:
            bot_id = create_bot(meeting_url, ngrok_wss, args.bot_name, args.bot_image)
            signal_handler.current_bot_id = bot_id

            if not bot_id:
                print("Bot creation failed. Retrying...")
                time.sleep(5)
                continue

            print("\nPress Enter to respawn bot with same URLs")
            print("Press 'n' + Enter to input new URLs")
            print("Press Ctrl+C to exit")
            user_choice = input().strip().lower()

            delete_bot(bot_id)
            signal_handler.current_bot_id = None

            if user_choice == "n":
                meeting_url, ngrok_wss = get_user_input(args.meeting_url, args.ngrok_url)

        except Exception as e:
            print(f"An error occurred: {e}")
            if hasattr(signal_handler, "current_bot_id") and signal_handler.current_bot_id:
                delete_bot(signal_handler.current_bot_id)
                signal_handler.current_bot_id = None
            time.sleep(5)

if __name__ == "__main__":
    main()
