"""
Code search service - searches for ML models on HuggingFace and GitHub
"""
import os
import re
import json
import asyncio
import logging
from typing import List, Dict, Optional
import httpx
from models import SearchResult, ModelRecommendation
from utils.llm import get_llm_manager
from utils.exceptions import CodeSearchException

logger = logging.getLogger(__name__)


class CodeSearchService:
    """Service for searching ML models and code on HuggingFace and GitHub"""
    
    def __init__(self):
        self.llm_manager = get_llm_manager()
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.hf_token = os.getenv("HF_TOKEN")
        logger.info("CodeSearchService initialized")
    
    async def search_for_model(
        self,
        recommendation: ModelRecommendation,
        task_description: str
    ) -> Dict[str, any]:
        """
        Search for model implementation based on recommendation
        
        Args:
            recommendation: Model recommendation from designer
            task_description: Original task description
            
        Returns:
            Dict with best_link and other_links
        """
        logger.info(f"Searching for {recommendation.recommended_model.value} implementation")
        
        try:
            # Construct search query
            query = self._build_search_query(recommendation, task_description)
            
            # Decide which platforms to search
            platforms = await self._decide_platforms(query, recommendation)
            
            # Perform searches
            results = await self._perform_searches(query, platforms)
            
            # Select best result
            best_result = await self._select_best_result(query, results)
            
            return best_result
            
        except Exception as e:
            logger.error(f"Error in code search: {e}", exc_info=True)
            raise CodeSearchException(f"Failed to search for model: {str(e)}")
    
    def _build_search_query(
        self,
        recommendation: ModelRecommendation,
        task_description: str
    ) -> str:
        """Build search query from recommendation and task"""
        
        model_names = {
            "RF": "Random Forest",
            "LR": "Logistic Regression",
            "GRB": "Gradient Boosting",
            "NN": "Neural Network",
            "SVM": "SVM",
            "DT": "Decision Tree",
            "KNN": "KNN",
            "LinR": "Linear Regression"
        }
        
        model_name = model_names.get(recommendation.recommended_model.value, "Machine Learning")
        
        # Extract key terms from task description
        query_parts = [model_name]
        
        # Add task-specific terms
        if "image" in task_description.lower() or "изображ" in task_description.lower():
            query_parts.append("image classification")
        elif "text" in task_description.lower() or "текст" in task_description.lower():
            query_parts.append("text classification")
        else:
            query_parts.append("classification")
        
        query = " ".join(query_parts)
        logger.debug(f"Built search query: {query}")
        
        return query
    
    async def _decide_platforms(
        self,
        query: str,
        recommendation: ModelRecommendation
    ) -> List[str]:
        """Decide which platforms to search"""
        
        prompt = f"""
Ты - интеллектуальный маршрутизатор поисковых запросов для ML-агента.

Запрос: "{query}"
Модель: {recommendation.recommended_model.value}

Определи, где искать:
- Если запрос связан с готовыми моделями NLP, CV, предобученными моделями - выбери **Hugging Face**
- Если запрос касается исходного кода, реализации, фреймворков, библиотек - выбери **GitHub**
- Если неясно - выбери **обе платформы**

Ответ верни строго в JSON:
{{"platforms": ["huggingface", "github"]}}

Никаких пояснений, только JSON.
"""
        
        try:
            response = await self.llm_manager.ainvoke_with_prompt(
                "Ты - эксперт по маршрутизации поисковых запросов.",
                prompt,
                temperature=0.3,
                format="json"
            )
            
            # Parse response
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                decision = json.loads(match.group())
                platforms = decision.get("platforms", ["huggingface", "github"])
            else:
                platforms = ["huggingface", "github"]
            
            logger.info(f"Searching on platforms: {platforms}")
            return platforms
            
        except Exception as e:
            logger.warning(f"Error deciding platforms: {e}. Using both.")
            return ["huggingface", "github"]
    
    async def _perform_searches(
        self,
        query: str,
        platforms: List[str]
    ) -> Dict[str, List[SearchResult]]:
        """Perform searches on selected platforms"""
        
        results = {}
        tasks = []
        
        for platform in platforms:
            if platform == "huggingface":
                tasks.append(self._search_huggingface(query))
            elif platform == "github":
                tasks.append(self._search_github(query))
        
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for platform, result in zip(platforms, search_results):
            if isinstance(result, Exception):
                logger.error(f"Error searching {platform}: {result}")
                results[platform] = []
            else:
                results[platform] = result
        
        return results
    
    async def _search_huggingface(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Search HuggingFace models"""
        
        url = "https://huggingface.co/api/models"
        params = {"search": query, "limit": limit}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = [
                    SearchResult(
                        name=m["id"],
                        link=f"https://huggingface.co/{m['id']}"
                    )
                    for m in data if "id" in m
                ]
                
                logger.info(f"Found {len(results)} results on HuggingFace")
                return results
                
            except Exception as e:
                logger.error(f"Error searching HuggingFace: {e}")
                return []
    
    async def _search_github(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Search GitHub repositories"""
        
        url = "https://api.github.com/search/repositories"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": limit
        }
        
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                items = response.json().get("items", [])
                
                results = [
                    SearchResult(
                        name=repo["full_name"],
                        link=repo["html_url"]
                    )
                    for repo in items
                ]
                
                logger.info(f"Found {len(results)} results on GitHub")
                return results
                
            except Exception as e:
                logger.error(f"Error searching GitHub: {e}")
                return []
    
    async def _select_best_result(
        self,
        query: str,
        results: Dict[str, List[SearchResult]]
    ) -> Dict[str, any]:
        """Select best result from search results using LLM"""
        
        prompt = f"""
Ты эксперт по ML. Пользователь ищет: "{query}"

Вот результаты поиска:
{json.dumps({k: [{"name": r.name, "link": r.link} for r in v] for k, v in results.items()}, ensure_ascii=False, indent=2)}

Выбери один наиболее релевантный результат. Он должен как можно точнее соответствовать запросу.

Верни JSON:
{{
  "link": "ссылка на лучший результат"
}}
"""
        
        try:
            response = await self.llm_manager.ainvoke_with_prompt(
                "Ты - эксперт по выбору ML решений.",
                prompt,
                temperature=0.3
            )
            
            # Extract URL from response
            match = re.search(r'https://[^\s,\"]+', response)
            if match:
                best_link = match.group(0)
            else:
                best_link = None
            
            # Collect other links
            other_links = []
            for platform_results in results.values():
                for result in platform_results:
                    if result.link != best_link:
                        other_links.append(result.link)
            
            logger.info(f"Selected best link: {best_link}")
            
            return {
                "best_link": best_link,
                "other_links": other_links[:5]  # Limit to 5 alternatives
            }
            
        except Exception as e:
            logger.error(f"Error selecting best result: {e}")
            
            # Fallback: return first available link
            for platform_results in results.values():
                if platform_results:
                    best_link = platform_results[0].link
                    other_links = [r.link for r in platform_results[1:]]
                    return {
                        "best_link": best_link,
                        "other_links": other_links[:5]
                    }
            
            return {
                "best_link": None,
                "other_links": []
            }

