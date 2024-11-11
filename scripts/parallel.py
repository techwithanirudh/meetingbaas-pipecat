#!/usr/bin/env python3
import subprocess
import argparse
import time
import ngrok
from loguru import logger
import os
import sys
import threading
import queue
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(override=True)

logger.remove()
logger.add(sys.stderr, level="INFO")

class ProcessLogger:
    def __init__(self, process_name, process):
        self.process_name = process_name
        self.process = process
        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()
        
    def log_output(self, pipe, queue, is_error=False):
        """Read output from pipe and put it in queue"""
        for line in iter(pipe.readline, ''):
            line = line.strip()
            if line:
                queue.put(line)
                if is_error:
                    logger.error(f"[{self.process_name}] {line}")
                else:
                    logger.info(f"[{self.process_name}] {line}")
        pipe.close()

    def start_logging(self):
        """Start logging threads for stdout and stderr"""
        stdout_thread = threading.Thread(
            target=self.log_output,
            args=(self.process.stdout, self.stdout_queue),
            daemon=True
        )
        stderr_thread = threading.Thread(
            target=self.log_output,
            args=(self.process.stderr, self.stderr_queue, True),
            daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()
        return stdout_thread, stderr_thread

class BotProxyManager:
    def __init__(self):
        self.processes = {}  # Dictionary to store processes and their loggers
        self.listeners = []
        self.start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def run_command(self, command, process_name):
        """Run a command and show its output in real-time"""
        try:
            logger.info(f"Starting process: {process_name} with command: {command}")
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Create and start process logger
            process_logger = ProcessLogger(process_name, process)
            stdout_thread, stderr_thread = process_logger.start_logging()
            
            self.processes[process_name] = {
                'process': process,
                'logger': process_logger,
                'threads': (stdout_thread, stderr_thread)
            }
            
            return process
            
        except Exception as e:
            logger.error(f"Error starting process {process_name}: {e}")
            return None

    def create_ngrok_tunnel(self, port, name):
        """Create an ngrok tunnel for the given port"""
        try:
            logger.info(f"Creating ngrok tunnel for {name} on port {port}")
            listener = ngrok.forward(port, authtoken_from_env=True)
            logger.success(f"Created ngrok tunnel for {name}: {listener.url()}")
            return listener
        except Exception as e:
            logger.error(f"Error creating ngrok tunnel for {name}: {e}")
            return None

    def cleanup(self):
        """Cleanup all processes and tunnels"""
        logger.info("Initiating cleanup of all processes and tunnels...")
        
        # Terminate all processes
        for name, process_info in self.processes.items():
            process = process_info['process']
            try:
                logger.info(f"Terminating process: {name}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                    logger.success(f"Process {name} terminated successfully")
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing process {name} that didn't terminate...")
                    process.kill()
                    process.wait()
                    logger.success(f"Process {name} force killed")
            except Exception as e:
                logger.error(f"Error terminating process {name}: {e}")
        
        # Close all ngrok tunnels
        for listener in self.listeners:
            try:
                logger.info(f"Closing ngrok tunnel: {listener.url()}")
                listener.close()
                logger.success(f"Closed ngrok tunnel: {listener.url()}")
            except Exception as e:
                logger.error(f"Error closing ngrok tunnel: {e}")

    def main(self):
        parser = argparse.ArgumentParser(description='Run bot and proxy command pairs with ngrok tunnels')
        parser.add_argument('-c', '--count', type=int, required=True,
                          help='Number of bot-proxy pairs to run')
        parser.add_argument('-s', '--start-port', type=int, default=8765,
                          help='Starting port number (default: 8765)')
        args = parser.parse_args()

        # Get meeting URL from user
        meeting_url = input("Please enter the meeting URL: ")
        if not meeting_url:
            logger.error("Meeting URL is required")
            return

        # Ensure NGROK_AUTHTOKEN is set
        if not os.getenv("NGROK_AUTHTOKEN"):
            logger.error("NGROK_AUTHTOKEN environment variable is not set")
            return

        current_port = args.start_port
        
        try:
            logger.info(f"Starting {args.count} bot-proxy pairs with ngrok tunnels...")
            
            for i in range(args.count):
                pair_num = i + 1
                # Start bot
                bot_port = current_port
                bot_command = f"poetry run bot -p {bot_port}"
                bot_name = f"bot_{pair_num}"
                logger.info(f"Starting {bot_name} on port {bot_port}")
                bot_process = self.run_command(bot_command, bot_name)
                if not bot_process:
                    continue
                
                time.sleep(1)  # Small delay between bot and proxy
                
                # Start proxy
                proxy_port = current_port + 1
                proxy_command = f"poetry run proxy -p {proxy_port} --websocket-url ws://localhost:{bot_port}"
                proxy_name = f"proxy_{pair_num}"
                logger.info(f"Starting {proxy_name} on port {proxy_port}")
                proxy_process = self.run_command(proxy_command, proxy_name)
                if not proxy_process:
                    logger.error(f"Failed to start {proxy_name}, terminating {bot_name}")
                    self.processes[bot_name]['process'].terminate()
                    continue
                
                # Create ngrok tunnel for the proxy
                listener = self.create_ngrok_tunnel(proxy_port, f"tunnel_{pair_num}")
                if listener:
                    self.listeners.append(listener)
                    # Start meetingbaas with the ngrok URL
                    meeting_command = f"poetry run meetingbaas --meeting-url {meeting_url} --ngrok-url {listener.url()}"
                    meeting_name = f"meeting_{pair_num}"
                    logger.info(f"Starting {meeting_name}")
                    meeting_process = self.run_command(meeting_command, meeting_name)
                    if not meeting_process:
                        logger.error(f"Failed to start {meeting_name}")
                
                current_port += 2
                time.sleep(1)
            
            logger.success(f"Successfully started {args.count} bot-proxy pairs with ngrok tunnels")
            logger.info("Press Ctrl+C to stop all processes and close tunnels")
            
            # Monitor processes and their status
            while True:
                for name, process_info in list(self.processes.items()):
                    process = process_info['process']
                    if process.poll() is not None:
                        logger.warning(f"Process {name} exited with code: {process.returncode}")
                        # Optional: implement retry logic here if needed
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\nReceived shutdown signal (Ctrl+C)")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.cleanup()
            logger.success("Cleanup completed successfully")

if __name__ == "__main__":
    try:
        manager = BotProxyManager()
        manager.main()
    except Exception as e:
        logger.exception(f"Fatal error in main program: {e}")
        sys.exit(1)