"""
Task classifier service - determines if query is informational or build_model
"""
import logging
from langchain_core.messages import HumanMessage
from models import TaskCategory
from utils.llm import get_llm_manager
from utils.exceptions import ClassificationException

logger = logging.getLogger(__name__)


class TaskClassifier:
    """Classifies user queries into task categories"""
    
    def __init__(self):
        self.llm_manager = get_llm_manager()
        logger.info("TaskClassifier initialized")
    
    async def classify(self, query: str) -> TaskCategory:
        """
        Classify user query into task category
        
        Args:
            query: User query
            
        Returns:
            TaskCategory enum value
        """
        logger.info(f"Classifying query: {query[:100]}...")
        
        prompt = f"""
Ты — интеллектуальный маршрутизатор задач в области машинного обучения и ИИ.

Определи, что пользователь хочет сделать:
1. Если вопрос — просто узнать что-то про ИИ, машинное обучение, нейросети, технологии, принципы работы моделей (новости, объяснения, концепции и т.п.), верни: 'informational'
2. Если это задача по созданию ИИ-модели, нейросети (например, "сделай модель", "создай нейросеть", "построй классификатор", "обучи модель" и т.п.), верни: 'build_model'
3. Если не уверен, верни: 'unclear'

Ответь строго ОДНИМ словом: 'informational', 'build_model', или 'unclear'. 
Никаких пояснений, только одно слово.

Сообщение пользователя:
{query}
"""
        
        try:
            response = await self.llm_manager.ainvoke(
                [HumanMessage(content=prompt)],
                temperature=0.3
            )
            
            # Extract category from response
            category_str = response.strip().lower()
            
            # Parse response
            if 'informational' in category_str:
                category = TaskCategory.INFORMATIONAL
            elif 'build_model' in category_str or 'build' in category_str:
                category = TaskCategory.BUILD_MODEL
            else:
                category = TaskCategory.UNCLEAR
            
            logger.info(f"Classified query as: {category.value}")
            return category
            
        except Exception as e:
            logger.error(f"Error classifying query: {e}", exc_info=True)
            raise ClassificationException(f"Failed to classify query: {str(e)}")
    
    def classify_sync(self, query: str) -> TaskCategory:
        """
        Synchronous version of classify
        
        Args:
            query: User query
            
        Returns:
            TaskCategory enum value
        """
        logger.info(f"Classifying query (sync): {query[:100]}...")
        
        prompt = f"""
Ты — интеллектуальный маршрутизатор задач в области машинного обучения и ИИ.

Определи, что пользователь хочет сделать:
1. Если вопрос — просто узнать что-то про ИИ, машинное обучение, нейросети, технологии, принципы работы моделей (новости, объяснения, концепции и т.п.), верни: 'informational'
2. Если это задача по созданию ИИ-модели, нейросети (например, "сделай модель", "создай нейросеть", "построй классификатор", "обучи модель" и т.п.), верни: 'build_model'
3. Если не уверен, верни: 'unclear'

Ответь строго ОДНИМ словом: 'informational', 'build_model', или 'unclear'. 
Никаких пояснений, только одно слово.

Сообщение пользователя:
{query}
"""
        
        try:
            response = self.llm_manager.invoke(
                [HumanMessage(content=prompt)],
                temperature=0.3
            )
            
            # Extract category from response
            category_str = response.strip().lower()
            
            # Parse response
            if 'informational' in category_str:
                category = TaskCategory.INFORMATIONAL
            elif 'build_model' in category_str or 'build' in category_str:
                category = TaskCategory.BUILD_MODEL
            else:
                category = TaskCategory.UNCLEAR
            
            logger.info(f"Classified query as: {category.value}")
            return category
            
        except Exception as e:
            logger.error(f"Error classifying query: {e}", exc_info=True)
            raise ClassificationException(f"Failed to classify query: {str(e)}")

