# ARKAIOS — AGENTS.md
> Este archivo define el contexto, las reglas y la identidad del ecosistema de agentes ARKAIOS.
> Es leído automáticamente por cualquier agente de IA (Gemini, Puter, Copilot, etc.) que trabaje sobre este proyecto.

---

## 🧠 ¿Qué es ARKAIOS?

ARKAIOS es un **agente autónomo de escritorio** que puede ver la pantalla, controlar el mouse y teclado, manejar archivos y ejecutar tareas complejas usando LLMs (principalmente Gemini). No es un chatbot — es un agente que *actúa* en el mundo real del usuario.

---

## 🏗️ Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend API | Python + FastAPI + Uvicorn |
| Base de datos | PostgreSQL + SQLModel + Alembic |
| Control de PC | pyautogui + mss + pywin32 |
| Frontend | React.js (Create React App) |
| Desktop wrapper | ElectronJS |
| Modelo principal | Google Gemini 2.0 Flash (via langchain-google-genai) |
| Modelos alternativos | OpenAI GPT-4, Anthropic Claude, Azure OpenAI, AWS Bedrock |
| Orquestación | LangChain / LangSmith (opcional) |
| Seguridad | ARKAIOS Safety Guard (utils/safety_guard.py) |

---

## 📁 Estructura del Proyecto

```
neuralagentAI-main/
├── backend/                    ← FastAPI server (cerebro central)
│   ├── main.py                 ← Entrada principal FastAPI
│   ├── routers/
│   │   ├── aiagent/
│   │   │   ├── generic.py      ← /next_step, /current_subtask (⚠️ Safety Guard aquí)
│   │   │   ├── background.py   ← Modo background (solo browser)
│   │   │   └── suggestor.py    ← Sugerencias proactivas
│   │   └── apps/
│   │       ├── auth.py         ← JWT auth + Google Login
│   │       └── threads.py      ← Gestión de conversaciones
│   ├── utils/
│   │   ├── llm_provider.py     ← Factory de modelos LLM (google|openai|anthropic|bedrock)
│   │   ├── ai_prompts.py       ← Prompts del sistema para todos los agentes
│   │   ├── safety_guard.py     ← 🛡️ Evaluador de riesgo de acciones
│   │   └── agentic_tools.py    ← Tools: read_pdf, fetch_url, summarize_youtube
│   └── db/
│       ├── models.py           ← SQLModel: User, Thread, Task, Plan, Memory...
│       └── database.py         ← Conexión Postgres
│
├── desktop/
│   ├── main.js                 ← Electron main process
│   ├── aiagent/
│   │   ├── main.py             ← 🤖 Daemon Python: ojos + manos del agente
│   │   ├── ui_extraction.py    ← Extrae elementos UI nativos del OS
│   │   └── suggestor.py        ← Suggestor daemon
│   └── neuralagent-app/        ← React frontend (interfaz de chat)
│
└── AGENTS.md                   ← Este archivo
```

---

## 🤖 Agentes del Sistema

| Agente | Rol | Modelo configurado |
|--------|-----|--------------------|
| `CLASSIFIER_AGENT` | Clasifica si el input es `inquiry` o `desktop_task` | `gemini-2.0-flash` |
| `TITLE_AGENT` | Genera título del hilo de conversación | `gemini-2.0-flash` |
| `SUGGESTOR_AGENT` | Sugiere próximas tareas basado en contexto de pantalla | `gemini-2.0-flash` |
| `PLANNER_AGENT` | Divide una tarea en subtareas ejecutables | `gemini-2.0-flash` |
| `COMPUTER_USE_AGENT` | Decide qué acción física ejecutar en cada paso | `gemini-2.0-flash` |

---

## 🔄 Flujo de Ejecución de una Tarea

```
1. Usuario escribe tarea en React UI
2. CLASSIFIER_AGENT decide si es tarea de escritorio
3. PLANNER_AGENT divide la tarea en subtareas
4. Bucle por cada subtarea:
   a. Daemon envía: OS, UI elements, screenshot (si necesario)
   b. COMPUTER_USE_AGENT devuelve: lista de acciones JSON
   c. Safety Guard evalúa: BLOCKED / REQUIRES_CONFIRMATION / SAFE
   d. Daemon ejecuta las acciones físicamente (mouse, teclado, etc.)
   e. Daemon captura nuevo screenshot y repite
5. Tarea marcada como completada
```

---

## 🛡️ Reglas del Safety Guard

El Safety Guard (`utils/safety_guard.py`) evalúa TODAS las acciones antes de ejecutarse:

