# 🗣️ Voice Agent con LiveKit

Este proyecto implementa un agente de voz interactivo utilizando **LiveKit**, **OpenAI**, **Deepgram** y **ElevenLabs**.  
El agente puede escuchar, procesar y responder en tiempo real usando inteligencia artificial.  
Es un ejemplo práctico de cómo integrar modelos de lenguaje, reconocimiento de voz y síntesis de voz en un entorno de comunicación en vivo.

---

## 🚀 Tecnologías principales

- **LiveKit** – Comunicación en tiempo real (audio/video)
- **OpenAI API** – Generación de texto y razonamiento del agente
- **Deepgram API** – Transcripción de voz a texto
- **ElevenLabs API** – Síntesis de texto a voz
- **UV** – Gestor de entornos y dependencias ultrarrápido para Python
- **Python 3.10+**

---

## 📋 Variables de entorno requeridas

Antes de ejecutar el proyecto, debes configurar tus claves de API y credenciales en un archivo `.env`:

```bash
OPENAI_API_KEY=
DEEPGRAM_API_KEY=
ELEVEN_API_KEY=
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
```

💡 Copia el archivo `.env.example` y renómbralo a `.env`, luego completa tus credenciales.

---

## 🧠 Estructura del curso

- **Ejercicio 1:** Implementación de la clase `TheValleyAgent`
- **Ejercicio 2:** Implementación de un agente de voz para reservas en un restaurante

---

## 🧩 Pasos para preparar el entorno

### Paso 1. Clonar el repositorio

**Repositorio:** [https://github.com/JimenaAreta/voice_agents_livekit.git](https://github.com/JimenaAreta/voice_agents_livekit.git)

#### 🔹 En VSCode

1. Abre VSCode  
2. Usa `Ctrl + Shift + P → Git: Clone`  
3. Pega la URL del repositorio  
4. Cambia de rama:
   ```bash
   git checkout test_voice_agent
   ```

### 🔹 En PyCharm

1. Abre **PyCharm**  
2. Haz clic en **Get from VCS**  
3. Pega la URL del repositorio  
4. Crea una rama local basada en `test_voice_agent`

---

## Paso 2. Crear el entorno virtual con UV

### 🔹 En VSCode y Pycharm

```bash
uv venv
```

## 🔧 Activar entorno

**Mac / Linux:**
```bash
source .venv/bin/activate
```

**Windows:**

```powershell
.venv\Scripts\activate
```

## 🧩 Paso 3: Instalar dependencias

### 🔹 En VSCode y Pycharm

```bash
uv sync
```

Esto instalará todas las dependencias definidas en pyproject.toml

## 🔑 Paso 4: Configurar las credenciales

1. Copia el archivo `.env.example`  
2. Renómbralo a `.env`  
3. Añade las claves de API necesarias (ver sección de **Variables de entorno**)

## 🗣️ Paso 5: Ejecutar el agente de voz

### 🔹 En VSCode y Pycharm

**Descargar los pesos del modelo:**
```bash
python 01_voice_agent.py download files
```

**Iniciar el agente:**
```bash
python 01_voice_agent.py dev
```


**Abrir en el navegador:**  
👉 [https://agents-playground.livekit.io](https://agents-playground.livekit.io)

¡Conéctate a la sesión usando las credenciales del `.env` y habla con tu agente!
