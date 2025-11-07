from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.chat_models import ChatOllama
from agent_state import AgentState
import json
import re
llm = ChatOllama(model="gemma3:27b")
def llm_node(state: AgentState):
    print("LLM")
    query = state["original_query"]
    prompt = f'''Ты - специалист в области машинного обучения и ИИ. 
    Ответь развернуто на вопрос пользователя, только если он связан с темой машинного обучения. 
    При любых вопросах на другие темы откажись отвечать, т.к ты не специалист в остальных вопросах
    Вопрос пользователя:{query}'''
    print(prompt)
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"messages": [response]}

def classify_task_node(state: AgentState):
    print("Классификатор")
    last_msg = state["messages"][-1].content.strip().lower()
    original_query = last_msg
    prompt = f"""
    Ты — интеллектуальный маршрутизатор задач.
    Определи, что пользователь хочет сделать:
    1. Если вопрос — просто узнать что-то про ИИ (новости, технологии, принципы), верни: 'informational'
    2. Если это задача по созданию ИИ-модели (например, "сделай модель", "создай нейросеть", "построй классификатор" и т.п.), верни: 'build_model'
    3. Если не уверен, верни: 'unclear'
    Ответь строго ОДНИМ словом: 'informational',  'build_model', 'unclear'. Без лишнего текста
    Сообщение пользователя:
    {last_msg}
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    category = response.content.strip().lower()
    return {"category": category, "original_query": original_query, "messages": [AIMessage(content=f"{category}")]}

def classify_decision(state: AgentState):
    print("Классификатор результат")
    category = state["messages"][-1].content
    print(category)
    if category == 'build_model':
        return "gather_data"
    else:
        return "llm"    

def gather_data(state: AgentState):
    print("Сбор данных")
    messages = state["messages"]
    collected = state.get("collected_data", {})
    system_content = '''
    Ты собираешь данные для построения ML модели. Тебе нужно собрать 4 пункта:
    1. data - данные для обучения
    2. features - признаки модели  
    3. output - целевая переменная
    4. metric_goal - метрика качества
    
    Уже собрано: {collected}
    
    ПРАВИЛА:
    - Отвечай ТОЛЬКО в формате JSON, без лишнего текста
    - Если пользователь предоставил информацию - добавь ее в collected_data
    - Если какой-то пункт отсутствует - запроси ТОЛЬКО его
    - Значения не могут быть "...", "None" или пустыми
    Формат ответа ДОЛЖЕН БЫТЬ JSON:
    {{
        "collected_data": {{"data": "...", "features": "...", "output": "...", "metric_goal": "..."}},
        "next_question": "текст вопроса ИЛИ 'complete' если все собрано"
    }}
    Запрашивай ТОЛЬКО поля на русском языке, что нужны для collected_data сам НИЧЕГО не добавляй лишнего.
    '''
    
    system_msg = SystemMessage(content=system_content.format(collected=collected))
    response = llm.invoke([system_msg] + messages)
    
    content = response.content.strip()
    print(f"Ответ LLM: {content}")
    
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            collected_data = parsed.get("collected_data", {})
            next_question = parsed.get("next_question", "")

            updated_collected = {**collected, **{k: v for k, v in collected_data.items() if v and v != "..." and v != "None"}}

            result = {"collected_data": updated_collected}
            
            if next_question and next_question != "complete":
                result["messages"] = [AIMessage(content=next_question)]
            else:
                result["messages"] = [AIMessage(content="Все данные собраны!")]
                
            return result
            
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            return {"messages": [AIMessage(content="Ошибка обработки данных.")]}
    
    return {"messages": [AIMessage(content="Ошибка обработки данных.")]}
