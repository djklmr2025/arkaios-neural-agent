# Puter Home + NeuralAgent Local Bridge

Este modo evita recompilar Electron en cada prueba.

## Flujo de desarrollo recomendado

1. Arrancar el nucleo ARKAIOS:

```powershell
C:\ARKAIOS\neuralagentAI-main\tools\start-arkaios-core.ps1 -Restart -OpenPuter
```

O desde Windows:

```text
C:\ARKAIOS\neuralagentAI-main\ARRANCAR_ARKAIOS_NUCLEO.bat
```

Ese arranque levanta:

- Backend + Local Bridge en `http://127.0.0.1:8000/local-bridge`.
- Eyes/Hands server en `http://127.0.0.1:8001`.
- Puter OS local en `http://puter.localhost:4100`.
- ARKAIOS invisible worker para el canal `neuro-login`.
- ARKAIOS Puter background worker para el canal `puter-native` cuando el GUI de Puter carga.
- Opcionalmente abre la app visual ARKAIOS en Puter.

Por defecto no abre la ventana vieja de NeuralAgent Desktop. Si se necesita ver esa UI, usar:

```powershell
C:\ARKAIOS\neuralagentAI-main\tools\start-arkaios-core.ps1 -Restart -OpenPuter -OpenNeuralAgentDesktop
```

2. Usar el ejecutable ya instalado como runtime Electron si hace falta depurar NeuralAgent Desktop:

```powershell
C:\ARKAIOS\neuralagentAI-main\tools\start-installed-dev.ps1 -RestartApp
```

Ese script:

- Detiene solo el backend de desarrollo anterior.
- Arranca `backend\run_server.py` desde el codigo fuente.
- Abre `C:\Users\djklm\AppData\Local\Programs\neuralagent-desktop\neuralagent-desktop.exe`.
- Mantiene logs en `tmp_backend_stdout.log` y `tmp_backend_stderr.log`.

3. Servir Puter Home legacy:

```powershell
C:\ARKAIOS\neuralagentAI-main\tools\serve-puter-home.ps1
```

Abrir:

```text
http://127.0.0.1:4177
```

4. Validar bridge:

- Click en `Probar bridge`.
- Copiar el token desde:

```text
%LOCALAPPDATA%\NeuralAgent\local_bridge_token.txt
```

- Pegar en la app.
- Probar `Abrir Bloc de notas`.

## Por que no empaquetar Electron en cada prueba

Para cambios de backend y bridge local, no hace falta tocar Electron: el ejecutable instalado puede hablar con el backend fuente en `127.0.0.1:8000`.

Para cambios de UI/Electron, la ruta rapida es reconstruir React y reemplazar solo:

```text
C:\Users\djklm\AppData\Local\Programs\neuralagent-desktop\resources\app.asar
```

El instalador completo se deja para versiones estables.

## Distribucion estable

Cuando el flujo este probado:

1. Generar build final normal una sola vez.
2. Copiar carpeta instalada limpia.
3. Crear paquete portable o autoextraible.

Si hay `7z` o WinRAR instalado, se puede crear SFX. Si no, se puede entregar ZIP + launcher PowerShell.

## Canal de invocacion

El bridge local expone un canal durable para que Puter, neuro-login, VS Code o un chat externo invoquen a ARKAIOS.

Arquitectura prevista:

- `neuro-login` o cualquier chat en Windows funciona como puerta de entrada.
- ARKAIOS vive como app/mente dentro de Puter.
- El Local Bridge es el bus seguro entre Windows, Puter y herramientas.
- El worker invisible consume `neuro-login` cuando la app visual de Puter no esta abierta.
- El worker nativo invisible dentro de Puter consume `puter-native` cuando el escritorio Puter esta cargado.
- Eyes/Hands permite ver pantalla, mover mouse, teclear y ejecutar acciones autorizadas.
- Herramientas como Media Cutter u Open Generative AI entran despues como `tasks/events`.

Todos los endpoints protegidos requieren el header:

```text
X-Bridge-Token: <contenido de %LOCALAPPDATA%\NeuralAgent\local_bridge_token.txt>
```

Flujo minimo:

1. Cliente externo envia una orden:

```http
POST /local-bridge/messages/inbox
```

```json
{
  "channel_id": "neuro-login",
  "conversation_id": "demo-1",
  "payload": {
    "source": "neuro-login",
    "mode": "computer",
    "text": "abre el bloc de notas",
    "auto_execute": true
  }
}
```

2. ARKAIOS en Puter lee:

```http
GET /local-bridge/messages/inbox
```

El bridge entrega mensajes con lease temporal. Si la app falla antes de confirmar, el mensaje puede reintentarse despues del lease.

3. ARKAIOS responde:

```http
POST /local-bridge/messages/outbox
```

4. ARKAIOS confirma el mensaje original:

```http
POST /local-bridge/messages/inbox/{message_id}/ack
```

5. El cliente externo lee respuestas:

```http
GET /local-bridge/messages/outbox?channel_id=neuro-login
```

Tambien existen endpoints basicos para `tasks` y `events`, pensados para mostrar bitacora viva, permisos y progreso de herramientas.

## Cliente externo de prueba

Para simular neuro-login desde PowerShell:

```powershell
C:\ARKAIOS\neuralagentAI-main\tools\invoke-arkaios.ps1 `
  -ChannelId neuro-login `
  -Mode computer `
  -Text "abre el bloc de notas por favor" `
  -AutoExecute `
  -WaitSeconds 30
```

Para solo dejar una orden en cola sin esperar respuesta:

```powershell
C:\ARKAIOS\neuralagentAI-main\tools\invoke-arkaios.ps1 `
  -Text "hola arkaios" `
  -Mode ask `
  -WaitSeconds 0
```

Para pedir una accion interna de Puter:

```powershell
C:\ARKAIOS\neuralagentAI-main\tools\invoke-arkaios.ps1 `
  -ChannelId puter-native `
  -Mode puter `
  -Text "estado del worker de puter" `
  -AutoExecute `
  -WaitSeconds 30
```

## Modo segundo plano

Hay dos niveles:

- Servicios invisibles: backend, bridge, Puter server, eyes/hands y ARKAIOS worker pueden correr en segundo plano.
- Casa visual Puter: la app ARKAIOS dentro de Puter muestra estado, visor, consola y acciones cuando se abre.
- Worker nativo Puter: `arkaios-worker` se registra como app `background=1` y se lanza al cargar el escritorio Puter.

El worker persistente consume el canal `neuro-login` sin depender de una pestaña abierta. Comparte el mismo contrato `/messages`, `/tasks` y `/events`, por eso neuro-login no tiene que cambiar si despues la mente visual de Puter toma el control.

IA en segundo plano:

- El worker de Windows usa el proveedor del backend (`ARKAIOS_WORKER_AGENT`, por defecto `planner`).
- Si el proveedor es Puter server-side y devuelve `This endpoint is only available to user sessions`, el worker lo reporta como bloqueo de sesion.
- Para IA invisible real desde Windows, configura una llave server-side como `GEMINI_API_KEY`, `OPENAI_API_KEY`, Azure, Anthropic o Bedrock.
- Para Puter AI con sesion de usuario, usa el canal `puter-native`, porque ese worker corre dentro del navegador autenticado de Puter.

Limitacion actual:

- Ejecuta acciones locales seguras ya mapeadas: abrir Notepad, listar procesos y capturar pantalla.
- El worker nativo de Puter puede usar APIs de Puter y Puter AI, pero las acciones visuales avanzadas del OS todavia necesitan mapeo especifico.
