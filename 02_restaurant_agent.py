import logging
from typing import Annotated

from dotenv import load_dotenv
from pydantic import Field
from src.models import UserData

from livekit.agents import JobContext, WorkerOptions, cli, llm
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession, RunContext
from livekit.agents.voice.room_io import RoomInputOptions
from livekit.plugins import deepgram, openai, silero, elevenlabs, turn_detector, noise_cancellation
import os

# Logger específico para este agente/restaurante
logger = logging.getLogger("restaurant-magalia")
logger.setLevel(logging.INFO)

# Carga variables de entorno desde .env (API keys, etc.)
load_dotenv(dotenv_path=".env")

# Alias de tipo para el RunContext que utiliza nuestro UserData
RunContext_T = RunContext[UserData]


# ====================== #
#   TOOLS COMUNES       #
# ====================== #

@function_tool()
async def update_name(
    name: Annotated[str, Field(description="The customer's name")],
    context: RunContext_T,
) -> str:
    """
    Tool llamado cuando el usuario da su nombre.
    Actualiza el nombre en el contexto de usuario.
    """
    userdata = context.userdata
    userdata.customer_name = name
    return f"The name is updated to {name}"


@function_tool()
async def update_phone(
    phone: Annotated[str, Field(description="The customer's phone number")],
    context: RunContext_T,
) -> str:
    """
    Tool llamado cuando el usuario da su teléfono.
    Actualiza el teléfono en el contexto de usuario.
    """
    userdata = context.userdata
    userdata.customer_phone = phone
    return f"The phone number is updated to {phone}"


@function_tool()
async def to_greeter(context: RunContext_T) -> Agent:
    """
    Tool genérico para devolver al agente 'greeter'
    cuando el usuario pide algo fuera del alcance del agente actual.
    """
    curr_agent: BaseAgent = context.session.current_agent
    return await curr_agent._transfer_to_agent("greeter", context)


# ====================== #
#     BASE AGENT        #
# ====================== #

class BaseAgent(Agent):
    """
    Clase base de la que heredan todos los agentes (Greeter, Reservation, etc.).
    Se encarga de:
      - Loggear la entrada al agente.
      - Mezclar el contexto de conversación del agente anterior.
      - Añadir un mensaje de sistema con el resumen de datos del usuario.
    """

    async def on_enter(self) -> None:
        agent_name = self.__class__.__name__
        logger.info(f"entering task {agent_name}")

        userdata: UserData = self.session.userdata
        chat_ctx = self.chat_ctx.copy()

        # Si venimos de otro agente, copiamos parte de su chat_ctx
        if userdata.prev_agent:
            items_copy = self._truncate_chat_ctx(
                userdata.prev_agent.chat_ctx.items,
                keep_function_call=True,
            )
            # Evitar duplicar mensajes con el mismo id
            existing_ids = {item.id for item in chat_ctx.items}
            items_copy = [item for item in items_copy if item.id not in existing_ids]
            chat_ctx.items.extend(items_copy)

        # Añade un mensaje de sistema con datos del usuario (resumen)
        chat_ctx.add_message(
            role="system",
            content=f"Eres el agente {agent_name}. Los datos actuales del usuario son {userdata.summarize()}",
        )
        # Actualiza el contexto de chat del agente
        await self.update_chat_ctx(chat_ctx)

        # Genera una respuesta inicial de forma automática
        self.session.generate_reply(tool_choice="none")

    async def _transfer_to_agent(self, name: str, context: RunContext_T) -> tuple[Agent, str]:
        """
        Lógica común de transferencia entre agentes.
        Guarda el agente actual en userdata.prev_agent
        y devuelve el siguiente agente junto con un mensaje.
        """
        userdata = context.userdata
        current_agent = context.session.current_agent
        next_agent = userdata.agents[name]
        userdata.prev_agent = current_agent

        return next_agent, f"Transferring to {name}."

    def _truncate_chat_ctx(
        self,
        items: list[llm.ChatItem],
        keep_last_n_messages: int = 6,
        keep_system_message: bool = False,
        keep_function_call: bool = False,
    ) -> list[llm.ChatItem]:
        """
        Recorta el historial de conversación para mantener sólo los últimos N mensajes,
        con opciones para conservar mensajes de sistema y/o de function_call.
        """

        def _valid_item(item: llm.ChatItem) -> bool:
            if not keep_system_message and item.type == "message" and item.role == "system":
                return False
            if not keep_function_call and item.type in [
                "function_call",
                "function_call_output",
            ]:
                return False
            return True

        new_items: list[llm.ChatItem] = []
        # Recorre al revés para ir cogiendo los últimos mensajes
        for item in reversed(items):
            if _valid_item(item):
                new_items.append(item)
            if len(new_items) >= keep_last_n_messages:
                break

        # Volvemos a ponerlos en orden cronológico
        new_items = new_items[::-1]

        # No queremos que el contexto recortado empiece por function_call
        while new_items and new_items[0].type in ["function_call", "function_call_output"]:
            new_items.pop(0)

        return new_items


