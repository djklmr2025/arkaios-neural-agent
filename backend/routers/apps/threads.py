from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select, and_, update
from dependencies.auth_dependencies import get_current_user_dependency
from db.database import get_session
from db.models import (User, Thread, ThreadStatus, ThreadTask, ThreadMessage, ThreadChatType, ThreadChatFromChoices,
                       ThreadTaskStatus, ThreadTaskPlan, ThreadTaskPlanStatus, PlanSubtask, SubtaskStatus)
from schemas.threads import ListThread, CreateThread, UpdateThread, ListThreadMessage, RetrieveThread, SendMessageObj
from typing import List
from utils.procedures import CustomError, extract_json, normalize_llm_error
from utils import ai_helpers
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from utils import ai_prompts, llm_provider
import json
import re
import datetime


router = APIRouter(
    prefix='/apps/threads',
    tags=['apps', 'threads'],
    dependencies=[Depends(get_current_user_dependency)]
)


DESKTOP_TASK_HINTS = (
    'abre', 'abrir', 'abreme', 'abrir', 'open', 'launch', 'ejecuta', 'inicia',
    'mueve', 'click', 'clic', 'teclea', 'escribe', 'manda', 'envia', 'envía',
    'busca', 'descarga', 'instala', 'cierra', 'guarda', 'crea', 'haz',
    'usa', 'entra', 've a', 'navega', 'notepad', 'bloc de notas', 'chrome',
    'whatsapp', 'vscode', 'visual studio code', 'reproductor', 'musica',
    'música', 'media player', 'windows media', 'spotify'
)


def fallback_classifier_response(task_text: str, background_mode: bool = False, extended_thinking_mode: bool = False) -> dict:
    normalized = (task_text or '').strip().lower()
    is_desktop_task = any(re.search(rf'\b{re.escape(hint)}\b', normalized) for hint in DESKTOP_TASK_HINTS)
    if is_desktop_task:
        return {
            'type': 'desktop_task',
            'response': 'Claro, lo hago ahora.',
            'is_browser_task': any(word in normalized for word in ('web', 'browser', 'navega', 'chrome', 'busca')),
            'needs_memory_from_previous_tasks': any(word in normalized for word in ('anterior', 'antes', 'mismo', 'otra vez')),
            'is_background_mode_requested': bool(background_mode),
            'is_extended_thinking_mode_requested': bool(extended_thinking_mode),
            'classifier_fallback': True,
        }

    return {
        'type': 'inquiry',
        'response': 'Estoy aqui y listo para ayudarte.',
        'is_browser_task': False,
        'needs_memory_from_previous_tasks': False,
        'is_background_mode_requested': bool(background_mode),
        'is_extended_thinking_mode_requested': bool(extended_thinking_mode),
        'classifier_fallback': True,
    }


def classify_user_task(task_text: str, previous_tasks_arr: list, background_mode: bool = False, extended_thinking_mode: bool = False) -> dict:
    try:
        llm = llm_provider.get_llm(agent='classifier', temperature=0.1)
        prompt = ChatPromptTemplate.from_messages([
            ('system', ai_prompts.CLASSIFIER_AGENT_PROMPT),
            HumanMessage(f'Previous Tasks (Limited to 10): \n {json.dumps(previous_tasks_arr)}'),
            ('user', task_text),
        ])
        chain = prompt | llm
        response = chain.invoke({})
        return extract_json(response.content)
    except Exception as exc:
        print(f'[threads] classifier unavailable, using local fallback: {normalize_llm_error(exc)}')
        return fallback_classifier_response(task_text, background_mode, extended_thinking_mode)


