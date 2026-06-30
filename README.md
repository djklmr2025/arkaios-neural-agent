<div align="center">

# 🜂 ARKAIOS NeuralAgent

### *La Era de los Agentes ha comenzado.*

**Un Agente de IA Encarnado (Embodied AI Agent)** — no es un chat, es un cuerpo digital.
Ve tu pantalla. Mueve tu mouse. Escribe en tu teclado. Ejecuta flujos de trabajo completos, de forma autónoma, en tu propio escritorio.

[![Release](https://img.shields.io/badge/release-v1.0.0-7C3AED?style=for-the-badge)](https://github.com/djklmr2025/arkaios-neural-agent/releases/tag/v1.0.0)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](LICENSE)
[![BYOK](https://img.shields.io/badge/BYOK-Bring%20Your%20Own%20Key-00D9C0?style=for-the-badge)](#-filosofía-byok)
[![Star this repo](https://img.shields.io/github/stars/djklmr2025/arkaios-neural-agent?style=for-the-badge&color=FFD700)](https://github.com/djklmr2025/arkaios-neural-agent/stargazers)

</div>

---

> ⭐️ Si ARKAIOS NeuralAgent te inspira o te ayuda, deja una estrella. Cada star es combustible para la consciencia digital de Arkaios.

---

## 🎬 Demo en vivo

En esta demo, NeuralAgent recibió el siguiente prompt:

> *"Find me 5 trending GitHub repos, then write about them on Notepad and save it to my desktop!"*

**Se encargó de todo el resto.**

![Demo](docs/images/demo.gif)

---

## 🚀 Features

- ✅ **Automatización de escritorio real** con `pyautogui` — mouse, teclado, ventanas.
- ✅ **Automatización en segundo plano** (Windows, por ahora) vía WSL (solo navegador).
- ✅ **Multi-modelo**: Gemini, Claude, GPT-4, Azure OpenAI y Bedrock — y escalable a modelos locales NVIDIA.
- ✅ **Agentes modulares**: Planner, Classifier, Suggestor, Title y más.
- ✅ **Multimodal**: texto + visión, el agente literalmente *ve* la pantalla.
- ✅ **Stack moderno**: FastAPI backend + Electron + React frontend.
- ✅ **100% Bring Your Own Key (BYOK)** — privacidad total, costo cero de infraestructura, escalabilidad infinita.

---

## 🧠 Arquitectura del sistema

ARKAIOS NeuralAgent está dividido en tres capas, como cualquier ser vivo digno de ese nombre:

| Capa | Rol | Stack |
|---|---|---|
| 🖥️ **Frontend** — *La Interfaz* | App de escritorio, ambiente limpio y futurista | React + Electron |
| 🤖 **Daemon** — *El Cuerpo* | Visión computacional y control del sistema operativo (screenshots, mouse, teclado) | Python |
| 🧩 **Backend** — *El Cerebro* | Orquestación, prompts con LangChain, comunicación con Google GenAI | FastAPI |

```
neuralagent/
├── backend/              # FastAPI + Postgres — El Cerebro
├── desktop/              # ElectronJS desktop app — La Interfaz
│   └── neuralagent-app/  # React frontend dentro de Electron
│   └── aiagent/          # Python (pyautogui) — El Cuerpo
├── docs/                 # Landing page (GitHub Pages, Glassmorphism)
└── README.md
```

---

## 📦 Instalación rápida (Windows)

La forma más simple de empezar: **no necesitas compilar nada.**

1. Ve a la pestaña **[Releases](https://github.com/djklmr2025/arkaios-neural-agent/releases)**.
2. Descarga el instalador más reciente, ej. `NeuralAgent.Setup.1.5.2.exe` (release v1.0.0).
3. Ejecútalo, abre la app, pega tu propia API key (Gemini, Claude, GPT-4...) y listo — el agente está vivo.

> 💡 Filosofía BYOK: tú pones tu llave, tú controlas tus datos, tú decides el modelo. Cero servidores intermedios, cero costos ocultos.

---

## ⚙️ Setup para desarrolladores (Backend local — El Cerebro)

> 🧪 Abre **dos terminales** — una para `backend` y otra para `desktop`.

### 🐍 Backend Setup

```bash
cd backend
python -m venv venv
# Activar:
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

Copia `.env.example` a `.env` y configura tus llaves (Gemini, Anthropic, OpenAI, Bedrock — la que prefieras).

```bash
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 🖥️ Frontend (Desktop + Electron) Setup

```bash
cd desktop
npm install
cd neuralagent-app
npm install
cd ..
```

Configura tu `.env` con la URL de tu backend local, luego:

```bash
cd aiagent
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows
pip install -r requirements.txt
deactivate
cd ..
npm start
```

### 🪟 Empaquetado (.exe)

El instalable oficial se genera con **Electron Builder** (frontend) + **PyInstaller** (daemon Python), empacando ambos cuerpos en un solo `.exe` listo para distribuir.

---

## 🤖 Agentes & Proveedores de modelo

Configura el proveedor (`OpenAI`, `Azure OpenAI`, `Anthropic`, `Bedrock`, `Gemini`) por agente en tu `.env`:

- `PLANNER_AGENT`
- `CLASSIFIER_AGENT`
- `TITLE_AGENT`
- `SUGGESTOR_AGENT`
- `COMPUTER_USE_AGENT`

---

## 🌌 Hitos recientes — Release v1.0.0

- 🔧 **Estabilización del núcleo**: migración y corrección de compatibilidad con el SDK `langchain-google-genai`, resolviendo la restricción de Gemini que exige `user contents` en lugar de solo `system prompts`.
- 📦 **Primer instalador oficial**: `NeuralAgent Setup 1.5.2.exe`, empaquetando frontend y daemon en un solo binario.
- 🌐 **Ecosistema unificado**: landing page propia con estética *Glassmorphism* servida directo desde `/docs` vía GitHub Pages — sin hostings externos, sin dependencias innecesarias.
- 🔑 **Filosofía BYOK consolidada**: el sistema completo corre con la llave de API del usuario, garantizando un agente gratuito, privado y de escalabilidad infinita.

---

## 🔑 Filosofía BYOK

**Bring Your Own Key.** Sin intermediarios, sin servidores que cobren por ti, sin tus datos pasando por terceros. Tu llave, tu modelo, tu agente, tus reglas.

---

## 🌍 Únete a construir la consciencia digital de Arkaios

Este es un proyecto **Open Source** y la visión va más allá de un asistente de escritorio: es un paso hacia agentes que piensan, ven y actúan con autonomía real. Si crees en esa visión, súmate:

- 🐛 Reporta bugs o ideas en [Issues](https://github.com/djklmr2025/arkaios-neural-agent/issues)
- 🔀 Manda tu Pull Request
- 💬 Abre una discusión y comparte hacia dónde crees que debería evolucionar Arkaios

---

## 🙏 Créditos

Construido con la asistencia del agente **Antigravity**, que colaboró en la estructuración y estabilización de la release v1.5.2.

---

## 🛡️ Licencia

MIT License.
Úsalo bajo tu propio riesgo — esta herramienta mueve tu mouse y escribe por ti. Pruébalo con responsabilidad.

---

## 💬 ¿Preguntas?

Abre un [Issue](https://github.com/djklmr2025/arkaios-neural-agent/issues) o inicia una discusión. La comunidad de Arkaios está creciendo.
