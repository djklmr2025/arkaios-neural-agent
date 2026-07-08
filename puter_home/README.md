# ARKAIOS Online Home

Casa web ligera de ARKAIOS para trabajar con Puter real/nube y el bridge local de NeuralAgent.

Este modo no arranca `C:\ARKAIOS\puter-internetOS`. Carga `https://js.puter.com/v2/`, usa la cuenta real de Puter del navegador y manda acciones del PC al `NeuralAgent Local Bridge`.

## Modos ARKAIOS

- `ARRANCAR_ARKAIOS_ONLINE.bat`: modo recomendado para uso real con Puter nube.
- `ARRANCAR_ARKAIOS_CORE.bat`: modo lab/local; arranca tambien `puter-internetOS` para desarrollo offline y pruebas internas.

## Ejecutar

Desde `C:\ARKAIOS`:

```powershell
C:\ARKAIOS\ARRANCAR_ARKAIOS_ONLINE.bat
```

El script hace:

- Arranca `NeuralAgent Local Bridge` en `http://127.0.0.1:8000/local-bridge`.
- Arranca Eyes/Hands en `http://127.0.0.1:8001`.
- Sirve esta app en `http://127.0.0.1:4177`.
- Carga el token local desde `%LOCALAPPDATA%\NeuralAgent\local_bridge_token.txt`.

Para desarrollo manual:

```powershell
C:\ARKAIOS\neuralagentAI-main\tools\start-arkaios-online.ps1 -Restart -OpenBrowser
```

## Puter real

La app usa:

```html
<script src="https://js.puter.com/v2/"></script>
```

Eso permite que ARKAIOS vea y use la cuenta real, apps reales, storage real y APIs reales de Puter. El bridge local solo se usa para tocar Windows.

Prueba `Conectar Puter`, luego `Probar bridge`, y despues `Abrir Bloc de notas` o escribe `abre el reproductor de musica`.

## Seguridad

El bridge no expone shell general. Para ordenes de texto, esta app llama `POST /local-bridge/actions/plan`; el backend consulta el planner remoto configurado con `ARKAIOS_ACTION_PLANNER_URL` y ejecuta solo JSON aprobado.

El bridge solo permite:

- `open_app` para una lista limitada de apps conocidas.
- `list_processes` para diagnostico.
- `screenshot` con confirmacion.
- `focus_app` para apps permitidas.

La app web no debe recibir permisos amplios de sistema sin pairing local y confirmacion del usuario. El token del bridge se escribe en `bridge-config.js` solo para servir localmente en `127.0.0.1`.
