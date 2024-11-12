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
import asyncio
from datetime import datetime
from contextlib import suppress
from typing import Dict, List, Tuple, Optional
import json

from dotenv import load_dotenv

load_dotenv(override=True)

logger.remove()
logger.add(sys.stderr, level="INFO")


def validate_url(url):
  """Validates the URL format, ensuring it starts with https://"""
  if not url.startswith("https://"):
    raise ValueError("URL must start with https://")
  return url


def get_user_input(prompt, validator=None):
  while True:
    user_input = input(prompt).strip()
    if validator:
      try:
        return validator(user_input)
      except ValueError as e:
        logger.warning(f"Invalid input received: {e}")
    else:
      return user_input


class ProcessLogger:
  def __init__(self, process_name: str, process: subprocess.Popen):
    self.process_name = process_name
    self.process = process
    self.stdout_queue: queue.Queue = queue.Queue()
    self.stderr_queue: queue.Queue = queue.Queue()
    self._stop_event = threading.Event()

  def log_output(self, pipe, queue: queue.Queue, is_error: bool = False) -> None:
    """Log output from a pipe to a queue and logger"""
    try:
      for line in iter(pipe.readline, ""):
        if self._stop_event.is_set():
          break
        line = line.strip()
        if line:
          queue.put(line)
          log_msg = f"[{self.process_name}] {line}"
          print(log_msg)
    finally:
      pipe.close()

  def start_logging(self) -> Tuple[threading.Thread, threading.Thread]:
    """Start logging threads for stdout and stderr"""
    stdout_thread = threading.Thread(
      target=self.log_output, args=(self.process.stdout, self.stdout_queue), daemon=True
    )
    stderr_thread = threading.Thread(
      target=self.log_output,
      args=(self.process.stderr, self.stderr_queue, True),
      daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    return stdout_thread, stderr_thread

  def stop(self) -> None:
    """Stop the logging threads gracefully"""
    self._stop_event.set()


class BotProxyManager:
  def __init__(self):
    self.processes: Dict = {}
    self.listeners: List = []
    self.start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    self.shutdown_event = asyncio.Event()

  async def create_ngrok_tunnel(self, port: int, name: str) -> Optional[ngrok.Listener]:
    """Create an ngrok tunnel for the given port"""
    try:
      logger.info(f"Creating ngrok tunnel for {name} on port {port}")
      listener = await ngrok.forward(port, authtoken_from_env=True)
      logger.success(f"Created ngrok tunnel for {name}: {listener.url()}")
      return listener
    except Exception as e:
      logger.error(f"Error creating ngrok tunnel for {name}: {e}")
      return None

  def run_command(self, command: str, process_name: str) -> Optional[subprocess.Popen]:
    """Run a command and set up logging for its output"""
    try:
      logger.info(f"Starting process: {process_name} with command: {command}")
      process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
      )

      process_logger = ProcessLogger(process_name, process)
      stdout_thread, stderr_thread = process_logger.start_logging()

      self.processes[process_name] = {
        "process": process,
        "logger": process_logger,
        "threads": (stdout_thread, stderr_thread),
      }

      return process

    except Exception as e:
      logger.error(f"Error starting process {process_name}: {e}")
      return None

  async def cleanup(self) -> None:
    """Cleanup all processes and tunnels"""
    logger.info("Initiating cleanup of all processes and tunnels...")

    # First close ngrok tunnels
    for listener in self.listeners:
      try:
        tunnel_url = listener.url()
        logger.info(f"Closing ngrok tunnel: {tunnel_url}")
        with suppress(Exception):
          await listener.close()
        logger.success(f"Successfully closed ngrok tunnel: {tunnel_url}")
      except Exception as e:
        logger.error(f"Error closing ngrok tunnel: {e}")

    # Then terminate all processes
    for name, process_info in self.processes.items():
      process = process_info["process"]
      process_logger = process_info["logger"]
      try:
        logger.info(f"Terminating process: {name}")
        process_logger.stop()  # Stop logging threads gracefully
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

  async def monitor_processes(self) -> None:
    """Monitor running processes and handle failures"""
    while not self.shutdown_event.is_set():
      try:
        for name, process_info in list(self.processes.items()):
          process = process_info["process"]
          if process.poll() is not None:
            logger.warning(f"Process {name} exited with code: {process.returncode}")
            # Could add restart logic here if needed
        await asyncio.sleep(1)
      except asyncio.CancelledError:
        break
      except Exception as e:
        logger.error(f"Error monitoring processes: {e}")
        await asyncio.sleep(1)

  async def async_main(self) -> None:
    parser = argparse.ArgumentParser(
      description="Run bot and proxy command pairs with ngrok tunnels"
    )
    parser.add_argument(
      "--args",
      type=str,
      required=True,
      help="JSON-like structure of arguments for each iteration",
    )
    parser.add_argument(
      "-s",
      "--start-port",
      type=int,
      default=8765,
      help="Starting port number (default: 8765)",
    )
    parser.add_argument(
      "--meeting-url", help="The meeting URL (must start with https://)"
    )
    args = parser.parse_args()

    try:
      args_list = json.loads(args.args)
    except json.JSONDecodeError:
      logger.error("Invalid JSON structure provided for --args")
      return

    meeting_url = args.meeting_url
    if not args.meeting_url:
      logger.info("Prompting for meeting URL")
      meeting_url = get_user_input(
        "Enter the meeting URL (must start with https://): ", validate_url
      )

    if not os.getenv("NGROK_AUTHTOKEN"):
      logger.error("NGROK_AUTHTOKEN environment variable is not set")
      return

    current_port = args.start_port

    try:
      logger.info(f"Starting {len(args_list)} bot-proxy pairs with ngrok tunnels...")

      for arg_set in args_list:
        pair_num = arg_set.get("id", 0)
        bot_args = arg_set.get("bot", [])
        proxy_args = arg_set.get("proxy", [])
        meeting_args = arg_set.get("meeting", [])

        # Start bot
        bot_port = current_port
        bot_name = f"bot_{pair_num}"
        bot_command = f"poetry run bot -p {bot_port} {' '.join(bot_args)}"
        bot_process = self.run_command(bot_command, bot_name)
        if not bot_process:
          continue

        await asyncio.sleep(1)

        # Start proxy
        proxy_port = current_port + 1
        proxy_name = f"proxy_{pair_num}"
        proxy_command = f"poetry run proxy -p {proxy_port} --websocket-url ws://localhost:{bot_port} {' '.join(proxy_args)}"
        proxy_process = self.run_command(proxy_command, proxy_name)
        if not proxy_process:
          logger.error(f"Failed to start {proxy_name}, terminating {bot_name}")
          self.processes[bot_name]["process"].terminate()
          continue

        # Create ngrok tunnel for the proxy
        listener = await self.create_ngrok_tunnel(proxy_port, f"tunnel_{pair_num}")
        if listener:
          self.listeners.append(listener)
          meeting_name = f"meeting_{pair_num}"
          meeting_command = f"poetry run meetingbaas --meeting-url {meeting_url} --ngrok-url {listener.url()} {' '.join(meeting_args)}"
          meeting_process = self.run_command(meeting_command, meeting_name)
          if not meeting_process:
            logger.error(f"Failed to start {meeting_name}")

        current_port += 2
        await asyncio.sleep(1)

      logger.success(
        f"Successfully started {len(args_list)} bot-proxy pairs with ngrok tunnels"
      )
      logger.info("Press Ctrl+C to stop all processes and close tunnels")

      # Start process monitor
      monitor_task = asyncio.create_task(self.monitor_processes())

      try:
        await self.shutdown_event.wait()
      except asyncio.CancelledError:
        logger.info("\nReceived shutdown signal")
      finally:
        self.shutdown_event.set()
        await monitor_task

    except KeyboardInterrupt:
      logger.info("\nReceived shutdown signal (Ctrl+C)")
    except Exception as e:
      logger.error(f"Unexpected error: {e}")
    finally:
      await self.cleanup()
      logger.success("Cleanup completed successfully")

  def main(self) -> None:
    """Main entry point with proper signal handling"""
    try:
      if sys.platform != "win32":
        # Set up signal handlers for Unix-like systems
        import signal

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def signal_handler():
          self.shutdown_event.set()

        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)

        try:
          loop.run_until_complete(self.async_main())
        finally:
          loop.close()
      else:
        # Windows doesn't support loop.add_signal_handler
        asyncio.run(self.async_main())
    except Exception as e:
      logger.exception(f"Fatal error in main program: {e}")
      sys.exit(1)


if __name__ == "__main__":
  manager = BotProxyManager()
  manager.main()
