# NeuralAgent Puter Home

MVP de la casa Puter para NeuralAgent.

Puter queda como entorno de identidad, AI y workspace del agente. El control real de Windows se hace por `NeuralAgent Local Bridge`, un endpoint local del backend que solo acepta acciones limitadas con token.

## Ejecutar

1. Arranca el backend local:

```powershell
cd C:\ARKAIOS\neuralagentAI-main\backend
.\venv\Scripts\python.exe .\run_server.py
```

2. Sirve esta carpeta por HTTP:

```powershell
cd C:\ARKAIOS\neuralagentAI-main\puter_home
py -3 -m http.server 4177
```

3. Abre:

```text
http://127.0.0.1:4177
```

4. Valida el bridge. Si usas `tools\serve-puter-home.ps1`, el token se carga automaticamente desde:

```text
%LOCALAPPDATA%\NeuralAgent\local_bridge_token.txt
```

5. Prueba `Abrir Bloc de notas`.

## Seguridad

El bridge no expone shell general. En este MVP solo permite:

- `open_app` para una lista limitada de apps conocidas.
- `list_processes` para diagnostico.

La app Puter no debe recibir permisos amplios de sistema sin pairing local y confirmacion del usuario.
