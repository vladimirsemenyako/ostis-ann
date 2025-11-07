from pydantic import BaseModel
from typing import Optional,Dict
class StartRequest(BaseModel):
    query: str

class ContinueRequest(BaseModel):
    session_id: str
    user_response: str

class AgentResponse(BaseModel):
    status: str
    message: Optional[str] = None
    collected_data: Optional[Dict[str, str]] = None