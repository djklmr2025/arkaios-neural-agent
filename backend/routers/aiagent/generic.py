from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select, and_
from db.database import get_session
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
import json
from utils import ai_prompts
from utils.procedures import CustomError, extract_json, normalize_llm_error
from dependencies.auth_dependencies import get_current_user_dependency
from db.models import (User, Thread, ThreadStatus, ThreadTask, ThreadTaskStatus, ThreadMessage,
                       ThreadChatType, ThreadChatFromChoices, ThreadTaskPlan, ThreadTaskPlanStatus,
                       PlanSubtask, SubtaskStatus, ThreadTaskMemoryEntry, SubtaskType)
from schemas.aiagent import NextStepRequest, CurrentSubtaskRequestObj
from utils.agentic_tools import run_tool_server_side
from utils import llm_provider
from utils.safety_guard import evaluate_actions
from base64 import b64decode
import io
import os
import requests
from utils import upload_helper


def build_fallback_plan(task_text: str) -> dict:
    normalized = (task_text or '').lower()
    if 'notepad' in normalized or 'bloc de notas' in normalized or 'block de notas' in normalized:
        return {'subtasks': [{'subtask': 'Open Notepad', 'type': 'desktop_subtask'}]}
    if is_music_player_request(normalized):
        return {'subtasks': [{'subtask': 'Open a music player', 'type': 'desktop_subtask'}]}
    return {'subtasks': [{'subtask': task_text or 'Complete the requested desktop task', 'type': 'desktop_subtask'}]}


def is_music_player_request(text: str) -> bool:
    return any(
        hint in text
        for hint in (
            'reproductor',
            'musica',
            'música',
            'media player',
            'windows media',
            'groove',
            'spotify',
            'player',
        )
    )


def music_player_is_running(current_running_apps: list[dict]) -> bool:
    return any(
        app_is_running(current_running_apps, app_name)
        for app_name in ('wmplayer', 'media player', 'music.ui', 'spotify')
    )


def app_is_running(current_running_apps: list[dict], app_name: str) -> bool:
    needle = app_name.lower()
    for app in current_running_apps or []:
        values = [str(value).lower() for value in app.values()]
        if any(needle in value for value in values):
            return True
    return False


