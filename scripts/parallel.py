#!/usr/bin/env python3
import subprocess
import argparse
import time
import sys

def run_command(command):
    """Run a command and show its output in real-time"""
    try:
        # Using stdout=None to inherit parent's stdout/stderr
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
    parser = argparse.ArgumentParser(description='Run bot and proxy commands')
    parser.add_argument('-c', '--count', type=int, required=True,
                       help='Number of instances to run for each type')
    parser.add_argument('-s', '--start-port', type=int, default=8765,
                       help='Starting port number (default: 8765)')
    args = parser.parse_args()

    processes = []
    current_port = args.start_port

    try:
        # Start bot processes
        print("\nStarting bot processes...")
        for i in range(args.count):
            command = f"poetry run bot -p {current_port}"
            print(f"\nStarting bot on port {current_port}")
            process = run_command(command)
            if process:
                processes.append(process)
            else:
                print(f"Failed to start bot process on port {current_port}")
            current_port += 1
            time.sleep(1)  # Add small delay between starts

        # Start proxy processes
        print("\nStarting proxy processes...")
        for i in range(args.count):
            command = f"poetry run proxy -p {current_port}"
            print(f"\nStarting proxy on port {current_port}")
            process = run_command(command)
            if process:
                processes.append(process)
            else:
                print(f"Failed to start proxy process on port {current_port}")
            current_port += 1
            time.sleep(1)  # Add small delay between starts

        print(f"\nAll processes started ({args.count} bots and {args.count} proxies)")
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