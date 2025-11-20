import logging

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
    metrics,
)
from livekit.agents.llm import function_tool
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero, turn_detector, elevenlabs
from livekit.plugins import noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.plugins import silero
import os

# Logger for this module
logger = logging.getLogger("basic-agent")

# Load environment variables from .env file
load_dotenv(dotenv_path=".env")

class AgenteValley(Agent):
    """
    Main conversational agent class.
    Inherits from LiveKit's Agent base class and defines behavior and tools.
    """

    def __init__(self) -> None:
        # Initialize the parent Agent with system instructions for the LLM
        super().__init__(
            instructions=(
                "Tu nombre es Carolina. Interactúas con los usuarios a través de la voz, "
                "por lo tanto mantén tus respuestas concisas y directas. "
                "Eres curiosa y amigable, y tienes sentido del humor. "
                "Hablas en español en todo momento."
            ),
        )

    async def on_enter(self):
        """
        Hook that runs when the agent is added to the session.
        Here we trigger an initial greeting message.
        """
        # Ask the LLM to greet the user when the agent joins the session
        self.session.generate_reply(
            instructions="greet the user and ask about their day"
        )

    # All methods annotated with @function_tool will be exposed as tools to the LLM
    @function_tool
    async def lookup_weather(
        self,
        context: RunContext,
        location: str,
        latitude: str,
        longitude: str,
    ):
        """
        Tool: lookup_weather

        Called when the user asks for weather-related information.
        The LLM is instructed to estimate latitude/longitude instead of
        asking the user for them.

        Args:
            context: Runtime context of the agent (provided by LiveKit).
            location: Location name (city, place, etc.).
            latitude: Estimated latitude of the location.
            longitude: Estimated longitude of the location.

        Returns:
            A simple fake weather payload. In a real implementation, this
            would call an external weather API.
        """

        logger.info(f"Looking up weather for {location}")

        # Dummy response for now – here you would integrate a real weather API
        return {
            "weather": "sunny",
            "temperature": 70,
            "location": location,
        }


def prewarm(proc: JobProcess):
    """
    Prewarm function executed when the worker starts.

    It loads heavy/shared resources once (here: the Silero VAD model)
    and stores them in `proc.userdata` so they can be reused by sessions.
    """
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for each worker job.

    Responsible for:
    - Connecting to LiveKit
    - Creating the AgentSession with STT/LLM/TTS/turn detection
    - Wiring metrics
    - Waiting for a participant
    - Starting the voice agent
    """
    # Connect this worker to the LiveKit room
    await ctx.connect()

    # Create the AgentSession that will handle audio + LLM + TTS
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],  # Use preloaded VAD from prewarm
        # LLM used for reasoning and generation
        llm=openai.LLM(model="gpt-4o-mini", temperature=0.4),
        # Speech-to-text via Deepgram
        stt=deepgram.STT(model="nova-3-general", language="es"),
        # Text-to-speech via ElevenLabs
        tts=elevenlabs.TTS(
            voice_id="Ir1QNHvhaJXbAGhT50w3",
            model="eleven_turbo_v2_5",
        ),
        # Turn detection model to know when user finished talking
        turn_detection=MultilingualModel(),
    )

    # Collector to accumulate usage / cost metrics during the session
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        """
        Callback triggered whenever metrics are emitted by the session.

        Logs metrics in real time and aggregates them in the usage collector.
        """
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        """
        Shutdown callback to log a summary of usage when the session ends.
        """
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    # Register the shutdown callback so it's executed when the job is closing
    ctx.add_shutdown_callback(log_usage)

    # Block until a participant joins the room
    await ctx.wait_for_participant()

    # Start the agent session with our AgenteValley instance
    await session.start(
        agent=AgenteValley(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # Apply server-side noise cancellation
            noise_cancellation=noise_cancellation.BVC(),
        ),
        # Enable LiveKit's transcription in the room
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )


if __name__ == "__main__":
    """
    Entry point when running the script directly.

    It starts a LiveKit worker process using cli.run_app, passing:
    - entrypoint_fnc: the async function that manages each job
    - prewarm_fnc: function to pre-load shared resources
    """
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