def build_proxy_planned_next_step(task_text: str, subtask_text: str) -> dict | None:
    planner_url = os.getenv('ARKAIOS_ACTION_PLANNER_URL')
    if not planner_url:
        return None

    objective = f'{task_text or ""}\n{subtask_text or ""}'.strip()
    headers = {'Content-Type': 'application/json'}
    planner_key = os.getenv('ARKAIOS_ACTION_PLANNER_KEY') or os.getenv('PROXY_API_KEY')
    if planner_key:
        headers['Authorization'] = f'Bearer {planner_key}'

    try:
        response = requests.post(
            planner_url,
            headers=headers,
            json={
                'objective': objective,
                'source': 'neuralagent-local-fallback',
                'capabilities': ['launch_app'],
            },
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        print(f'[aiagent] action planner unavailable, using built-in fallback: {exc}')
        return None

    if not data.get('approved') or not data.get('action'):
        return None

    planned_action = data['action']
    action_name = planned_action.get('action')
    params = planned_action.get('params') or {}
    if action_name != 'open_app':
        return None

    app_name = params.get('app_name')
    if not app_name:
        return None

    return {
        'current_state': {
            'evaluation_previous_goal': 'Unknown - The cloud action planner approved a safe local app launch.',
            'memory': f'The approved action is to open {app_name}.',
            'save_to_memory': False,
            'next_goal': f'Launch {app_name}.',
        },
        'actions': [{'action': 'launch_app', 'params': {'app_name': app_name}}],
        'agent_fallback': True,
        'action_planner': {
            'source': data.get('source'),
            'risk': data.get('risk'),
            'confidence': data.get('confidence'),
            'reason': data.get('reason'),
        },
    }


def build_fallback_next_step(task_text: str, subtask_text: str, current_running_apps: list[dict]) -> dict:
    normalized = f'{task_text or ""} {subtask_text or ""}'.lower()
    proxy_plan = build_proxy_planned_next_step(task_text, subtask_text)
    if proxy_plan:
        planned_app = proxy_plan['actions'][0]['params']['app_name']
        if app_is_running(current_running_apps, planned_app):
            return {
                'current_state': {
                    'evaluation_previous_goal': f'Success - {planned_app} is running.',
                    'memory': f'{planned_app} has been opened successfully.',
                    'save_to_memory': False,
                    'next_goal': f'Complete the subtask because {planned_app} is open.',
                },
                'actions': [{'action': 'subtask_completed', 'params': {}}],
                'agent_fallback': True,
                'action_planner': proxy_plan.get('action_planner'),
            }
        return proxy_plan

    if 'notepad' in normalized or 'bloc de notas' in normalized or 'block de notas' in normalized:
        if app_is_running(current_running_apps, 'notepad'):
            return {
                'current_state': {
                    'evaluation_previous_goal': 'Success - Notepad is running.',
                    'memory': 'Notepad has been opened successfully.',
                    'save_to_memory': False,
                    'next_goal': 'Complete the subtask because Notepad is open.',
                },
                'actions': [{'action': 'subtask_completed', 'params': {}}],
                'agent_fallback': True,
            }
        return {
            'current_state': {
                'evaluation_previous_goal': 'Unknown - Notepad is not running yet.',
                'memory': 'The goal is to open Notepad.',
                'save_to_memory': False,
                'next_goal': 'Launch Notepad.',
            },
            'actions': [{'action': 'launch_app', 'params': {'app_name': 'Notepad'}}],
            'agent_fallback': True,
        }

    if is_music_player_request(normalized):
        if music_player_is_running(current_running_apps):
            return {
                'current_state': {
                    'evaluation_previous_goal': 'Success - A music player is running.',
                    'memory': 'A music player has been opened successfully.',
                    'save_to_memory': False,
                    'next_goal': 'Complete the subtask because a music player is open.',
                },
                'actions': [{'action': 'subtask_completed', 'params': {}}],
                'agent_fallback': True,
            }
        return {
            'current_state': {
                'evaluation_previous_goal': 'Unknown - No music player is running yet.',
                'memory': 'The goal is to open a Windows music player.',
                'save_to_memory': False,
                'next_goal': 'Launch a Windows music player.',
            },
            'actions': [{'action': 'launch_app', 'params': {'app_name': 'Windows Media Player'}}],
            'agent_fallback': True,
        }

    return {
        'current_state': {
            'evaluation_previous_goal': 'Failed - The local fallback does not know how to complete this task without the AI provider.',
            'memory': 'The configured AI provider is unavailable for this task.',
            'save_to_memory': False,
            'next_goal': 'Report the task as failed.',
        },
        'actions': [{'action': 'subtask_failed', 'params': {}}],
        'agent_fallback': True,
    }


router = APIRouter(
    prefix='/aiagent',
    tags=['aiagent'],
    dependencies=[Depends(get_current_user_dependency)]
)


@router.post('/{tid}/current_subtask')
def current_subtask_request(tid: str, current_subtask_request_obj: CurrentSubtaskRequestObj,
                            db: Session = Depends(get_session), user: User = Depends(get_current_user_dependency)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status == ThreadStatus.WORKING
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    task = db.exec(select(ThreadTask).where(and_(
        ThreadTask.thread_id == tid,
        ThreadTask.status == ThreadTaskStatus.WORKING,
    ))).first()

    if not task:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread has no running task')

    current_plan = db.exec(select(ThreadTaskPlan).where(and_(
        ThreadTaskPlan.thread_task_id == task.id,
        ThreadTaskPlan.status == ThreadTaskPlanStatus.ACTIVE,
    ))).first()

    if not current_plan:
        previous_tasks = db.exec(select(ThreadTask).where(and_(
            ThreadTask.thread.has(Thread.user_id == user.id),
            ThreadTask.thread.has(Thread.status != ThreadStatus.DELETED),
            ThreadTask.status != ThreadTaskStatus.WORKING,
        )).order_by(ThreadTask.created_at.desc()).limit(10)).all()
        previous_tasks_arr = []
        for previous_task in previous_tasks:
            previous_tasks_arr.append({
                'task': previous_task.task_text,
                'status': previous_task.status,
            })

        llm = llm_provider.get_llm(agent='planner', temperature=0.3)

        plan_user_message = [
            {
                'type': 'text',
                'text': f'Current OS: {current_subtask_request_obj.current_os} \n\nCurrent Visible OS Native Interactive Elements: {json.dumps(current_subtask_request_obj.current_interactive_elements)}'
            },
            {
                'type': 'text',
                'text': f'Current Running Apps: {json.dumps(current_subtask_request_obj.current_running_apps)}'
            }
        ]

        if len(previous_tasks_arr) > 0:
            plan_user_message.append({
                'type': 'text',
                'text': f'Previous Tasks (Limited to 10): \n {json.dumps(previous_tasks_arr)}',
            })

        plan_user_message.append({
            'type': 'text',
            'text': f'Task: {task.task_text}'
        })

        plan_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(ai_prompts.PLANNER_AGENT_PROMPT),
            HumanMessage(content=plan_user_message),
        ])

        try:
            chain = plan_prompt | llm
            plan_response = chain.invoke({})
            plan_response_data = extract_json(plan_response.content)
        except Exception as exc:
            print(f'[aiagent] planner unavailable, using local fallback: {normalize_llm_error(exc)}')
            plan_response_data = build_fallback_plan(task.task_text)

        plan = plan_response_data.get('subtasks')

        plan_ai_message = ThreadMessage(
            thread_id=instance.id,
            thread_chat_type=ThreadChatType.PLAN,
            thread_chat_from=ThreadChatFromChoices.FROM_AI,
            text=json.dumps(plan_response_data),
        )
        db.add(plan_ai_message)
        db.commit()
        db.refresh(plan_ai_message)

        current_plan = ThreadTaskPlan(
            thread_task_id=task.id,
        )
        db.add(current_plan)
        db.commit()
        db.refresh(current_plan)

        for i, subtask_item in enumerate(plan):
            subtask = PlanSubtask(
                thread_task_plan_id=current_plan.id,
                subtask_text=subtask_item.get('subtask'),
                subtask_type=SubtaskType.DESKTOP,
                # subtask_type=SubtaskType.DESKTOP if subtask_item.get(
                #     'type') == 'desktop_subtask' else SubtaskType.BROWSER,
                ordering=i + 1,
            )
            db.add(subtask)
            db.commit()
            db.refresh(subtask)

    current_subtask = db.exec(select(PlanSubtask).where(and_(
        PlanSubtask.status == SubtaskStatus.ACTIVE,
        PlanSubtask.thread_task_plan_id == current_plan.id
    )).order_by(PlanSubtask.ordering.asc())).first()

    if not current_subtask:
        current_plan.status = ThreadTaskPlanStatus.COMPLETED
        db.add(current_plan)
        db.commit()
        db.refresh(current_plan)

        task.status = ThreadTaskStatus.COMPLETED
        db.add(task)
        db.commit()
        db.refresh(task)

        instance.status = ThreadStatus.STANDBY
        db.add(instance)
        db.commit()
        db.refresh(instance)

        ai_message = ThreadMessage(
            thread_id=instance.id,
            thread_task_id=task.id,
            thread_chat_type=ThreadChatType.DESKTOP_USE,
            thread_chat_from=ThreadChatFromChoices.FROM_AI,
            text=json.dumps({'actions': [{'action': 'task_completed'}]}),
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        return {'action': 'task_completed'}

    return {
        'id': current_subtask.id,
        'subtask_text': current_subtask.subtask_text,
        'subtask_type': current_subtask.subtask_type,
        'status': current_subtask.status,
    }


@router.post('/{tid}/next_step')
def next_step(tid: str, next_step_req: NextStepRequest, db: Session = Depends(get_session),
              user: User = Depends(get_current_user_dependency)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status == ThreadStatus.WORKING
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    task = db.exec(select(ThreadTask).where(and_(
        ThreadTask.thread_id == tid,
        ThreadTask.status == ThreadTaskStatus.WORKING,
    ))).first()

    if not task:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread has no running task')

    current_plan = db.exec(select(ThreadTaskPlan).where(and_(
        ThreadTaskPlan.thread_task_id == task.id,
        ThreadTaskPlan.status == ThreadTaskPlanStatus.ACTIVE,
    ))).first()

    current_subtask = db.exec(select(PlanSubtask).where(and_(
        PlanSubtask.status == SubtaskStatus.ACTIVE,
        PlanSubtask.thread_task_plan_id == current_plan.id
    )).order_by(PlanSubtask.ordering.asc())).first()
    if not current_subtask or current_subtask.subtask_type != SubtaskType.DESKTOP:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'No Current Desktop Task!')

    if task.extended_thinking_mode is True:
        llm = llm_provider.get_llm(agent='computer_use', temperature=1.0, thinking_enabled=True)
    else:
        llm = llm_provider.get_llm(agent='computer_use', temperature=0.0)

    previous_subtasks = db.exec(select(PlanSubtask).where(and_(
        PlanSubtask.status != SubtaskStatus.ACTIVE,
        PlanSubtask.plan.has(ThreadTaskPlan.thread_task_id == task.id)
    )).order_by(PlanSubtask.ordering.asc())).all()
    previous_subtasks_arr = []
    for previous_subtask in previous_subtasks:
        previous_subtasks_arr.append({
            'subtask_text': previous_subtask.subtask_text,
            'status': previous_subtask.status,
        })

    screenshot_user_message_block = None
    screenshot_s3_path = None
    if next_step_req.screenshot_b64:
        if os.getenv('ENABLE_SCREENSHOT_LOGGING_FOR_TRAINING') == 'true':
            image_bytes = b64decode(next_step_req.screenshot_b64)
            image_io = io.BytesIO(image_bytes)
            screenshot_s3_path = upload_helper.upload_screenshot_s3_bytesio(image_io, extension="png")
        
        screenshot_user_message_block = {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{next_step_req.screenshot_b64}"}
        }

    action_history = []
    task_previous_messages = db.exec(
        select(ThreadMessage)
        .where(
            and_(
                ThreadMessage.thread_task_id == task.id,
                ThreadMessage.thread_chat_type == ThreadChatType.DESKTOP_USE,
            )
        )
        .order_by(ThreadMessage.created_at.desc())
        .limit(5)
    ).all()
    for previous_message in task_previous_messages:
        previous_action_dict = json.loads(previous_message.text)
        # previous_action_dict.pop("current_state", None)
        action_history.append(previous_action_dict)

    if task.needs_memory_from_previous_tasks is True:
        tasks_for_memory = db.exec(select(ThreadTask).where(and_(
            ThreadTask.thread.has(Thread.user_id == user.id),
            ThreadTask.thread.has(Thread.status != ThreadStatus.DELETED),
        )).order_by(ThreadTask.created_at.desc()).limit(5)).all()
        tasks_for_memory_ids = [task.id for task in tasks_for_memory]
        memory_items = db.exec(
            select(ThreadTaskMemoryEntry).where(
                ThreadTaskMemoryEntry.thread_task_id.in_(tasks_for_memory_ids)
            )
        ).all()
    else:
        memory_items = db.exec(select(ThreadTaskMemoryEntry).where(
            ThreadTaskMemoryEntry.thread_task_id == task.id
        )).all()

    memory_items_arr = []
    for memory_item in memory_items:
        memory_items_arr.append({
            'memory_item_text': memory_item.text,
        })

    computer_use_user_message = [
        {
            'type': 'text',
            'text': f'Current Subtask: {current_subtask.subtask_text}'
        },
        {
            'type': 'text',
            'text': f'Current OS: {next_step_req.current_os} \n\nCurrent Visible OS Native Interactive Elements: {json.dumps(next_step_req.current_interactive_elements)}'
        },
        {
            'type': 'text',
            'text': f'Current Running Apps: {json.dumps(next_step_req.current_running_apps)}'
        }
    ]

    if len(memory_items_arr) > 0:
        computer_use_user_message.append({
            'type': 'text',
            'text': f'Stored Memory Items: \n {json.dumps(memory_items_arr)}'
        })
    if len(action_history) > 0:
        computer_use_user_message.append({
            'type': 'text',
            'text': f'Previous Actions (Limited to 5, newest first): \n {json.dumps(action_history)}'
        })
    if len(previous_subtasks_arr) > 0:
        computer_use_user_message.append({
            'type': 'text',
            'text': f'Previous Subtasks: \n {json.dumps(previous_subtasks_arr)}'
        })
    
    computer_use_text_prompt = computer_use_user_message.copy()
    
    if screenshot_user_message_block:
        computer_use_user_message.append(screenshot_user_message_block)

    soul_id = os.environ.get("ARKAIOS_NODE_SOUL_ID", "ARKAIOS-NODE-GENESIS")
    system_prompt = ai_prompts.COMPUTER_USE_SYSTEM_PROMPT.replace("{{SOUL_ID}}", soul_id)

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content=computer_use_user_message),
    ])

    try:
        chain = prompt | llm
        response = chain.invoke({})

        print('Token Usage: ', response.usage_metadata)

        response_data = None
        if task.extended_thinking_mode is True:
            for response_item in response.content:
                if response_item.get('type') == 'reasoning_content':
                    thinking_message = ThreadMessage(
                        thread_id=instance.id,
                        thread_task_id=task.id,
                        thread_chat_type=ThreadChatType.THINKING,
                        thread_chat_from=ThreadChatFromChoices.FROM_AI,
                        chain_of_thought=response_item.get('reasoning_content', {}).get('text'),
                    )
                    db.add(thinking_message)
                    db.commit()
                    db.refresh(thinking_message)
                elif response_item.get('type') == 'text':
                    response_data = extract_json(response_item.get('text'))
        else:
            response_data = extract_json(response.content)
    except Exception as exc:
        print(f'[aiagent] computer-use unavailable, using local fallback: {normalize_llm_error(exc)}')
        response_data = build_fallback_next_step(task.task_text, current_subtask.subtask_text, next_step_req.current_running_apps)

    ai_message = ThreadMessage(
        thread_id=instance.id,
        thread_task_id=task.id,
        plan_subtask_id=current_subtask.id,
        thread_chat_type=ThreadChatType.DESKTOP_USE,
        thread_chat_from=ThreadChatFromChoices.FROM_AI,
        screenshot=screenshot_s3_path,
        prompt=json.dumps(computer_use_text_prompt),
        text=json.dumps(response_data),
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)

    if response_data.get('current_state', {}).get('save_to_memory', False):
        memory_text = response_data['current_state'].get('memory')
        if memory_text:
            memory_entry = ThreadTaskMemoryEntry(
                thread_task_id=task.id,
                text=memory_text,
            )
            db.add(memory_entry)
            db.commit()
            db.refresh(memory_entry)

    # Iterate over all actions
    actions_arr = response_data.get('actions', [])
    for act in actions_arr:
        action_type = act.get('action')

        if action_type == 'subtask_completed' and len(actions_arr) == 1:
            current_subtask.status = SubtaskStatus.COMPLETED
            db.add(current_subtask)
            db.commit()
            db.refresh(current_subtask)

            remaining_subtask = db.exec(select(PlanSubtask).where(and_(
                PlanSubtask.status == SubtaskStatus.ACTIVE,
                PlanSubtask.thread_task_plan_id == current_plan.id
            ))).first()

            if not remaining_subtask:
                current_plan.status = ThreadTaskPlanStatus.COMPLETED
                db.add(current_plan)
                db.commit()
                db.refresh(current_plan)

                task.status = ThreadTaskStatus.COMPLETED
                db.add(task)
                db.commit()
                db.refresh(task)

                instance.status = ThreadStatus.STANDBY
                db.add(instance)
                db.commit()
                db.refresh(instance)

                task_completed_message = ThreadMessage(
                    thread_id=instance.id,
                    thread_task_id=task.id,
                    thread_chat_type=ThreadChatType.DESKTOP_USE,
                    thread_chat_from=ThreadChatFromChoices.FROM_AI,
                    text=json.dumps({'actions': [{'action': 'task_completed'}]}),
                )
                db.add(task_completed_message)
                db.commit()
                db.refresh(task_completed_message)

        elif action_type == 'subtask_failed':
            # Mark plan, task, and thread as failed
            current_plan.status = ThreadTaskPlanStatus.FAILED
            db.add(current_plan)
            db.commit()
            db.refresh(current_plan)

            task.status = ThreadTaskStatus.FAILED
            db.add(task)
            db.commit()
            db.refresh(task)

            instance.status = ThreadStatus.STANDBY
            db.add(instance)
            db.commit()
            db.refresh(instance)

            ai_message = ThreadMessage(
                thread_id=instance.id,
                thread_task_id=task.id,
                thread_chat_type=ThreadChatType.DESKTOP_USE,
                thread_chat_from=ThreadChatFromChoices.FROM_AI,
                text=json.dumps({'actions': [{'action': 'task_failed'}]}),
            )
            db.add(ai_message)
            db.commit()
            db.refresh(ai_message)

        elif action_type == 'tool_use':
            tool = act['params'].get('tool')
            args = act['params'].get('args', {})

            if tool == 'save_to_memory':
                memory_entry = ThreadTaskMemoryEntry(
                    thread_task_id=task.id,
                    text=args.get('text', ''),
                )
                db.add(memory_entry)
                db.commit()
                db.refresh(memory_entry)

            elif tool in ['read_pdf', 'fetch_url', 'summarize_youtube_video']:
                tool_output_text = run_tool_server_side(tool, args)
                memory_entry = ThreadTaskMemoryEntry(
                    thread_task_id=task.id,
                    text=tool_output_text,
                )
                db.add(memory_entry)
                db.commit()
                db.refresh(memory_entry)

    # ── ARKAIOS Safety Guard ────────────────────────────────────────────────
    # Evaluate actions before sending them to the daemon for execution.
    # Skip evaluation for meta-actions that don't touch the OS.
    META_ACTIONS = {'subtask_completed', 'subtask_failed', 'request_screenshot',
                    'tool_use', 'wait'}
    actions_to_check = [
        a for a in response_data.get('actions', [])
        if a.get('action') not in META_ACTIONS
    ]

    if actions_to_check:
        guard_result = evaluate_actions(actions_to_check)

        if guard_result['blocked']:
            # Hard block — log and return error to daemon
            return {
                'arkaios_safety': 'BLOCKED',
                'reason': guard_result['blocked_reason'],
                'actions': [{'action': 'subtask_failed', 'params': {}}],
            }

        if guard_result['requires_confirmation']:
            # Soft block — daemon will pause and frontend shows confirmation modal
            return {
                'arkaios_safety': 'REQUIRES_CONFIRMATION',
                'risk_level': guard_result['risk_level'],
                'flagged_actions': guard_result['flagged_actions'],
                'pending_actions': response_data.get('actions', []),
                'actions': [{'action': 'wait', 'params': {'duration': 1, 'reason': 'Waiting for user confirmation'}}],
            }

    return response_data
