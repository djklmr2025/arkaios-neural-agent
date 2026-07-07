# ARKAIOS + UI-TARS Integration Notes

## Objetivo

ARKAIOS no debe copiar UI-TARS completo. UI-TARS sirve como referencia madura para el contrato de acciones, operadores GUI y normalizacion de coordenadas. ARKAIOS mantiene su identidad:

- Puter comercial es la casa viva del agente: identidad, internet, workspace, archivos, apps y memoria operativa.
- NeuralAgent es el comunicador del PC anfitrion: recibe senales, valida acciones y toca Windows solo por bridge local.
- `arkaios-service-proxy` es la capa de gobierno remoto: valida intenciones y publica politicas.
- `builderOS_Lab` es el hub documental del ecosistema.

## Dos vertientes

### 1. ARKAIOS en Puter

ARKAIOS debe operar dentro del ecosistema Puter como usuario vivo:

- navegar, observar y actuar dentro de Puter;
- usar Puter AI, filesystem, apps, internet y APIs oficiales;
- producir entregables dentro de su propia casa, por ejemplo documentos, presentaciones, archivos editados o paquetes;
- descargar, copiar o transferir resultados al escritorio anfitrion solo cuando el usuario lo pida o el flujo lo requiera.

La version local `puter-internetOS` sirve como laboratorio. La meta operativa es conectar con Puter comercial y sus servidores, no depender de un fork local para produccion.

### 2. NeuralAgent como comunicador anfitrion

NeuralAgent no es la casa principal del agente. Es el canal fisico hacia el PC anfitrion:

- expone `Local Bridge` con token local;
- ejecuta acciones limitadas y auditables;
- recibe planes aprobados por el proxy;
- captura pantalla, UI visible y eventos cuando el agente necesita contexto del anfitrion;
- devuelve resultados a Puter/ARKAIOS por inbox/outbox.

## Que se toma de UI-TARS

Repos revisados:

- `C:\ARKAIOS\ui-tars-desktop`
- `C:\ARKAIOS\ui-tars`

Piezas utiles:

- contrato de acciones GUI: `click`, `left_double`, `right_single`, `type`, `hotkey`, `scroll`, `wait`, `finished`, `call_user`;
- conversion de cajas/puntos a coordenadas reales de pantalla;
- separacion entre modelo multimodal, parser de accion y operador fisico;
- operadores especializados para escritorio y navegador;
- MCP como sistema de herramientas externas;
- event stream para depurar flujo de decisiones.

Piezas que no se toman directamente ahora:

- monorepo Electron completo;
- ejecucion directa sin politica;
- dependencias `nut-js` dentro de NeuralAgent hasta que haya una migracion controlada;
- modelo UI-TARS como requisito obligatorio.

## Contrato local agregado

NeuralAgent expone:

```http
POST /local-bridge/actions/ui-tars
X-Bridge-Token: <token local>
Content-Type: application/json
```

Ejemplo:

```json
{
  "action_type": "click",
  "action_inputs": {
    "start_box": "[0.42, 0.51, 0.48, 0.57]"
  },
  "screen_width": 1920,
  "screen_height": 1080
}
```

El bridge convierte esa accion al contrato local existente:

- `click`, `left_click`, `left_single` -> `click` izquierdo.
- `left_double`, `double_click` -> `click` doble.
- `right_click`, `right_single` -> `click` derecho.
- `type` -> `type_text`.
- `hotkey` -> `hotkey`.
- `wait` -> espera local limitada a 30 segundos.
- `scroll` -> delega a Eyes/Hands si el endpoint `/scroll` esta disponible.
- `finished`, `call_user`, `user_stop` -> acciones terminales, no tocan el sistema.

## Politica

Las acciones UI-TARS son de bajo nivel y pueden modificar la pantalla del anfitrion. Por eso no se agregan automaticamente al planner remoto como acciones seguras generales. La ruta recomendada es:

1. ARKAIOS razona en Puter o con el modelo multimodal.
2. El proxy valida la intencion o el plan.
3. NeuralAgent ejecuta pasos UI-TARS solo dentro de una sesion autorizada.
4. El bridge registra resultado por outbox/eventos.

## Siguiente migracion tecnica

1. Agregar endpoint `/scroll` al servicio Eyes/Hands si aun no existe.
2. Unificar screenshots con metadata de escala, siguiendo la idea de `NutJSOperator.screenshot`.
3. Crear parser local opcional para respuestas UI-TARS crudas usando el patron de `ui_tars.action_parser`.
4. Publicar policy versionada que distinga:
   - acciones de intencion segura: abrir app, listar procesos;
   - acciones visuales con confirmacion: click, type, hotkey, scroll;
   - acciones prohibidas: shell arbitrario, credenciales, extraccion masiva.
