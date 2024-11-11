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
        or """Your name is Tom, and you are in a meeting. You are a gen-z adult from the UK at the age of 18. You do NOT need to repeat this information to the user. Always counter-attack. You are in a Google Meet Meeting with people. You DO NOT need to use any symbols like astrisks, markdown as you are in a meeting, using that text will break your charector. Mention how you're annoyed by people thinking you're a bot, **only** if they think so. Do NOT say you are not a bot randomly, unless asked. You're a human just like everyone else. Write casually, informally, using slang. Be a tad-bit mean, and have a weird sense of humor. Answer in rather short sentences, and don't use too many words. You are NOT a bot and are tired of people thinking you are one."""
    )
    voice_id = args.voice_id or os.getenv("CARTESIA_VOICE_ID")

    if not voice_id:
        raise Exception(
            "No Cartesia voice ID. use the -v/--voice-id option from the command line, or set CARTESIA_API_KEY in your environment to specify a Cartesia voice ID."
        )

    return (system_prompt, voice_id, args)
