#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#
import argparse
import os


async def configure(
    parser: argparse.ArgumentParser | None = None,
):
    if not parser:
        parser = argparse.ArgumentParser(description="Pipecat SDK AI Bot")
    parser.add_argument(
        "-s", "--system-prompt", type=str, required=False, help="Prompt of the AI Bot"
    )
    parser.add_argument(
        "-v",
        "--voice-id",
        type=str,
        required=False,
        help="Daily API Key (needed to create an owner token for the room)",
    )

    args, unknown = parser.parse_known_args()

    system_prompt = (
        args.system_prompt
        or """\
You are a helpful assistant who converses with a user and answers questions. Respond concisely to general questions.

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

    return (system_prompt, voice_id, args)
