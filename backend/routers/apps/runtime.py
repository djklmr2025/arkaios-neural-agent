from fastapi import APIRouter, Depends, status
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from dependencies.auth_dependencies import get_current_user_dependency
from db.models import User
from schemas.runtime import RuntimeChatRequest, RuntimePlanRequest
from utils import ai_prompts, llm_provider
from utils.procedures import CustomError, extract_json


router = APIRouter(
    prefix="/apps/runtime",
    tags=["apps", "runtime"],
)


@router.get("/capabilities")
def capabilities():
    return llm_provider.get_runtime_capabilities()


@router.post("/chat")
def runtime_chat(request: RuntimeChatRequest, user: User = Depends(get_current_user_dependency)):
    try:
        llm = llm_provider.get_llm(
            agent=request.agent,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        messages = [
            SystemMessage(content=request.system_prompt or ai_prompts.CLASSIFIER_AGENT_PROMPT)
        ]
        if request.context:
            messages.append(HumanMessage(content=f"Contexto disponible:\n{request.context}"))
        messages.append(HumanMessage(content=request.message))

        response = llm.invoke(messages)
        return {
            "status": "success",
            "agent": request.agent,
            "message": response.content,
        }
    except Exception as exc:
        raise CustomError(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Runtime chat failed: {str(exc)}")


@router.post("/plan")
def runtime_plan(request: RuntimePlanRequest, user: User = Depends(get_current_user_dependency)):
    try:
        llm = llm_provider.get_llm(agent="planner", temperature=0.3)
        plan_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(ai_prompts.PLANNER_AGENT_PROMPT),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": f"Current OS: {request.current_os}\n\nCurrent Visible OS Native Interactive Elements: {request.current_interactive_elements}",
                },
                {
                    "type": "text",
                    "text": f"Current Running Apps: {request.current_running_apps}",
                },
                {
                    "type": "text",
                    "text": f"Task: {request.task}",
                },
            ]),
        ])

        response = (plan_prompt | llm).invoke({})
        return {
            "status": "success",
            "plan": extract_json(response.content),
        }
    except Exception as exc:
        raise CustomError(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Runtime planning failed: {str(exc)}")