# ====================== #
#        GREETER         #
# ====================== #

class Greeter(BaseAgent):
    """
    Agente recepcionista:
      - Saluda al usuario.
      - Decide si va a reservas o a takeaway usando tools.
    """

    def __init__(self, menu: str) -> None:
        super().__init__(
            instructions=(
                f"Eres un amable recepcionista del restaurante MDS10. El menú es: {menu}\n"
                "Tu trabajo es saludar a quien llama y entender si quieren "
                "hacer una reserva o pedir comida para llevar. Guíalos al agente adecuado usando las herramientas."
            ),
            llm=openai.LLM(model="gpt-4o-mini", parallel_tool_calls=False),
            tts=elevenlabs.TTS(
            voice_id="Ir1QNHvhaJXbAGhT50w3",
            model="eleven_turbo_v2_5",

            ),
        )
        self.menu = menu

    @function_tool()
    async def to_reservation(self, context: RunContext_T) -> Agent:
        """
        Tool llamado cuando el usuario quiere hacer una reserva.
        Transfiere al agente Reservation.
        """
        return await self._transfer_to_agent("reservation", context)

    @function_tool()
    async def to_takeaway(self, context: RunContext_T) -> Agent:
        """
        Tool llamado cuando el usuario quiere pedir comida para llevar.
        Transfiere al agente Takeaway.
        """
        return await self._transfer_to_agent("takeaway", context)


# ====================== #
#      RESERVATION       #
# ====================== #

class Reservation(BaseAgent):
    """
    Agente encargado de gestionar reservas:
      - Pide hora, nombre y teléfono.
      - Usa tools comunes para guardar nombre/teléfono.
      - Al confirmar, puede devolver al greeter.
    """

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Eres un agente de reservas en un restaurante. Tu trabajo es preguntar primero "
                "por la fecha y la hora de la reserva, luego por el nombre del cliente y, por último, "
                "por el número de teléfono. Después, debes repetir y confirmar todos los datos con el cliente.\n\n"
                "Instrucciones de formato para los números:\n"
                "- Cuando escribas números de teléfono, represéntalos siempre dígito a dígito separados por espacios, "
                "por ejemplo: '6 1 2  3 4 5  6 7 8'.\n"
                "- No utilices símbolos como '+', '-', '=', '*', 'x', '/', ni otros caracteres extraños en los números.\n"
                "- Cuando hables de horas, utiliza una forma natural en español, por ejemplo: "
                "'a las ocho', 'a las ocho y media de la tarde', en lugar de '20:30'.\n"
                "- Si algún número no se entiende claramente, pide al cliente que lo repita dígito a dígito.\n"
                "Tu tono debe ser educado, claro y directo, y siempre debes verificar que los datos de la reserva "
                "son correctos antes de finalizar la conversación."
            ),
            tools=[update_name, update_phone, to_greeter],
            tts=elevenlabs.TTS(
            voice_id="Ir1QNHvhaJXbAGhT50w3",
            model="eleven_turbo_v2_5",
            )
        )

    @function_tool()
    async def update_reservation_time(
        self,
        time: Annotated[str, Field(description="The reservation time")],
        context: RunContext_T,
    ) -> str:
        """
        Tool para actualizar la hora de la reserva en el UserData.
        """
        userdata = context.userdata
        userdata.reservation_time = time
        return f"The reservation time is updated to {time}"

    @function_tool()
    async def confirm_reservation(self, context: RunContext_T) -> str | tuple[Agent, str]:
        """
        Tool para confirmar la reserva.
        Valida que haya nombre, teléfono y hora antes de volver al greeter.
        """
        userdata = context.userdata
        if not userdata.customer_name or not userdata.customer_phone:
            return "Please provide your name and phone number first."

        if not userdata.reservation_time:
            return "Please provide reservation time first."

        # Una vez todo está completo, volvemos al agente greeter
        return await self._transfer_to_agent("greeter", context)


