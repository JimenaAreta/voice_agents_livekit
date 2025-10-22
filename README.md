🗣️ Voice Agent con LiveKit
Este proyecto implementa un agente de voz interactivo utilizando LiveKit, OpenAI, Deepgram y ElevenLabs.
El agente puede escuchar, procesar y responder en tiempo real usando inteligencia artificial.
Es un ejemplo práctico de cómo integrar modelos de lenguaje, reconocimiento de voz y síntesis de voz en un entorno de comunicación en vivo.
🚀 Tecnologías principales
LiveKit – Comunicación en tiempo real (audio/video)
OpenAI API – Generación de texto y razonamiento del agente
Deepgram API – Transcripción de voz a texto
ElevenLabs API – Síntesis de texto a voz
UV – Gestor de entornos y dependencias ultrarrápido para Python
Python 3.10+
📋 Variables de entorno requeridas
Antes de ejecutar el proyecto, debes configurar tus claves de API y credenciales en un archivo .env:
OPENAI_API_KEY=
DEEPGRAM_API_KEY=
ELEVEN_API_KEY=
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
💡 Copia el archivo .env.example y renómbralo a .env, luego completa tus credenciales.
🧠 Estructura del curso
Ejercicio 1: Implementación de la clase TheValleyAgent
Ejercicio 2: (por definir en clase)
🧩 Pasos para preparar el entorno
1. Clonar el repositorio
Repositorio: https://github.com/JimenaAreta/voice_agents_livekit.git
🔹 En VSCode
Abre VSCode
Usa Ctrl + Shift + P → Git: Clone
Pega la URL del repositorio
Cambia de rama:
git checkout test_voice_agent
🔹 En PyCharm
Abre PyCharm
Haz clic en Get from VCS
Pega la URL del repositorio
Crea una rama local basada en test_voice_agent
2. Crear el entorno virtual con uv
🔹 En VSCode
uv venv
Activar entorno:
Mac / Linux:
source .venv/bin/activate
Windows (PowerShell):
.venv\Scripts\activate
🔹 En PyCharm
Abre la terminal integrada
Ejecuta:
uv venv
Activa el entorno según tu sistema operativo (mismos comandos que arriba)
3. Instalar dependencias
🔹 En VSCode
uv sync
🔹 En PyCharm
Ejecuta el mismo comando en la terminal del proyecto:
uv sync
Esto instalará todas las dependencias definidas en pyproject.toml.
4. Configurar las credenciales
Copia el archivo .env.example y renómbralo a .env
Añade las claves de API necesarias (ver sección de Variables de entorno)
5. Ejecutar el agente de voz
🔹 En VSCode
Descargar los pesos del modelo:
python 01_voice_agent.py download files
Iniciar el agente:
python 01_voice_agent.py dev
Abre en el navegador:
👉 https://agents-playground.livekit.io
Conéctate a la sesión usando las credenciales del .env.
🔹 En PyCharm
Los mismos pasos aplican desde la terminal de PyCharm:
python 01_voice_agent.py download files
python 01_voice_agent.py dev
🧰 Comandos útiles
Comando	Descripción
uv add paquete	Instala un nuevo paquete y lo añade al proyecto
uv sync	Sincroniza dependencias con pyproject.toml
uv lock	Genera el archivo uv.lock
source .venv/bin/activate	Activa el entorno virtual (Mac/Linux)
.venv\Scripts\activate	Activa el entorno virtual (Windows)
👩‍🏫 Notas adicionales
No es necesario ejecutar uv init, ya que el archivo pyproject.toml ya está creado.
Asegúrate de tener Python 3.10 o superior instalado.
Si experimentas errores con dependencias, elimina la carpeta .venv y vuelve a crearla.
✨ Créditos
Proyecto educativo creado para The Valley, demostrando el uso de LiveKit y modelos de voz AI con Python.
Autora: Jimena Areta