import os
from dotenv import load_dotenv

load_dotenv(override=True)
os.environ.setdefault("CLASSIFIER_AGENT_MODEL_TYPE", "google")
os.environ.setdefault("CLASSIFIER_AGENT_MODEL_ID", "gemini-2.0-flash")

from utils import llm_provider
from langchain_core.messages import HumanMessage

llm = llm_provider.get_llm(agent='classifier', temperature=0.1)
try:
    resp = llm.invoke([HumanMessage("Hello")])
    print("SUCCESS:", resp.content)
except Exception as e:
    print("ERROR:", e)