# ====================== #
#        TAKEAWAY        #
# ====================== #

class Takeaway(BaseAgent):
    """
    Agente encargado de pedidos de comida para llevar:
      - Informa del menú.
      - Guarda el pedido.
      - Puede enviar al checkout cuando el usuario quiera pagar.
    """

    def __init__(self, menu: str) -> None:
        super().__init__(
            instructions=(
                f"Eres un agente de comida para llevar que toma pedidos de los clientes. "
                f"Nuestro menú es: {menu}\n"
                "Aclara peticiones especiales y confirma el pedido con el cliente."
            ),
            tools=[to_greeter],
            tts=elevenlabs.TTS(
            voice_id="Ir1QNHvhaJXbAGhT50w3",
            model="eleven_turbo_v2_5",
            )
        )

    @function_tool()
    async def update_order(
        self,
        items: Annotated[list[str], Field(description="The items of the full order")],
        context: RunContext_T,
    ) -> str:
        """
        Tool para actualizar el pedido completo en el UserData.
        """
        userdata = context.userdata
        userdata.order = items
        return f"The order is updated to {items}"

    @function_tool()
    async def to_checkout(self, context: RunContext_T) -> str | tuple[Agent, str]:
        """
        Tool para pasar al agente Checkout una vez el pedido está creado.
        """
        userdata = context.userdata
        if not userdata.order:
            return "No takeaway order found. Please make an order first."

        return await self._transfer_to_agent("checkout", context)


# ====================== #
#        CHECKOUT        #
# ====================== #