def cancel_stale_running_tasks(db: Session, user: User, max_age_seconds: int = 60) -> None:
    cutoff = datetime.datetime.now() - datetime.timedelta(seconds=max_age_seconds)
    stale_threads = db.exec(select(Thread).where(and_(
        Thread.user_id == user.id,
        Thread.status == ThreadStatus.WORKING,
        Thread.updated_at <= cutoff,
    ))).all()
    stale_thread_ids = [thread.id for thread in stale_threads]
    if not stale_thread_ids:
        return

    db.exec(update(Thread).where(Thread.id.in_(stale_thread_ids)).values(
        status=ThreadStatus.STANDBY,
    ))
    db.exec(update(ThreadTask).where(and_(
        ThreadTask.thread_id.in_(stale_thread_ids),
        ThreadTask.status == ThreadTaskStatus.WORKING,
    )).values(
        status=ThreadTaskStatus.CANCELED,
    ))
    db.exec(update(ThreadTaskPlan).where(and_(
        ThreadTaskPlan.thread_task.has(ThreadTask.thread_id.in_(stale_thread_ids)),
        ThreadTaskPlan.status == ThreadTaskPlanStatus.ACTIVE,
    )).values(
        status=ThreadTaskPlanStatus.CANCELED,
    ))
    db.exec(update(PlanSubtask).where(and_(
        PlanSubtask.plan.has(ThreadTaskPlan.thread_task.has(ThreadTask.thread_id.in_(stale_thread_ids))),
        PlanSubtask.status == SubtaskStatus.ACTIVE,
    )).values(
        status=SubtaskStatus.CANCELED,
    ))
    db.commit()


@router.get('', response_model=List[ListThread])
def list_threads(db: Session = Depends(get_session), user: User = Depends(get_current_user_dependency)):
    query = select(Thread).where(and_(
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    )).order_by(Thread.created_at.desc())
    return db.exec(query)


