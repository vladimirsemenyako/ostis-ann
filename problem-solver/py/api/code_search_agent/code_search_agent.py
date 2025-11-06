import os
import json
import re
import asyncio
from typing import Dict, List, Any
from dotenv import load_dotenv

import httpx
from langchain_community.chat_models import ChatOllama
from langchain_community.tools import Tool
from langgraph.graph import StateGraph, END

from hf_mcp import get_response_from_hf_mcp  
from gh_mcp import get_repos_from_github_mcp

load_dotenv()


async def search_huggingface_api(query: str, limit: int = 5) -> List[Dict[str, str]]:
    url = "https://huggingface.co/api/models"
    params = {"search": query, "limit": limit}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return [{"name": m["id"], "link": f"https://huggingface.co/{m['id']}"} for m in data if "id" in m]
        except Exception as e:
            return [{"error": str(e)}]


async def search_huggingface_mcp(query: str, limit: int = 5) -> List[Dict[str, str]]:
    try:
        links = await get_response_from_hf_mcp(query, limit)
        return [{"name": f"Result {i+1}", "link": link} for i, link in enumerate(links)]
    except Exception as e:
        return [{"error": str(e)}]


async def search_huggingface(query: str, limit: int = 5) -> List[Dict[str, str]]:
    try:
        results = await search_huggingface_mcp(query, limit)
        if not results or "error" in results[0]:
            results = await search_huggingface_api(query, limit)
    except Exception:
        results = await search_huggingface_api(query, limit)
    return results


async def search_github_api(query: str, limit: int = 5) -> List[Dict[str, str]]:
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [{"name": r["full_name"], "link": r["html_url"]} for r in items]
        except Exception as e:
            return [{"error": str(e)}]
    

async def search_github_mcp(query: str, limit: int = 5) -> List[Dict[str, str]]:
    try:
        links = await get_repos_from_github_mcp(query, limit)
        return [{"name": f"Result {i+1}", "link": link} for i, link in enumerate(links)]
    except Exception as e:
        return [{"error": str(e)}]


async def search_github(query: str, limit: int = 5) -> List[Dict[str, str]]:
    try:
        results = await search_github_mcp(query, limit)
        if not results or "error" in results[0]:
            results = await search_github_api(query, limit)
    except Exception:
        results = await search_github_api(query, limit)
    return results

llm = ChatOllama(model="llama3.1")



async def decide_platform(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state["query"]

    prompt = f"""
        Ты - интеллектуальный маршрутизатор поисковых запросов для ML-агента.

        Запрос пользователя: "{query}"

        Твоя задача - определить, где искать ответ:
        - Если запрос связан с **NLP, CV** - выбери **Hugging Face**.
        - Если запрос касается **исходного кода, реализации, фреймворка, библиотеки, репозитория, проекта, примеров кода или общее понятие например: (random forest, SVM, LinearRegression и так далее)** - выбери **GitHub**.
        - Если запрос может относиться к обоим (например, "Llama 3", "YOLO", "Whisper") - выбери **обе платформы**.

        Ответ верни строго в JSON:
        {{"platforms": ["huggingface", "github"]}}
        Если не уверен верни 
        {{"platforms": ["huggingface", "github"]}}
        Никаких пояснений, только JSON.
        """

    response = await llm.ainvoke(prompt)
    text = response.content
    match = re.search(r"\{.*\}", text, re.S)
    try:

        decision = json.loads(match.group(0))
    except Exception:
        decision = {"platforms": ["huggingface", "github"]}

    return {"platforms": decision["platforms"], "query": query}


async def perform_search(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state["query"]
    platforms = state["platforms"]

    results = {}
    tasks = []
    for p in platforms:
        if p == "huggingface":
            tasks.append(search_huggingface(query))
        elif p == "github":
            tasks.append(search_github(query))

    
    search_results = await asyncio.gather(*tasks, return_exceptions=True)

    for p, result in zip(platforms, search_results):
        results[p] = result
    return {"query": query, "platforms": platforms, "results": results}


async def select_best_result(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state["query"]
    results = state["results"]
    prompt = f"""
    Ты эксперт по ML. Пользователь ищет: "{query}"
    Вот результаты поиска:
    {json.dumps(results, ensure_ascii=False)}

    Выбери один наиболее релевантный результат, он должен как можно точнее соответствовать запросу пользователя, и верни JSON:
    {{
      "link": "..."
    }}
    """
    response = await llm.ainvoke(prompt)
    text = response.content
    match = re.search(r"https://[^\s,\"]+", text)
    try:
        best = match.group(0)
    except Exception:
        best = None

    other_links = []
    for key in results:
        array = results[key]
        for pair in array:
            if pair['link'] != best:
                other_links.append(pair['link'])

    return {"best_link": best, 'other_links': other_links}



graph = StateGraph(dict)
graph.add_node("decide_platform", decide_platform)
graph.add_node("perform_search", perform_search)
graph.add_node("select_best_result", select_best_result)

graph.add_edge("decide_platform", "perform_search")
graph.add_edge("perform_search", "select_best_result")
graph.add_edge("select_best_result", END)
graph.set_entry_point("decide_platform")

agent_graph = graph.compile()



async def run_agent(user_query: str) -> Dict[str, Any]:
    result = await agent_graph.ainvoke({"query": user_query})
    return result