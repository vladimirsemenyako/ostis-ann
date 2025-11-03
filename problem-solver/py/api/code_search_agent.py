import os
import re
import json
import requests
import concurrent.futures
from typing import Dict, List




class GroqLLM:
    
    def __init__(self, api_key: str, model="llama-3.1-8b-instant"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def ask(self, messages: list, temperature=0.2, max_tokens=800) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        resp = requests.post(self.url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text}")
        return resp.json()["choices"][0]["message"]["content"]




def search_huggingface(query: str, limit: int = 8) -> List[Dict]:
    
    url = "https://huggingface.co/api/models"
    params = {"search": query, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [{"name": m.get("id"), "link": f"https://huggingface.co/{m['id']}"} for m in data if "id" in m]
    except Exception as e:
        print("HuggingFace error:", e)
        return []


def search_github(query: str, limit: int = 8) -> List[Dict]:
    
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
        print("GitHub error:", e)
        return []




class SmartMLAgent:
    
    def __init__(self, llm: GroqLLM):
        self.llm = llm

    def decide(self, query: str) -> Dict:
        
        prompt = [
            {"role": "system", "content": (
                "Ты агент поиска ML-моделей и кода. "
                "Реши, где искать ответ: на Hugging Face (если речь о модели, задаче, инференсе, NLP, CV) "
                "или на GitHub (если о коде, библиотеке, фреймворке). "
                "Можно использовать обе платформы. "
                "Верни JSON: {\"platforms\": [\"huggingface\", \"github\"], \"refined_query\": \"...\"}"
            )},
            {"role": "user", "content": query}
        ]
        response = self.llm.ask(prompt)
        m = re.search(r"\{.*\}", response, re.S)
        try:
            return json.loads(m.group(0))
        except Exception:
            return {"platforms": ["huggingface", "github"], "refined_query": query}

    def filter_results(self, query: str, raw_results: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        
        prompt = [
            {"role": "system", "content": (
                "Ты эксперт по ML. "
                "Выбери только те ссылки, которые наиболее релевантны запросу. "
                "Верни JSON {'huggingface': [...], 'github': [...]} с максимум 5 лучшими ссылками, "
                "каждая ссылка должна содержать поля 'name' и 'link'."
            )},
            {"role": "user", "content": json.dumps({"query": query, "candidates": raw_results}, ensure_ascii=False)}
        ]
        response = self.llm.ask(prompt)
        m = re.search(r"\{.*\}", response, re.S)
        try:
            return json.loads(m.group(0))
        except Exception:
            return raw_results

    def run(self, query: str) -> Dict[str, List[Dict]]:
        decision = self.decide(query)
        refined_query = decision.get("refined_query", query)
        platforms = decision.get("platforms", ["huggingface", "github"])

        
        results = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            if "huggingface" in platforms:
                futures["huggingface"] = executor.submit(search_huggingface, refined_query)
            if "github" in platforms:
                futures["github"] = executor.submit(search_github, refined_query)
            for name, fut in futures.items():
                results[name] = fut.result()

        
        final = self.filter_results(query, results)
        return final




if __name__ == "__main__":
    GROQ_KEY = os.getenv('GROQ_API_KEY',"")
    agent = SmartMLAgent(GroqLLM(GROQ_KEY))
    user_query = input("Введите запрос: ")

    result = agent.run(user_query)
    print("\nФинальный результат:")
    print(json.dumps(result, indent=2, ensure_ascii=False))