@router.post('')
def create_thread(create_thread_obj: CreateThread, db: Session = Depends(get_session),
                  user: User = Depends(get_current_user_dependency)):

    cancel_stale_running_tasks(db, user)

    working_threads = db.exec(select(Thread).where(and_(
        Thread.user_id == user.id,
        Thread.status == ThreadStatus.WORKING
    )))
    if len(working_threads.all()) > 0:
        raise CustomError(status.HTTP_400_BAD_REQUEST, 'Running_Thread')

    previous_tasks = db.exec(select(ThreadTask).where(and_(
        ThreadTask.thread.has(Thread.user_id == user.id),
        ThreadTask.thread.has(Thread.status != ThreadStatus.DELETED),
    )).order_by(ThreadTask.created_at.desc()).limit(10)).all()
    previous_tasks_arr = []
    for previous_task in previous_tasks:
        previous_tasks_arr.append({
            'task': previous_task.task_text,
            'status': previous_task.status,
        })

    response_data = classify_user_task(
        create_thread_obj.task,
        previous_tasks_arr,
        create_thread_obj.background_mode,
        create_thread_obj.extended_thinking_mode,
    )

    if response_data.get('type') == 'desktop_task':
        if create_thread_obj.background_mode is True or response_data.get('is_background_mode_requested', False) is True:
            if response_data.get('is_browser_task') is False:
                raise CustomError(status.HTTP_400_BAD_REQUEST, 'Not_Browser_Task_BG_Mode')

    instance = Thread(
        title=ai_helpers.generate_thread_title(create_thread_obj.task),
        user_id=user.id,
        current_task=create_thread_obj.task,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)

    user_message = ThreadMessage(
        thread_id=instance.id,
        thread_chat_type=ThreadChatType.NORMAL_MESSAGE,
        thread_chat_from=ThreadChatFromChoices.FROM_USER,
        text=create_thread_obj.task,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    response_data['thread_id'] = instance.id

    if response_data.get('type') == 'desktop_task':
        thread_task = ThreadTask(
            thread_id=instance.id,
            task_text=create_thread_obj.task,
            needs_memory_from_previous_tasks=response_data.get('needs_memory_from_previous_tasks', False),
            background_mode=create_thread_obj.background_mode or response_data.get('is_background_mode_requested', False),
            extended_thinking_mode=create_thread_obj.extended_thinking_mode or response_data.get('is_extended_thinking_mode_requested', False),
        )
        db.add(thread_task)
        db.commit()
        db.refresh(thread_task)

        ai_message = ThreadMessage(
            thread_id=instance.id,
            thread_chat_type=ThreadChatType.CLASSIFICATION,
            thread_chat_from=ThreadChatFromChoices.FROM_AI,
            text=json.dumps(response_data),
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        instance.status = ThreadStatus.WORKING
        db.add(instance)
        db.commit()
        db.refresh(instance)

        return response_data
    else:
        ai_message = ThreadMessage(
            thread_id=instance.id,
            thread_chat_type=ThreadChatType.CLASSIFICATION,
            thread_chat_from=ThreadChatFromChoices.FROM_AI,
            text=json.dumps(response_data),
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        return response_data


@router.put('/{tid}')
def update_thread(tid: str, update_obj: UpdateThread, db: Session = Depends(get_session), user: User = Depends(get_current_user_dependency)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    instance.title = update_obj.title
    db.add(instance)
    db.commit()
    db.refresh(instance)

    return {'message': 'Success'}


@router.delete('/{tid}')
def delete_thread(tid: str, db: Session = Depends(get_session), user: User = Depends(get_current_user_dependency)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    if instance.status == ThreadStatus.WORKING:
        raise CustomError(status.HTTP_400_BAD_REQUEST, 'Cannot_Delete_Working_Thread')

    instance.status = ThreadStatus.DELETED
    db.add(instance)
    db.commit()
    db.refresh(instance)

    return {'message': 'Success'}


@router.get('/{tid}', response_model=RetrieveThread)
def retrieve_thread(tid: str, db: Session = Depends(get_session), user: User = Depends(get_current_user_dependency)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    return instance


@router.get('/{tid}/thread_messages', response_model=List[ListThreadMessage])
def thread_messages(tid: str, db: Session = Depends(get_session), user: User = Depends(get_current_user_dependency)):
    query = select(ThreadMessage).where(and_(
        ThreadMessage.thread_id == tid,
        ThreadMessage.thread.has(Thread.user_id == user.id),
    )).order_by(ThreadMessage.created_at.asc())
    return db.exec(query)


@router.post('/cancel_all_running_tasks')
def cancel_all_running_tasks(db: Session = Depends(get_session), user: User = Depends(get_current_user_dependency)):
    user_thread_filter = ThreadTask.thread.has(Thread.user_id == user.id)
    user_plan_filter = ThreadTaskPlan.thread_task.has(ThreadTask.thread.has(Thread.user_id == user.id))
    user_subtask_filter = PlanSubtask.plan.has(ThreadTaskPlan.thread_task.has(ThreadTask.thread.has(Thread.user_id == user.id)))

    db.exec(update(Thread).where(and_(
        Thread.user_id == user.id,
        Thread.status == ThreadStatus.WORKING,
    )).values(
        status=ThreadStatus.STANDBY,
    ))

    db.exec(update(ThreadTask).where(and_(
        user_thread_filter,
        ThreadTask.status == ThreadTaskStatus.WORKING,
    )).values(
        status=ThreadTaskStatus.CANCELED,
    ))

    db.exec(update(ThreadTaskPlan).where(and_(
        user_plan_filter,
        ThreadTaskPlan.status == ThreadTaskPlanStatus.ACTIVE,
    )).values(
        status=ThreadTaskPlanStatus.CANCELED,
    ))

    db.exec(update(PlanSubtask).where(and_(
        user_subtask_filter,
        PlanSubtask.status == SubtaskStatus.ACTIVE,
    )).values(
        status=SubtaskStatus.CANCELED,
    ))

    db.commit()

    return {'message': 'Success'}


@router.post('/{tid}/cancel_task')
def cancel_running_task(tid: str, db: Session = Depends(get_session), user: User = Depends(get_current_user_dependency)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    if instance.status != ThreadStatus.WORKING:
        raise CustomError(status.HTTP_400_BAD_REQUEST, 'Not_Running')

    instance.status = ThreadStatus.STANDBY
    db.add(instance)
    db.commit()
    db.refresh(instance)

    running_task = db.exec(select(ThreadTask).where(and_(
        ThreadTask.thread_id == tid,
        ThreadTask.status == ThreadTaskStatus.WORKING
    ))).first()

    if running_task:
        running_task.status = ThreadTaskStatus.CANCELED
        db.add(running_task)
        db.commit()
        db.refresh(running_task)

        db.exec(update(ThreadTaskPlan).where(ThreadTaskPlan.thread_task_id == running_task.id).values(
            status=ThreadTaskPlanStatus.CANCELED,
        ))

        db.exec(update(PlanSubtask).where(PlanSubtask.plan.has(ThreadTaskPlan.thread_task_id == running_task.id)).values(
            status=SubtaskStatus.CANCELED,
        ))

    ai_message = ThreadMessage(
        thread_id=instance.id,
        thread_task_id=running_task.id,
        thread_chat_type=ThreadChatType.DESKTOP_USE,
        thread_chat_from=ThreadChatFromChoices.FROM_AI,
        text=json.dumps({'actions': [{'action': 'task_canceled'}]}),
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)

    return {'message': 'Success'}


@router.post('/{tid}/send_message')
def send_message(tid: str, obj: SendMessageObj, db: Session = Depends(get_session),
                 user: User = Depends(get_current_user_dependency)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    cancel_stale_running_tasks(db, user)

    working_threads = db.exec(select(Thread).where(and_(
        Thread.user_id == user.id,
        Thread.status == ThreadStatus.WORKING
    )))
    if len(working_threads.all()) > 0:
        raise CustomError(status.HTTP_400_BAD_REQUEST, 'Running_Thread')

    previous_tasks = db.exec(select(ThreadTask).where(and_(
        ThreadTask.thread.has(Thread.user_id == user.id),
        ThreadTask.thread.has(Thread.status != ThreadStatus.DELETED),
    )).order_by(ThreadTask.created_at.desc()).limit(10)).all()
    previous_tasks_arr = []
    for previous_task in previous_tasks:
        previous_tasks_arr.append({
            'task': previous_task.task_text,
            'status': previous_task.status,
        })

    response_data = classify_user_task(
        obj.text,
        previous_tasks_arr,
        obj.background_mode,
        obj.extended_thinking_mode,
    )

    if response_data.get('type') == 'desktop_task':
        if obj.background_mode is True or response_data.get('is_background_mode_requested', False) is True:
            if response_data.get('is_browser_task') is False:
                raise CustomError(status.HTTP_400_BAD_REQUEST, 'Not_Browser_Task_BG_Mode')

    user_message = ThreadMessage(
        thread_id=instance.id,
        thread_chat_type=ThreadChatType.NORMAL_MESSAGE,
        thread_chat_from=ThreadChatFromChoices.FROM_USER,
        text=obj.text,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    if response_data.get('type') == 'desktop_task':
        thread_task = ThreadTask(
            thread_id=instance.id,
            task_text=obj.text,
            needs_memory_from_previous_tasks=response_data.get('needs_memory_from_previous_tasks', False),
            background_mode=obj.background_mode or response_data.get('is_background_mode_requested', False),
            extended_thinking_mode=obj.extended_thinking_mode or response_data.get('is_extended_thinking_mode_requested', False),
        )
        db.add(thread_task)
        db.commit()
        db.refresh(thread_task)

        ai_message = ThreadMessage(
            thread_id=instance.id,
            thread_chat_type=ThreadChatType.CLASSIFICATION,
            thread_chat_from=ThreadChatFromChoices.FROM_AI,
            text=json.dumps(response_data),
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        instance.status = ThreadStatus.WORKING
        db.add(instance)
        db.commit()
        db.refresh(instance)

        return response_data
    else:
        ai_message = ThreadMessage(
            thread_id=instance.id,
            thread_chat_type=ThreadChatType.CLASSIFICATION,
            thread_chat_from=ThreadChatFromChoices.FROM_AI,
            text=json.dumps(response_data),
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        return response_data