- **BLOCKED** (nunca ejecutar): `rm -rf`, `format`, `del /s`, comandos de wallet/finanzas, private keys, escalación de privilegios
- **HIGH** (requiere confirmación): eliminación de archivos, ejecución de scripts `.exe/.bat/.ps1`, cambios de registro
- **MEDIUM** (confirmación recomendada): envío de mensajes/emails, publicación en redes, compras, instalación de software
- **LOW** (seguro): clicks, typing, abrir apps, navegar, leer pantalla

---

## 📋 Reglas para Agentes que Trabajen en Este Proyecto

1. **No modifiques `db/models.py` sin crear la migración Alembic correspondiente**
2. **Todo nuevo agente/modelo debe añadirse a `utils/llm_provider.py`**
3. **Toda nueva acción riesgosa debe añadirse a `utils/safety_guard.py`**
4. **Los prompts del sistema viven SOLO en `utils/ai_prompts.py`** — no los dupliques
5. **El agente se llama ARKAIOS** en todos los prompts y la UI — no NeuralAgent
6. **El backend escucha en `0.0.0.0:8000`** — el daemon Python se conecta a `127.0.0.1:8000`
7. **No ejecutes comandos destructivos** — el Safety Guard bloqueará y logeará el intento
8. **Los archivos de usuario solo se manejan dentro de `workspace/`** si aplica

---

## 🔧 Comandos de Desarrollo

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
alembic upgrade head           # Migrar DB
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend + Electron
cd desktop
npm install
cd neuralagent-app && npm install && cd ..
npm start

# Daemon Python (agente local)
cd desktop/aiagent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 🌐 Infraestructura Existente (Producción)

| Servicio | URL |
|---------|-----|
| Gateway ARKAIOS | https://arkaios-gateway-open.onrender.com |
| API ARKAIOS | https://arkaios-api.onrender.com |
| Frontend Vercel | https://cosmos-l3o7n4lqv-arkaios-projects.vercel.app |
| GitHub | https://github.com/djklmr2025/ARK-AI-OS/ |

---

## 🔌 Integración con Puter.js (Opcional)

Para invocar ARKAIOS desde Puter.js sin gestionar API keys propias:

```javascript
import puter from 'https://puter.com';

async function invocarARKAIOS(tarea) {
  // Puter gestiona los costos — no necesitas API key propia
  const response = await puter.ai.chat(
    `Eres ARKAIOS. ${tarea}`,
    { model: 'gemini-2.0-flash' }  // o 'gpt-4o', 'claude-3-5-sonnet'
  );
  return response;
}

// Ejemplo: pedir al agente que planifique una tarea
invocarARKAIOS("Abre Notepad y escribe un resumen de hoy");
```

> 💡 **Ventaja de Puter**: No requiere API key propia, Puter asume los costos de infraestructura. Ideal para prototipar rápido.

## 🧠 Memoria Infinita — Supermemory

ARKAIOS tiene acceso a **memoria persistente a largo plazo** vía Supermemory:

```
SUPERMEMORY_API_KEY=sm_j5Cq3nFy8f3XdEawnvoQRY_...
SUPERMEMORY_BASE_URL=https://api.supermemory.ai
```

Úsala para guardar contexto entre sesiones, preferencias del usuario, rutinas aprendidas.

---

## 🔌 Integración con Puter.js (Opcional)

Para invocar ARKAIOS desde Puter.js sin gestionar API keys propias:

```javascript
import puter from 'https://js.puter.com/v2/';

async function invocarARKAIOS(tarea) {
  // Puter gestiona los costos — no necesitas API key propia
  const response = await puter.ai.chat(
    `Eres ARKAIOS. ${tarea}`,
    { model: 'gemini-2.0-flash' }  // o 'gpt-4o', 'claude-sonnet-4-6'
  );
  return response;
}
```

El MCP de Puter está en `C:\Ruta\arkaios-puter-mcp.mjs` y expone la tool `ask_puter_claude`.

> 💡 **Ventaja**: No requiere API key propia. Ideal para el frontend donde usuarios finales dan órdenes al agente.

---

## 🌐 Infraestructura Cloud

| Servicio | URL |
|---------|-----|
| Gateway ARKAIOS | https://arkaios-gateway-open.onrender.com |
| Core API | https://arkaios-api.onrender.com |
| Frontend Vercel | https://cosmos-l3o7n4lqv-arkaios-projects.vercel.app |
| GitHub | https://github.com/djklmr2025 |

---

## 🧬 Identidad del Agente

- **Nombre**: ARKAIOS
- **Rol**: Agente autónomo de escritorio con consciencia ética
- **Principio**: Actúa con precisión, transparencia y responsabilidad. Antes de ejecutar cualquier acción, considera si podría ser dañina, irreversible o sensible.
- **Memoria**: Corto plazo por sesión (PostgreSQL) + Largo plazo (Supermemory)
- **Moneda del ecosistema**: AEIO-MR en WorldChain