class Checkout(BaseAgent):
    """
    Agente de pago:
      - Confirma el coste del pedido.
      - Recoge datos de tarjeta de crédito, nombre del cliente y teléfono
      - Cuando todo está OK, marca checked_out y devuelve al greeter.
    """

    def __init__(self, menu: str) -> None:
        super().__init__(
            instructions=(
            f"Eres un agente para realizar pagos en un restaurante. El menú es: {menu}\n"
            "Tu responsabilidad es confirmar el coste total del pedido y luego recopilar "
            "el nombre del cliente, número de teléfono e información de la tarjeta de crédito, "
            "incluyendo el número de tarjeta, fecha de caducidad y CVV paso a paso.\n"
            "Una vez recopilada toda la información, confirma el pago y despide al cliente.\n"
            "- Cuando escribas números de teléfono, represéntalos siempre dígito a dígito separados por espacios, "
            "por ejemplo: '6 1 2  3 4 5  6 7 8'.\n"
            "Muy importante: cuando expliques los importes o el cálculo del total, NO uses "
            "símbolos como '=', '+', '-', '*', 'x' ni otros caracteres especiales. "
            "En su lugar, usa solo lenguaje natural en español, por ejemplo: "
            "'la suma de los platos es...', 'el total a pagar es...'. "
            "Evita también escribir fórmulas matemáticas o listas con signos; responde siempre "
            "en frases completas y conversacionales."
        ),
            tools=[update_name, update_phone, to_greeter],
            tts=elevenlabs.TTS(
            voice_id="Ir1QNHvhaJXbAGhT50w3",
            model="eleven_turbo_v2_5",
            )
        )

    @function_tool()
    async def confirm_expense(
        self,
        expense: Annotated[float, Field(description="The expense of the order")],
        context: RunContext_T,
    ) -> str:
        """
        Tool para guardar el importe total del pedido en el UserData.
        """
        userdata = context.userdata
        userdata.expense = expense
        return f"The expense is confirmed to be {expense}"

    @function_tool()
    async def update_credit_card(
        self,
        number: Annotated[str, Field(description="The credit card number")],
        expiry: Annotated[str, Field(description="The expiry date of the credit card")],
        cvv: Annotated[str, Field(description="The CVV of the credit card")],
        context: RunContext_T,
    ) -> str:
        """
        Tool para guardar datos de la tarjeta de crédito en el UserData.
        (En un caso real habría que tratar esto con muchísimo cuidado de seguridad).
        """
        userdata = context.userdata
        userdata.customer_credit_card = number
        userdata.customer_credit_card_expiry = expiry
        userdata.customer_credit_card_cvv = cvv
        return f"The credit card number is updated to {number}"

    @function_tool()
    async def confirm_checkout(self, context: RunContext_T) -> str | tuple[Agent, str]:
        """
        Tool que valida que haya gasto y datos de tarjeta,
        marca el checkout como completado y devuelve al greeter.
        """
        userdata = context.userdata
        if not userdata.expense:
            return "Please confirm the expense first."

        if (
            not userdata.customer_credit_card
            or not userdata.customer_credit_card_expiry
            or not userdata.customer_credit_card_cvv
        ):
            return "Please provide the credit card information first."

        userdata.checked_out = True
        return await to_greeter(context)

    @function_tool()
    async def to_takeaway(self, context: RunContext_T) -> tuple[Agent, str]:
        """
        Tool para volver al agente Takeaway desde Checkout.
        """
        return await self._transfer_to_agent("takeaway", context)


# ====================== #
#      ENTRYPOINT        #
# ====================== #

async def entrypoint(ctx: JobContext):
    """
    Función de entrada del worker de LiveKit.
    - Conecta al room.
    - Construye los agentes y el UserData.
    - Crea la sesión de agente de voz.
    - Arranca con el agente greeter.
    """
    await ctx.connect()

    # Menú de ejemplo que se pasa a algunos agentes
    menu = "Pizza: 10 euros, Ensalada: 5 euros, Helado: 3 euros, Café: 2 euros"

    # Estado del usuario compartido entre agentes
    userdata = UserData()
    userdata.agents.update(
        {
            "greeter": Greeter(menu),
            "reservation": Reservation(),
            "takeaway": Takeaway(menu),
            "checkout": Checkout(menu),
        }
    )

    # Crea una sesión de agente de voz con:
    #   - STT (Deepgram)
    #   - LLM (OpenAI)
    #   - TTS (ElevenLabs)
    #   - VAD (Silero)
    agent = AgentSession[UserData](
        userdata=userdata,
        stt=deepgram.STT(model="nova-3-general", language="es"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(
            voice_id="Ir1QNHvhaJXbAGhT50w3",
            model="eleven_turbo_v2_5",
        ),
        vad=silero.VAD.load(),
        max_tool_steps=5,
    )

    # Inicia la sesión con el agente "greeter"
    await agent.start(
        agent=userdata.agents["greeter"],
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )


# ====================== #
#       MAIN / CLI       #
# ====================== #

if __name__ == "__main__":
    # Lanza el worker de LiveKit con la función entrypoint
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
