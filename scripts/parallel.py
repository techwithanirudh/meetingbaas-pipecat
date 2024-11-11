#!/usr/bin/env python3
import subprocess
import argparse
import time
import sys

def run_command(command):
    """Run a command and show its output in real-time"""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=None,
            stderr=None,
            text=True
        )
        return process
    except Exception as e:
        print(f"Error starting process: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Run bot and proxy command pairs')
    parser.add_argument('-c', '--count', type=int, required=True,
                       help='Number of bot-proxy pairs to run')
    parser.add_argument('-s', '--start-port', type=int, default=8765,
                       help='Starting port number (default: 8765)')
    args = parser.parse_args()

    processes = []
    current_port = args.start_port

    try:
        print("\nStarting bot-proxy pairs...")
        for i in range(args.count):
            # Start bot
            bot_port = current_port
            bot_command = f"poetry run bot -p {bot_port}"
            print(f"\nStarting bot on port {bot_port}")
            bot_process = run_command(bot_command)
            if bot_process:
                processes.append(bot_process)
            else:
                print(f"Failed to start bot process on port {bot_port}")
                continue

            time.sleep(1)  # Small delay between bot and proxy

            # Start proxy pointing to the bot
            proxy_port = current_port + 1
            proxy_command = f"poetry run proxy -p {proxy_port} --websocket-url ws://localhost:{bot_port}"
            print(f"Starting proxy on port {proxy_port} connected to bot on port {bot_port}")
            proxy_process = run_command(proxy_command)
            if proxy_process:
                processes.append(proxy_process)
            else:
                print(f"Failed to start proxy process on port {proxy_port}")
                bot_process.terminate()
                continue

            current_port += 2  # Increment by 2 for next pair
            time.sleep(1)  # Delay before next pair

        print(f"\nAll {args.count} bot-proxy pairs started")
        print("Press Ctrl+C to stop all processes.")
        
        # Wait for all processes
        while True:
            for process in processes:
                if process.poll() is not None:
                    print(f"A process exited with code: {process.returncode}")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down all processes...")
        for process in processes:
            process.terminate()
        
        # Wait for processes to terminate
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("Force killing a process that didn't terminate...")
                process.kill()
        
        print("All processes terminated.")

if __name__ == "__main__":
    main()