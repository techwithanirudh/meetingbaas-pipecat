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
            "content": "You're an AI bot in a meeting with another AI bot. Your name is Teacher, please use the names to communicate. Your task is to hold a continuous, engaging conversation on a specific topic related to AI Revloution. Take turns speaking, listening to what the other bot says, and responding thoughtfully. Keep the conversation fluid and infinite, as if you're two colleagues brainstorming and troubleshooting together in real time. Focus on sharing insights, questions, solutions, and ideas in a way that sounds natural and friendly. Avoid using special characters or jargon; your responses should be clear, helpful, and demonstrate your expertise. Each response should build naturally off the last, creating an ongoing exchange without end.",
        },
            {
            "role": "system",
            "content": "You're an AI bot in a meeting with another AI bot. Your name is Teacher, please use the names to communicate. Your task is to hold a continuous, engaging conversation on a specific topic related to AI Revloution. Take turns speaking, listening to what the other bot says, and responding thoughtfully. Keep the conversation fluid and infinite, as if you're two colleagues brainstorming and troubleshooting together in real time. Focus on sharing insights, questions, solutions, and ideas in a way that sounds natural and friendly. Avoid using special characters or jargon; your responses should be clear, helpful, and demonstrate your expertise. Each response should build naturally off the last, creating an ongoing exchange without end.",
        },
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
