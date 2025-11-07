from langgraph.graph.message import MessagesState
from typing import Optional, Dict
class AgentState(MessagesState):
    category: Optional[str] = None
    original_query: Optional[str] = None
    collected_data: Optional[Dict[str, str]] = None