import os
from dataclasses import dataclass
from dotenv import load_dotenv
from botocore.config import Config

from langchain_core.language_models.chat_models import BaseChatModel
# Load repo defaults first, then user runtime config from AppData.
# API_KEYS.env must win so Puter/API key changes survive backend restarts.
load_dotenv(override=True)
app_data = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
if app_data:
    api_keys_path = os.path.join(app_data, 'NeuralAgent', 'API_KEYS.env')
    if os.path.exists(api_keys_path):
        load_dotenv(dotenv_path=api_keys_path, override=True)


SUPPORTED_MODEL_TYPES = ("google", "openai", "azure_openai", "anthropic", "bedrock", "puter")
DEFAULT_PUTER_OPENAI_BASE_URL = "https://api.puter.com/puterai/openai/v1/"


@dataclass(frozen=True)
class AgentModelConfig:
    agent: str
    model_type: str
    model_id: str
    configured: bool
    missing: tuple[str, ...] = ()


def get_model_config(agent: str) -> AgentModelConfig:
    model_type = os.getenv(f"{agent.upper()}_AGENT_MODEL_TYPE") or os.getenv("DEFAULT_AGENT_MODEL_TYPE", "google")
    model_id = os.getenv(f"{agent.upper()}_AGENT_MODEL_ID") or os.getenv("DEFAULT_AGENT_MODEL_ID", "gemini-2.5-flash")
    missing: list[str] = []

    if model_type == "google" and not os.getenv("GEMINI_API_KEY"):
        missing.append("GEMINI_API_KEY")
    elif model_type == "openai" and not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    elif model_type == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    elif model_type == "azure_openai":
        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not os.getenv("AZURE_OPENAI_API_KEY"):
            missing.append("AZURE_OPENAI_API_KEY")
    elif model_type == "puter" and not os.getenv("PUTER_AUTH_TOKEN"):
        missing.append("PUTER_AUTH_TOKEN")
    elif model_type not in SUPPORTED_MODEL_TYPES:
        missing.append("SUPPORTED_MODEL_TYPE")

    return AgentModelConfig(
        agent=agent,
        model_type=model_type,
        model_id=model_id,
        configured=len(missing) == 0,
        missing=tuple(missing),
    )


def get_runtime_capabilities() -> dict:
    agents = ("classifier", "title", "suggestor", "planner", "computer_use")
    configs = [get_model_config(agent) for agent in agents]
    return {
        "runtime": "arkaios-neuralagent",
        "supported_model_types": list(SUPPORTED_MODEL_TYPES),
        "puter": {
            "server_side": bool(os.getenv("PUTER_AUTH_TOKEN")),
            "browser_login_supported": True,
            "openai_compatible_base_url": os.getenv("PUTER_OPENAI_BASE_URL", DEFAULT_PUTER_OPENAI_BASE_URL),
        },
        "agents": [
            {
                "agent": cfg.agent,
                "model_type": cfg.model_type,
                "model_id": cfg.model_id,
                "configured": cfg.configured,
                "missing": list(cfg.missing),
            }
            for cfg in configs
        ],
    }

def get_llm(agent: str, temperature: float = 0.0, max_tokens: int = None, thinking_enabled: bool = False) -> BaseChatModel:
    """
    Get an LLM instance based on agent name and environment variables.

    Args:
        agent (str): Logical name of the agent, e.g., "planner", "suggestor", "computer_use", "classifier", "title"
        temperature (float): Sampling temperature
        max_tokens (int): Optional token limit
        thinking_enabled (bool): Enable extended thinking (Anthropic/Bedrock only)

    Returns:
        langchain-compatible LLM object
    """
    config = get_model_config(agent)
    model_type = config.model_type
    model_id = config.model_id

    if not model_type or not model_id:
        raise ValueError(f"Missing model config for agent: {agent}")

    if model_type == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        google_api_key = os.getenv("GEMINI_API_KEY")
        if not google_api_key:
            raise ValueError("Missing GEMINI_API_KEY")

        return ChatGoogleGenerativeAI(
            model=model_id,
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=google_api_key,
            timeout=float(os.getenv("GEMINI_TIMEOUT", "20")),
            max_retries=int(os.getenv("GEMINI_MAX_RETRIES", "1")),
        )

    elif model_type == "azure_openai":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=model_id,
            api_version=os.getenv("OPENAI_API_VERSION", "2024-12-01-preview"),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=None,
            max_retries=2
        )
    
    elif model_type == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=None,
            max_retries=2
        )

    elif model_type == "puter":
        from langchain_openai import ChatOpenAI

        puter_auth_token = os.getenv("PUTER_AUTH_TOKEN")
        if not puter_auth_token:
            raise ValueError("Missing PUTER_AUTH_TOKEN")

        return ChatOpenAI(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=puter_auth_token,
            base_url=os.getenv("PUTER_OPENAI_BASE_URL", DEFAULT_PUTER_OPENAI_BASE_URL),
            timeout=float(os.getenv("PUTER_TIMEOUT", "30")),
            max_retries=int(os.getenv("PUTER_MAX_RETRIES", "2")),
        )

    elif model_type == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not thinking_enabled:
            return ChatAnthropic(
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=None,
                max_retries=2,
            )
        else:
            return ChatAnthropic(
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=None,
                max_retries=2,
                thinking={"type": "enabled", "budget_tokens": 2000},
            )

    elif model_type == "bedrock":
        from langchain_aws import ChatBedrockConverse

        thinking_params = {
            "thinking": {
                "type": "enabled",
                "budget_tokens": 2000
            }
        }
        boto3_config = Config(
            connect_timeout=300,
            read_timeout=300,
            retries={'max_attempts': 5},
            region_name=os.getenv("BEDROCK_REGION", "us-east-1")
        )
        if thinking_enabled and 'claude' in model_id:
            return ChatBedrockConverse(
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                config=boto3_config,
                region_name=os.getenv("BEDROCK_REGION", "us-east-1"),
                additional_model_request_fields=thinking_params
            )
        else:
            return ChatBedrockConverse(
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                config=boto3_config,
                region_name=os.getenv("BEDROCK_REGION", "us-east-1")
            )

    else:
        raise ValueError(f"Unsupported model type '{model_type}' for agent '{agent}'")
