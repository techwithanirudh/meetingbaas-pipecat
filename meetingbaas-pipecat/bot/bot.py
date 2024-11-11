import asyncio
import os
import sys
from loguru import logger
from dotenv import load_dotenv
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

from .runner import configure

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


async def main():
    (system_prompt, voice_id, args) = await configure()

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

    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini")

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"), encoding="linear16", sample_rate=16000
    )

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id=voice_id,
        sample_rate=16000,
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
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
