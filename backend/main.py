import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routers.apps.auth import router as userauth_router
from routers.aiagent.generic import router as aiagent_router
from routers.apps.threads import router as threads_router
from routers.aiagent.suggestor import router as suggestor_aiagent_router
from routers.aiagent.background import router as bg_mode_aiagent_router
from routers.apps.system import router as system_router
from routers.apps.runtime import router as runtime_router
from routers.apps.local_bridge import router as local_bridge_router
from utils.procedures import CustomError
from utils.identity_manager import boot_identity

from dotenv import load_dotenv
import os

# Load repo defaults first, then user runtime config from AppData.
# API_KEYS.env must win so installed/user-selected providers are not reset by backend/.env.
load_dotenv(override=True)
app_data = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
if app_data:
    api_keys_path = os.path.join(app_data, 'NeuralAgent', 'API_KEYS.env')
    if os.path.exists(api_keys_path):
        load_dotenv(dotenv_path=api_keys_path, override=True)
from sqlmodel import SQLModel
from db.database import engine
# Import all models so SQLModel knows about them before create_all
from db import models

app = FastAPI(
    title='NeuralAgent'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        '*',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(CustomError)
async def custom_http_exception_handler(request: Request, exc: CustomError):
    return JSONResponse(
        status_code=exc.status_code,
        content={'message': exc.message},
    )


app.include_router(userauth_router)
app.include_router(threads_router)
app.include_router(suggestor_aiagent_router)
app.include_router(bg_mode_aiagent_router)
app.include_router(aiagent_router)
app.include_router(system_router)
app.include_router(runtime_router)
app.include_router(local_bridge_router)

@app.on_event('startup')
async def startup():
    print('Starting up...')
    
    # 1. Boot Node Identity and Register with PRIMORDIAL-VAULT
    boot_identity()
    
    # 2. Re-create default tools (Disabled as db.tools_list does not exist)
    # import db.tools_list
    SQLModel.metadata.create_all(engine)

# @app.on_event('shutdown')
# async def shutdown():
#     await broadcast.disconnect()


@app.get('/')
async def index():
    return {'message': datetime.datetime.now()}
