from fastapi import FastAPI, HTTPException
from models import StartRequest, AgentResponse, ContinueRequest
from models import AgentResponse
from agent_state import AgentState
from langchain.messages import HumanMessage
from typing import Dict
from interface_agent import classify_decision, classify_task_node, llm_node, gather_data
app = FastAPI()

sessions: Dict[str, AgentState] = {}

@app.post("/start", response_model=AgentResponse)
def start_agent(request: StartRequest):
    session_id = str(len(sessions) + 1)
    initial_state = AgentState(messages=[HumanMessage(content=request.query)], collected_data={})
    sessions[session_id] = initial_state
    
    result = run_graph(session_id, is_continue=False)
    
    return result

@app.post("/continue", response_model=AgentResponse)
def continue_agent(request: ContinueRequest):
    session_id = request.session_id
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = sessions[session_id]
    if state.get("category") != "build_model":
        raise HTTPException(status_code=400, detail="Session not in build_model mode")
    
    state["messages"].append(HumanMessage(content=request.user_response))
    
    result = run_graph(session_id, is_continue=True)
    
    return result

def run_graph(session_id: str, is_continue: bool) -> AgentResponse:
    state = sessions[session_id]
    
    try:
        if not is_continue:
            updates = classify_task_node(state)
            state.update(updates)
            
            next_path = classify_decision(state)
            
            if next_path == "llm":
                updates = llm_node(state)
                state.update(updates)
                return AgentResponse(status="complete", message=state["messages"][-1].content)
            elif next_path == "gather_data":
                pass 

        updates = gather_data(state)
        state.update(updates)
        
        last_msg = state["messages"][-1].content
        
        if "Все данные собраны!" in last_msg:
            return AgentResponse(status="complete", message=last_msg, collected_data=state["collected_data"])
        else:
            return AgentResponse(status="question", message=last_msg)
    
    except Exception as e:
        return AgentResponse(status="error", message=str(e))