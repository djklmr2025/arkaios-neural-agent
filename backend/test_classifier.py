import sys
from utils.llm_provider import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from utils import ai_prompts

llm = get_llm('classifier', temperature=0.1)
prompt = ChatPromptTemplate.from_messages([
    ('system', ai_prompts.CLASSIFIER_AGENT_PROMPT),
    HumanMessage('Previous Tasks (Limited to 10): \n []'),
    ('user', 'hello'),
])
chain = prompt | llm
print(chain.invoke({}))
