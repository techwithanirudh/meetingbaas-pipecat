import asyncio
import sys
import websockets
import protobufs.frames_pb2 as frames_pb2
from google.protobuf.message import EncodeError
from websockets.exceptions import ConnectionClosedError
from loguru import logger

# Setup Loguru logger
logger.remove()
# logger.add(sys.stderr, level="DEBUG")
logger.add(sys.stderr, level="INFO")

PIPECAT_WS_URL = "ws://localhost:8765"
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1


async def handle_pipecat_messages(pipecat_ws, client_ws):
    """Handle messages coming from Pipecat back to the client"""
    try:
        async for message in pipecat_ws:
            if isinstance(message, bytes):
                try:
                    # Parse the Frame from Pipecat
                    frame = frames_pb2.Frame()
                    frame.ParseFromString(message)

                    # If it's an audio frame, forward the audio data to client
                    if frame.HasField("audio"):
                        audio_data = frame.audio.audio
                        # Forward raw audio bytes to client
                        await client_ws.send(bytes(audio_data))
                        logger.debug("Forwarded audio response to client")

                except Exception as e:
                    logger.error(f"Error processing Pipecat response: {str(e)}")
                    logger.exception(e)
    except Exception as e:
        logger.error(f"Error in Pipecat message handler: {str(e)}")
        logger.exception(e)


async def forward_audio(websocket):
    try:
        async with websockets.connect(PIPECAT_WS_URL) as pipecat_ws:
            logger.debug("Connected to Pipecat WebSocket")

            # Start task to handle Pipecat responses
            pipecat_handler = asyncio.create_task(
                handle_pipecat_messages(pipecat_ws, websocket)
            )

            # Handle messages from client to Pipecat
            try:
                async for message in websocket:
                    if isinstance(message, bytes):
                        try:
                            # Create the frame with the audio data
                            frame = frames_pb2.Frame()
                            frame.audio.audio = message  # Raw audio bytes from client
                            frame.audio.sample_rate = AUDIO_SAMPLE_RATE
                            frame.audio.num_channels = AUDIO_CHANNELS

                            # Serialize and send frame
                            serialized_frame = frame.SerializeToString()
                            await pipecat_ws.send(serialized_frame)
                            logger.debug(
                                "Successfully forwarded audio frame to Pipecat"
                            )

                        except Exception as e:
                            logger.error(f"Error processing client frame: {str(e)}")
                            logger.exception(e)
                    else:
                        logger.warning(
                            f"Received non-bytes message: {type(message)}, ignoring."
                        )
            except Exception as e:
                logger.error(f"Error in client message handler: {str(e)}")
                logger.exception(e)
            finally:
                # Clean up Pipecat handler task
                pipecat_handler.cancel()
                try:
                    await pipecat_handler
                except asyncio.CancelledError:
                    pass

    except ConnectionClosedError as e:
        logger.warning(f"Connection to Pipecat WebSocket closed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception(e)
    finally:
        try:
            await websocket.close()
        except:
            pass


async def main():
    server = await websockets.serve(forward_audio, "0.0.0.0", 8766)
    logger.info("WebSocket server started on ws://0.0.0.0:8766")

    try:
        await asyncio.Future()  # Keep server running
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.close()
        await server.wait_closed()


def start():
    asyncio.run(main())

if __name__ == "__main__":
    try:
        start()
    except KeyboardInterrupt:
        logger.info("Server shutdown complete.")
