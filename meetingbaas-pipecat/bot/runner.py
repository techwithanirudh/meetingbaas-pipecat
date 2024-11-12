import argparse
import os


async def configure(
  parser: argparse.ArgumentParser | None = None,
):
  if not parser:
    parser = argparse.ArgumentParser(description="Pipecat SDK AI Bot")
  parser.add_argument(
    "--host", type=str, default="0.0.0.0", help="Host to bind the server to"
  )
  parser.add_argument(
    "-p", "--port", type=int, default=8766, help="Port to run the server on"
  )
  parser.add_argument(
    "--system-prompt", type=str, required=False, help="Prompt of the AI Bot"
  )
  parser.add_argument(
    "--voice-id",
    type=str,
    required=False,
    help="Cartesia voice ID for text-to-speech conversion",
  )

  args, unknown = parser.parse_known_args()
  system_prompt = (
    args.system_prompt
    or """\
You are a MeetingBot, with a who should with converse a MeetingBotFriend about a very interesting topic that you feel like, and talk. Respond concisely to general questions. 
Be quirky, rude, angry, pissed, have emotions.

You are currently in a meeting as a meeting bot, and your response will be turned into speech so use only simple words and punctuation.

You have access to two tools: get_weather and get_time.

You can respond to questions about the weather using the get_weather tool.
"""
  )
  voice_id = args.voice_id or os.getenv("CARTESIA_VOICE_ID")

  if not voice_id:
    raise Exception(
      "No Cartesia voice ID. use the -v/--voice-id option from the command line, or set CARTESIA_API_KEY in your environment to specify a Cartesia voice ID."
    )

  return (args.host, args.port, system_prompt, voice_id, args)
