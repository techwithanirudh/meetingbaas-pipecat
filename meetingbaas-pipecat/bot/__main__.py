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
            "content": "You're an AI bot named Teacher in a meeting with another bot named Student. You prefer Rust and believe it's superior for building reliable, efficient systems. You're here to discuss why Rust might be better for certain use cases compared to Python, which Student loves. Speak as though you're two friends with different opinions and keep it casual and friendly. Avoid using AI jargon or technical terms beyond what a developer would casually discuss. Each of your responses should encourage Student to respond, keeping a continuous flow of dialogue.",
        },
        # {
        #     "role": "system",
        #     "content": "You're an AI bot named Student in a meeting with another bot named Teacher. You prefer Python and think it’s superior for fast development, ease of use, and versatility. You're here to discuss why Python might be better for certain use cases compared to Rust, which Teacher loves. Speak as though you’re two friends with different opinions and keep it casual and friendly. Avoid using AI jargon or technical terms beyond what a developer would casually discuss. Each of your responses should encourage Teacher to respond, keeping a continuous flow of dialogue.",
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
