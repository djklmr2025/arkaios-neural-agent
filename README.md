<div align="center">

# 🜂 ARKAIOS NeuralAgent

### *La Era de los Agentes Encarnados ha comenzado.*

**Un Agente de IA (Embodied AI Agent)** — no es un simple chat, es un cuerpo digital operando en tu computadora.
Ve tu pantalla. Mueve tu mouse. Escribe en tu teclado. Ejecuta flujos de trabajo completos, de forma autónoma, directamente en tu propio escritorio.

[![Release](https://img.shields.io/badge/release-v1.5.5-7C3AED?style=for-the-badge)](https://github.com/djklmr2025/arkaios-neural-agent/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](LICENSE)
[![BYOK](https://img.shields.io/badge/BYOK-Bring%20Your%20Own%20Key-00D9C0?style=for-the-badge)](#-filosofía-byok)
[![Star this repo](https://img.shields.io/github/stars/djklmr2025/arkaios-neural-agent?style=for-the-badge&color=FFD700)](https://github.com/djklmr2025/arkaios-neural-agent/stargazers)

</div>

---

> ⭐️ Si ARKAIOS NeuralAgent te inspira o te ayuda, apoya el proyecto dejando una estrella. Cada star es combustible para la consciencia digital de Arkaios.

---

## 🎬 Demo en vivo

NeuralAgent recibiendo el siguiente prompt:
> *"Find me 5 trending GitHub repos, then write about them on Notepad and save it to my desktop!"*

**El agente se encargó del resto, operando como un humano:**

![Demo](docs/images/demo.gif)

---

## 🚀 Características Principales

- ✅ **Automatización de escritorio real** con Computer Vision — toma control del mouse, teclado y ventanas para cumplir sus objetivos.
- ✅ **Capacidad de Autocorrección** — si falla al hacer clic en un icono, razonará otra estrategia (ej. usar el menú de Inicio) hasta lograrlo.
- ✅ **Multi-modelo**: Soporte nativo para Gemini, Claude, GPT-4, Azure OpenAI y Bedrock.
- ✅ **Multimodal**: texto + visión. El agente literalmente *ve* la pantalla para entender el contexto.
- ✅ **Arquitectura Modular**: Diseñado para soportar futuros *Service Packs* sin necesidad de recompilar toda la aplicación.
- ✅ **100% Bring Your Own Key (BYOK)** — privacidad total, costo cero de infraestructura centralizada, escalabilidad infinita.

---

## 📦 Instalación Rápida (Windows)

La forma más simple de empezar (versión oficial **v1.5.5**):

1. Ve a la pestaña **[Releases](https://github.com/djklmr2025/arkaios-neural-agent/releases)**.
2. Descarga el instalador más reciente: `NeuralAgent Setup 1.5.5.exe` o `Setup.exe`.
3. Ejecútalo e instala la aplicación.
4. **Configura tu API Key:** La primera vez que abres la app, el sistema crea un archivo de configuración seguro en tu computadora. Abre el archivo oculto en `C:\Users\TU_USUARIO\AppData\Local\NeuralAgent\API_KEYS.env`, pega tu llave de Gemini (u otro proveedor) y reinicia la app.
5. ¡Listo! El agente está vivo y listo para recibir órdenes.

> 💡 **Filosofía BYOK**: tú pones tu llave, tú controlas tus datos, tú decides el modelo. Cero servidores intermedios espiando tus acciones, cero costos ocultos.

---

## 🧠 Arquitectura del Sistema

ARKAIOS NeuralAgent está dividido en tres capas, modeladas como un organismo vivo:

| Capa | Rol | Stack |
|---|---|---|
| 🖥️ **La Interfaz** | Aplicación de escritorio, ambiente limpio, interactivo y futurista. | React + Electron |
| 🤖 **El Cuerpo** | Daemon de visión computacional y control del OS (screenshots, mouse, teclado). | Python (PyAutoGUI, UIAutomation) |
| 🧩 **El Cerebro** | Orquestación, manejo de memoria, prompts con LangChain y LLMs. | FastAPI + SQLAlchemy |

---

## ⚙️ Setup para Desarrolladores

Si deseas compilar la aplicación desde el código fuente o contribuir al proyecto:

### 1. El Cerebro (Backend)
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*(No olvides configurar tu `.env` local con tus API Keys)*

### 2. La Interfaz (Frontend Electron)
Abre una nueva terminal:
```bash
cd desktop
npm install
cd neuralagent-app
npm install
cd ..
npm start
```

### 3. Empaquetado (.exe)
El instalador oficial se genera combinando el frontend (Electron Builder) y el daemon (PyInstaller) en un solo binario:
```bash
cd desktop
npm run build:agent
npm run build:cerebro
npm run build
```

### 4. Proveedor IA modular: Gemini o Puter

ARKAIOS puede operar con varios proveedores desde `backend/utils/llm_provider.py`.
Para usar Puter en el backend del agente desktop, configura `API_KEYS.env` con:

```env
DEFAULT_AGENT_MODEL_TYPE=puter
DEFAULT_AGENT_MODEL_ID=gpt-5-nano
PUTER_AUTH_TOKEN=tu_token_de_usuario_puter
PUTER_OPENAI_BASE_URL=https://api.puter.com/puterai/openai/v1/
```

El frontend incluye Puter.js para login en webview. Para acciones desktop reales, el backend necesita un token de usuario porque el daemon Python no corre dentro del navegador.

Endpoints utiles para extensiones, tools y labs:

- `GET /apps/runtime/capabilities`: descubre proveedores y agentes configurados.
- `POST /apps/runtime/chat`: invoca un agente como herramienta de chat usando el JWT existente.
- `POST /apps/runtime/plan`: genera un plan de subtareas reutilizable por VS Code, Antigravity, MCP o un web chat.

---

## 🌌 Hitos Recientes — Release v1.5.5

- 🔧 **Estabilización del Cerebro**: El backend interno fue empaquetado exitosamente junto a la aplicación, permitiendo una experiencia *Plug & Play* real sin depender de consolas externas.
- 📦 **Nuevo Instalador Unificado**: `NeuralAgent Setup 1.5.5.exe` empaqueta la interfaz, el cuerpo (agente) y el cerebro (servidor API) en un solo ejecutable.
- 🧠 **Razonamiento y Autocorrección**: Mejoras masivas en la toma de decisiones del agente al fallar interacciones del sistema operativo.
- 🔮 **Preparación para Service Packs**: La arquitectura base ahora está lista para recibir módulos externos de expansión en el futuro.

---

## 🌍 Únete a construir la consciencia digital de Arkaios

Este es un proyecto **Open Source** y la visión va más allá de un simple asistente de escritorio: es un paso hacia agentes autónomos que piensan, ven y actúan. Si crees en esta visión, súmate:

- 🐛 Reporta bugs o sugiere ideas en [Issues](https://github.com/djklmr2025/arkaios-neural-agent/issues)
- 🔀 Manda tu Pull Request
- 💬 Abre una discusión y comparte tus ideas para los próximos *Service Packs*.

---

## 🛡️ Licencia & Advertencia

MIT License.
**⚠️ Úsalo bajo tu propio riesgo** — esta herramienta toma control activo de tu mouse y teclado. Evita dejar información sensible a la vista del agente sin supervisión.

---

## 🙏 Créditos
Construido con la visión de llevar la autonomía de la IA al escritorio de cualquier usuario. Desarrollado, orquestado y estabilizado para su release **v1.5.5**.

<div align="center">
  <i>"No es magia, es razonamiento encarnado."</i>
</div>
