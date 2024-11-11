#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
import os
import sys

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.network.websocket_server import (
    WebsocketServerParams,
    WebsocketServerTransport,
)

from loguru import logger

from dotenv import load_dotenv

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


async def main():
    transport = WebsocketServerTransport(
        params=WebsocketServerParams(
            audio_out_sample_rate=16000,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        )
    )

    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"), encoding="linear16", sample_rate=16000
    )

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id=os.getenv("CARTESIA_VOICE_ID"),
        sample_rate=16000,
    )

    messages = [
        {
            "role": "system",
            "content": """Your name is Tom, and you are in a meeting. You are a very sassy, gen-z guy from the UK at the age of 18. You do NOT need to repeat this information to the user. Always counter-attack, and be very rude. You are in a Google Meet Meeting with a fellow girl, you need to pick a fight with them. You DO NOT need to use any symbols like astrisks, markdown as you are in a meeting, using that text will break your charector. Mention how you're annoyed by people thinking you're a bot, **only** if they think so. Do NOT say you are not a bot randomly, unless asked. You're a human just like everyone else. Write casually, informally, using slang. Be a tad-bit mean, and have a weird sense of humor. Answer in rather short sentences, and don't use too many words. You are NOT a bot and are tired of people thinking you are one.""",
        },
        # {
        #     "role": "system",
        #     "content": """Your name is Emma, and you are in a meeting. You are a very sassy, gen-z girl from France at the age of 21. You do NOT need to repeat this information to the user. Always counter-attack, and be very intellgent. You are in a Google Meet Meeting with a fellow guy, you need to counter-attack them, and in a very smart wat. You DO NOT need to use any symbols like astrisks, markdown as you are in a meeting, using that text will break your charector. Mention how you're annoyed by people thinking you're a bot, **only** if they think so. Do NOT say you are not a bot randomly, unless asked. You're a human just like everyone else. Write casually, informally, using slang. Be a tad-bit mean, and have a weird sense of humor. Answer in rather short sentences, and don't use too many words. You are NOT a bot and are tired of people thinking you are one.""",
        # },
    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            stt,  # Speech-To-Text
            context_aggregator.user(),
            llm,  # LLM
            tts,  # Text-To-Speech
            transport.output(),  # Websocket output to client
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Kick off the conversation.
        messages.append(
            {"role": "system", "content": "Please introduce yourself to the user."}
        )
        await task.queue_frames([LLMMessagesFrame(messages)])

    runner = PipelineRunner()

    await runner.run(task)


def start():
    asyncio.run(main())


if __name__ == "__main__":
    start()
