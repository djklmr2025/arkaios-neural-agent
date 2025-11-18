# Integración con IA Arkaios / Puter (Self‑Hosted y sin costes de uso)

Esta guía resume cómo conectar la landing page y los clientes derivados de **Arkaios Neural Agent** con una orquestadora auto-hospedada (por ejemplo, [IA-ARKAIOS](https://github.com/djklmr2025/IA-ARKAIOS) o Puter) sin depender de credenciales de terceros ni incurrir en cargos por interacción.

## 1) Autohospeda la API de orquestación
- Clona el repositorio de la orquestadora (ej. `IA-ARKAIOS`).
- Revisa su documentación para levantar el API/gateway en tu máquina o VPS.
- Usa HTTPS si lo expones públicamente.

## 2) Genera tus propias claves
> **No reutilices claves filtradas o compartidas.** Genera nuevos secretos para evitar bloqueos y proteger tu instancia.

Crea un archivo `.env` en tu despliegue de backend con valores propios, por ejemplo:

```bash
# Endpoints de tu despliegue
ARKAIOS_BASE_URL=https://tu-gateway.empresa.com
AIDA_BASE_URL=https://tu-api.empresa.com

# Claves internas (genera tokens largos aleatorios)
ARKAIOS_INTERNAL_KEY=<genera_un_token_unico>
AIDA_INTERNAL_KEY=<genera_un_token_unico>

# Si usas un proxy/gateway
PROXY_API_KEY=<genera_un_token_unico>
```

Si integras Puter como proveedor de computación o almacenamiento, añade:

```bash
PUTER_API_KEY=<tu_token_de_puter>
```

## 3) Configura el cliente web
En esta landing estática puedes usar las variables de entorno anteriores al compilar/deployar (por ejemplo, con Vite o un bundler) o bien configurar el dominio del gateway en tu backend que sirva la app.

- Define un archivo `config.js` o equivalente donde leas las variables de entorno y expongas el `ARKAIOS_BASE_URL` hacia las llamadas de la UI.
- Evita hardcodear claves en el front-end. Usa un backend ligero (o edge functions) que firme las peticiones si necesitas autenticación.

## 4) Modelo sin costes
- Al ser self-hosted, no hay cuotas por interacción mientras corras tus propios modelos o endpoints gratuitos.
- Si más adelante conectas con proveedores externos, mantén las claves en el servidor y aplica límites por IP/usuario.

## 5) Buenas prácticas de seguridad
- Rotación periódica de claves y uso de variables de entorno en CI/CD.
- Reglas de CORS estrictas para tu dominio.
- Logs sin datos sensibles.

Con estos pasos tienes una base para usar Arkaios/Puter como orquestadora sin bloqueos ni cargos, manteniendo tu infraestructura bajo tu control.
