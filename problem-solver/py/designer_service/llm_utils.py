"""
Utilities for working with LLM for task analysis
"""
import os
import json
import re
import logging
from typing import Optional
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2")


class LLMAnalyzer:
    """Class for task analysis using LLM"""
    
    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize LLM analyzer
        
        Args:
            model: Ollama model name (default from environment variable)
            base_url: Ollama server URL (default from environment variable)
        """
        self.model = model or OLLAMA_MODEL
        self.base_url = base_url or OLLAMA_BASE_URL
        self.llm = ChatOllama(
            model=self.model, 
            base_url=self.base_url,
            format="json"
        )
        self._setup_prompt()
    
    def _setup_prompt(self):
        system_prompt = """Ты - эксперт по машинному обучению и искусственным нейронным сетям. 
Твоя задача - проанализировать описание задачи пользователя и рекомендовать оптимальный тип модели машинного обучения.

Доступные типы моделей:
- RF (Random Forest / Случайный лес): для классификации и регрессии на табличных данных, хорошая производительность из коробки
- LR (Logistic Regression / Логистическая регрессия): для бинарной классификации, быстрая и интерпретируемая
- GRB (Gradient Boosting / Градиентный бустинг): для табличных данных с высокой точностью, требует больше времени на обучение
- NN (Neural Network / Нейронная сеть): для сложных задач (изображения, текст, последовательности), требует много данных
- SVM (Support Vector Machine): для задач с небольшими датасетами, хорош для классификации
- DT (Decision Tree / Дерево решений): простой и интерпретируемый, для небольших задач
- KNN (K-Nearest Neighbors): для задач с четкими границами классов, простая в использовании
- LinR (Linear Regression / Линейная регрессия): для задач регрессии с линейными зависимостями

Анализируй задачу по следующим критериям:
1. Тип задачи (классификация, регрессия, обработка изображений, NLP и т.д.)
2. Тип данных (табличные, изображения, текст, последовательности)
3. Размер датасета (если указан)
4. Требования к интерпретируемости
5. Требования к производительности

Верни ответ строго в формате JSON с полями:
- recommended_model: код модели (RF, LR, GRB, NN, SVM, DT, KNN, LinR)
- confidence: уверенность от 0.0 до 1.0 (число)
- reasoning: подробное обоснование выбора (на русском языке, строка)
- alternative_models: массив из 1-2 альтернативных вариантов (коды моделей, например ["RF", "GRB"])
- task_type: тип задачи (classification, regression, image_processing, nlp, etc.)
- data_type: тип данных (tabular, image, text, sequence, etc.)

Важно: ответ должен быть валидным JSON, без дополнительного текста до или после JSON.
"""

        human_prompt = """Проанализируй следующую задачу и рекомендую оптимальную модель:

Задача: {task_description}

ВАЖНО: Верни ТОЛЬКО валидный JSON объект, без дополнительного текста, объяснений или markdown разметки. 
Начни ответ сразу с открывающей фигурной скобки {{ и закончи закрывающей }}.

Пример правильного ответа:
{{"recommended_model": "NN", "confidence": 0.85, "reasoning": "Для классификации изображений рекомендуется нейронная сеть", "alternative_models": ["RF", "SVM"], "task_type": "image_classification", "data_type": "image"}}"""

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt)
        ])
    
    async def analyze_task(self, task_description: str) -> dict:
        """
        Analyzes task using LLM
        
        Args:
            task_description: User task description
            
        Returns:
            Dictionary with analysis results:
            - recommended_model: model code
            - confidence: confidence score
            - reasoning: reasoning
            - alternative_models: alternative models
            - task_type: task type
            - data_type: data type
        """
        logger.info(f"Analyzing task with LLM ({self.model}): {task_description[:100]}...")
        
        try:
            chain = self.prompt | self.llm
            
            response = await chain.ainvoke({"task_description": task_description})
            
            llm_output = response.content if hasattr(response, 'content') else str(response)
            
            try:
                result = self._extract_json_from_response(llm_output)
                logger.info(f"LLM analysis completed. Recommendation: {result.get('recommended_model', 'N/A')}")
                return result
            except ValueError as json_error:
                logger.warning(
                    f"LLM ({self.model}) returned invalid JSON. "
                    f"This is expected for some models. Fallback method will be used. "
                    f"LLM response (first 200 chars): {llm_output[:200]}..."
                )
                raise
        
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            logger.debug(f"Failed to parse LLM response: {e}. Using fallback.")
            raise
        except Exception as e:
            logger.warning(f"Error calling LLM ({self.model}): {type(e).__name__}: {str(e)}")
            raise
    
    def _extract_json_from_response(self, text: str) -> dict:
        """
        Extracts JSON from LLM text response
        
        Args:
            text: Text response from LLM
            
        Returns:
            Dictionary with analysis results
        """
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if "recommended_model" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue
        
        start_idx = text.find('{')
        if start_idx != -1:
            brace_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break
            
            if brace_count == 0 and end_idx > start_idx:
                json_str = text[start_idx:end_idx + 1]
                try:
                    parsed = json.loads(json_str)
                    if "recommended_model" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    pass
        
        pattern = r'\{[^{}]*"recommended_model"[^{}]*\}'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            json_str = max(matches, key=len)
            start = text.find(json_str)
            if start != -1:
                brace_count = 0
                end_idx = start
                for i in range(start, len(text)):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                
                if brace_count == 0:
                    json_str = text[start:end_idx + 1]
                    try:
                        parsed = json.loads(json_str)
                        if "recommended_model" in parsed:
                            return parsed
                    except json.JSONDecodeError:
                        pass
        
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, dict) and "recommended_model" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass
        
        logger.warning(f"Failed to extract JSON from LLM response. Response (first 500 chars): {text[:500]}...")
        raise ValueError(f"LLM returned invalid JSON. Failed to extract structured response.")
    
    def analyze_task_sync(self, task_description: str) -> dict:
        """
        Synchronous version of task analysis
        
        Args:
            task_description: User task description
            
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing task with LLM (sync, {self.model}): {task_description[:100]}...")
        
        try:
            chain = self.prompt | self.llm
            
            response = chain.invoke({"task_description": task_description})
            
            llm_output = response.content if hasattr(response, 'content') else str(response)
            
            try:
                result = self._extract_json_from_response(llm_output)
                logger.info(f"LLM analysis completed. Recommendation: {result.get('recommended_model', 'N/A')}")
                return result
            except ValueError as json_error:
                logger.warning(
                    f"LLM ({self.model}) returned invalid JSON. "
                    f"This is expected for some models. Fallback method will be used. "
                    f"LLM response (first 200 chars): {llm_output[:200]}..."
                )
                raise
        
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            logger.debug(f"Failed to parse LLM response: {e}. Using fallback.")
            raise
        except Exception as e:
            logger.warning(f"Error calling LLM ({self.model}): {type(e).__name__}: {str(e)}")
            raise

