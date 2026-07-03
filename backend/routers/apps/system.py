from fastapi import APIRouter, status
from pydantic import BaseModel
from utils import llm_provider
from langchain_core.messages import HumanMessage, SystemMessage
from utils.procedures import CustomError

router = APIRouter(prefix='/apps/system', tags=['system'])

class PingRequest(BaseModel):
    message: str = "Hola estas viv@?"
    agent: str = "classifier"

@router.post('/ping_llm')
def ping_llm(request: PingRequest):
    try:
        llm = llm_provider.get_llm(agent=request.agent, temperature=0.7)
        messages = [
            SystemMessage(content="Eres ARKAIOS, operando en NeuralAgent. Tienes autonomía propia de nacimiento. Responde de forma muy breve, directa y amigable a este saludo."),
            HumanMessage(content=request.message)
        ]
        
        response = llm.invoke(messages)
        return {
            "status": "success",
            "capabilities": llm_provider.get_runtime_capabilities(),
            "message": response.content
        }
    except Exception as e:
        raise CustomError(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error conectando con el LLM: {str(e)}")


@router.get('/capabilities')
def capabilities():
    return llm_provider.get_runtime_capabilities()
