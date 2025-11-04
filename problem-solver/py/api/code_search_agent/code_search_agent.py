import os
import json
import re
import requests
from typing import Dict, List, Any

from langchain_community.chat_models import ChatOllama
from langchain_community.tools import Tool
from langgraph.graph import StateGraph, END




def search_huggingface(query: str, limit: int = 5) -> List[Dict[str, str]]:
    """Поиск моделей на Hugging Face"""
    url = "https://huggingface.co/api/models"
    params = {"search": query, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [{"name": m["id"], "link": f"https://huggingface.co/{m['id']}"} for m in data if "id" in m]
    except Exception as e:
        return [{"error": str(e)}]


def search_github(query: str, limit: int = 5) -> List[Dict[str, str]]:
    """Поиск репозиториев на GitHub"""
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [{"name": r["full_name"], "link": r["html_url"]} for r in items]
    except Exception as e:
        return [{"error": str(e)}]




llm = ChatOllama(model="llama3.1")

tools = {
    "huggingface": Tool(
        name="HuggingFaceSearch",
        func=lambda q: json.dumps(search_huggingface(q)),
        description="Поиск ML моделей на Hugging Face по названию или задаче"
    ),
    "github": Tool(
        name="GitHubSearch",
        func=lambda q: json.dumps(search_github(q)),
        description="Поиск кода и ML проектов на GitHub"
    ),
}




def decide_platform(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state["query"]

    prompt = f"""
    Пользователь ввёл запрос: "{query}"
    Определи, где лучше искать результат:
    - Если это модель, архитектура, инференс или NLP, или уточнённая задача — выбирай Hugging Face.
    - Если это код, библиотека, проект, фреймворк или общее понятие — выбирай GitHub.
    - Если сомневаешься — выбери обе платформы.

    Ответ верни строго в формате JSON:
    {{"platforms": ["huggingface", "github"]}}
    """

    response = llm.invoke(prompt)
    text = response.content if hasattr(response, "content") else str(response)
    match = re.search(r"\{.*\}", text, re.S)

    try:
        decision = json.loads(match.group(0))
    except Exception:
        decision = {"platforms": ["huggingface", "github"]}

    return {"platforms": decision["platforms"], "query": query}


def perform_search(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state["query"]
    platforms = state["platforms"]

    results = {}
    for p in platforms:
        if p == "huggingface":
            results[p] = search_huggingface(query)
        elif p == "github":
            results[p] = search_github(query)

    return {"query": query, "platforms": platforms, "results": results}


def select_best_result(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state["query"]
    results = state["results"]

    prompt = f"""
    Ты эксперт по ML. Пользователь ищет: "{query}"
    Вот результаты поиска:
    {json.dumps(results, ensure_ascii=False)}

    Выбери один наиболее релевантный результат и верни JSON:
    {{
      "platform": "huggingface" или "github",
      "name": "...",
      "link": "..."
    }}
    """

    response = llm.invoke(prompt)
    text = response.content if hasattr(response, "content") else str(response)
    match = re.search(r"\{.*\}", text, re.S)

    try:
        best = json.loads(match.group(0))
    except Exception:
        best = {"platform": "unknown", "link": ""}

    return {"final_result": best}




graph = StateGraph(dict)
graph.add_node("decide_platform", decide_platform)
graph.add_node("perform_search", perform_search)
graph.add_node("select_best_result", select_best_result)
graph.add_edge("decide_platform", "perform_search")
graph.add_edge("perform_search", "select_best_result")
graph.add_edge("select_best_result", END)
graph.set_entry_point("decide_platform")
agent_graph = graph.compile()




def run_agent(user_query: str) -> Dict[str, Any]:
    result = agent_graph.invoke({"query": user_query})
    return result["final_result"]
