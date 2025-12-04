"""
Designer service - determines optimal ML model type
"""
import json
import re
import logging
from typing import Dict, List
from models import ModelType, ModelRecommendation
from utils.llm import get_llm_manager
from utils.exceptions import DesignerException

logger = logging.getLogger(__name__)


class DesignerService:
    """Service for determining optimal ML model type"""
    
    # Keyword-based fallback patterns
    KEYWORDS = {
        ModelType.RANDOM_FOREST: [
            "random forest", "случайный лес", "rf", "дерево решений", "ensemble",
            "classification", "классификация", "tabular", "табличные данные"
        ],
        ModelType.LOGISTIC_REGRESSION: [
            "logistic regression", "логистическая регрессия", "lr", "binary",
            "бинарная", "probability", "вероятность"
        ],
        ModelType.GRADIENT_BOOSTING: [
            "gradient boosting", "градиентный бустинг", "grb", "xgboost", "lightgbm",
            "catboost", "ensemble", "ансамбль"
        ],
        ModelType.NEURAL_NETWORK: [
            "neural network", "нейронная сеть", "nn", "deep learning", "глубокое обучение",
            "image", "изображение", "nlp", "text", "текст", "cnn", "rnn", "lstm", "transformer"
        ],
        ModelType.SVM: [
            "svm", "support vector machine", "машина опорных векторов"
        ],
        ModelType.DECISION_TREE: [
            "decision tree", "дерево решений", "dt", "interpretable", "интерпретируемый"
        ],
        ModelType.KNN: [
            "knn", "k-nearest neighbors", "k ближайших соседей"
        ],
        ModelType.LINEAR_REGRESSION: [
            "linear regression", "линейная регрессия", "regression", "регрессия"
        ]
    }
    
    def __init__(self):
        self.llm_manager = get_llm_manager()
        self._compile_patterns()
        logger.info("DesignerService initialized")
    
    def _compile_patterns(self):
        """Compile regex patterns for keyword matching"""
        self.patterns = {}
        for model_type, keywords in self.KEYWORDS.items():
            pattern = re.compile(
                r'\b(?:' + '|'.join(re.escape(kw) for kw in keywords) + r')\b',
                re.IGNORECASE
            )
            self.patterns[model_type] = pattern
    
    async def analyze_task(self, task_description: str) -> ModelRecommendation:
        """
        Analyze task and recommend optimal model
        
        Args:
            task_description: Task description from user
            
        Returns:
            ModelRecommendation
        """
        logger.info(f"Analyzing task: {task_description[:100]}...")
        
        try:
            # Try LLM-based analysis first
            result = await self._llm_analyze(task_description)
            return result
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}. Using keyword fallback.")
            # Fallback to keyword-based analysis
            return self._keyword_analyze(task_description)
    
    async def _llm_analyze(self, task_description: str) -> ModelRecommendation:
        """Analyze task using LLM"""
        
        system_prompt = """Ты - эксперт по машинному обучению. 
Проанализируй описание задачи и определи:
1. Тип задачи: РЕГРЕССИЯ (предсказание числового значения) или КЛАССИФИКАЦИЯ (предсказание категории)
2. Оптимальный тип модели

ВАЖНО: 
- Для РЕГРЕССИИ (стоимость, цена, количество, прогноз) используй: LinR, GRB, RF
- Для КЛАССИФИКАЦИИ (категория, класс, да/нет) используй: RF, LR, GRB, NN

Доступные типы моделей:
- RF (Random Forest): универсальный, для табличных данных (классификация и регрессия)
- LR (Logistic Regression): для бинарной классификации
- GRB (Gradient Boosting): для табличных данных с высокой точностью (классификация и регрессия)
- NN (Neural Network): для изображений, текста, сложных нелинейных задач
- SVM (Support Vector Machine): для небольших датасетов, классификация
- DT (Decision Tree): простой и интерпретируемый
- KNN (K-Nearest Neighbors): для задач с четкими границами
- LinR (Linear Regression): для линейной регрессии (предсказание чисел)

Верни ответ строго в JSON:
{
  "task_type": "РЕГРЕССИЯ" или "КЛАССИФИКАЦИЯ",
  "recommended_model": "код модели (RF/LR/GRB/NN/SVM/DT/KNN/LinR)",
  "confidence": 0.75,
  "reasoning": "краткое обоснование на русском",
  "alternative_models": ["альт1", "альт2"]
}
"""
        
        user_prompt = f"Задача: {task_description}"
        
        try:
            response = await self.llm_manager.ainvoke_with_prompt(
                system_prompt,
                user_prompt,
                temperature=0.5,
                format="json"
            )
            
            # Parse JSON
            result = self._parse_llm_response(response)
            
            # Determine task type and validate model choice
            task_type = result.get("task_type", "").upper()
            recommended_code = result.get("recommended_model", "NN").upper()
            
            # Validate and correct model choice based on task type
            if "РЕГРЕССИЯ" in task_type or "REGRESSION" in task_type:
                # For regression, prefer: LinR, GRB, RF
                regression_models = ["LinR", "GRB", "RF", "NN"]
                if recommended_code not in regression_models:
                    # Auto-correct to appropriate regression model
                    if "стоимость" in task_description.lower() or "цена" in task_description.lower() or "cost" in task_description.lower():
                        recommended_code = "LinR"  # Linear regression for price prediction
                    else:
                        recommended_code = "GRB"  # Gradient boosting for general regression
                    logger.info(f"Auto-corrected to regression model: {recommended_code}")
            elif "КЛАССИФИКАЦИЯ" in task_type or "CLASSIFICATION" in task_type:
                # For classification, prefer: RF, LR, GRB, NN
                classification_models = ["RF", "LR", "GRB", "NN", "SVM", "DT", "KNN"]
                if recommended_code not in classification_models:
                    recommended_code = "RF"  # Default to Random Forest for classification
                    logger.info(f"Auto-corrected to classification model: {recommended_code}")
            else:
                # Try to infer from description
                desc_lower = task_description.lower()
                if any(word in desc_lower for word in ["стоимость", "цена", "cost", "price", "прогноз", "forecast", "регрессия", "regression"]):
                    if recommended_code not in ["LinR", "GRB", "RF", "NN"]:
                        recommended_code = "GRB"
                elif any(word in desc_lower for word in ["класс", "категория", "class", "category", "классификация", "classification"]):
                    if recommended_code not in ["RF", "LR", "GRB", "NN", "SVM"]:
                        recommended_code = "RF"
            
            try:
                recommended_model = ModelType(recommended_code)
            except ValueError:
                logger.warning(f"Invalid model code '{recommended_code}', falling back to GRB")
                recommended_model = ModelType.GRADIENT_BOOSTING
            
            confidence = float(result.get("confidence", 0.5))
            confidence = max(0.3, min(0.95, confidence))
            reasoning = result.get("reasoning", "Рекомендация на основе анализа задачи")
            if task_type:
                reasoning = f"[{task_type}] {reasoning}"
            
            alt_models_raw = result.get("alternative_models", [])
            alternative_models = []
            for alt in alt_models_raw[:2]:
                try:
                    alt_code = str(alt).upper()
                    # Normalize alternative models too
                    paren_match = re.search(r'\(([A-Z]+)\)', alt_code)
                    if paren_match:
                        alt_code = paren_match.group(1)
                    alternative_models.append(ModelType(alt_code))
                except (ValueError, AttributeError):
                    pass
            
            logger.info(f"LLM recommendation: {recommended_model.value} (task: {task_type}), confidence: {confidence:.2f}")
            
            return ModelRecommendation(
                recommended_model=recommended_model,
                confidence=confidence,
                reasoning=reasoning,
                alternative_models=alternative_models if alternative_models else None
            )
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            raise DesignerException(f"LLM analysis failed: {str(e)}")
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response to extract JSON"""
        
        # Try to find JSON in response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                # Normalize model code - handle cases like "Random Forest (RF)" -> "RF"
                if "recommended_model" in parsed:
                    model_str = str(parsed["recommended_model"]).upper()
                    # Extract code from parentheses if present
                    paren_match = re.search(r'\(([A-Z]+)\)', model_str)
                    if paren_match:
                        parsed["recommended_model"] = paren_match.group(1)
                    else:
                        # Map common names to codes
                        model_mapping = {
                            "RANDOM FOREST": "RF",
                            "LOGISTIC REGRESSION": "LR",
                            "GRADIENT BOOSTING": "GRB",
                            "NEURAL NETWORK": "NN",
                            "SUPPORT VECTOR MACHINE": "SVM",
                            "DECISION TREE": "DT",
                            "K-NEAREST NEIGHBORS": "KNN",
                            "LINEAR REGRESSION": "LinR"
                        }
                        for name, code in model_mapping.items():
                            if name in model_str:
                                parsed["recommended_model"] = code
                                break
                return parsed
            except json.JSONDecodeError:
                pass
        
        # If no valid JSON, raise exception
        raise ValueError("Failed to parse JSON from LLM response")
    
    def _keyword_analyze(self, task_description: str) -> ModelRecommendation:
        """Fallback: keyword-based analysis"""
        
        logger.info("Using keyword-based analysis")
        normalized_text = task_description.lower()
        
        scores: Dict[ModelType, float] = {}
        matches: Dict[ModelType, List[str]] = {}
        
        for model_type, pattern in self.patterns.items():
            found_matches = pattern.findall(normalized_text)
            if found_matches:
                unique_matches = list(set(found_matches))
                scores[model_type] = len(unique_matches)
                matches[model_type] = unique_matches
        
        if not scores:
            # Default to Neural Network
            return ModelRecommendation(
                recommended_model=ModelType.NEURAL_NETWORK,
                confidence=0.35,
                reasoning="Нейронная сеть рекомендуется как универсальное решение (низкая уверенность)",
                alternative_models=None
            )
        
        # Get top recommendation
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        recommended_model = sorted_scores[0][0]
        max_score = scores[recommended_model]
        
        # Calculate confidence based on scores
        confidence = min(0.6 + (max_score * 0.1), 0.9)
        
        # Generate reasoning
        reasoning = f"Рекомендуется {recommended_model.value}. Найдены ключевые слова: {', '.join(matches[recommended_model][:3])}"
        
        # Get alternatives
        alternative_models = [model for model, score in sorted_scores[1:3]]
        
        logger.info(f"Keyword recommendation: {recommended_model.value}, confidence: {confidence:.2f}")
        
        return ModelRecommendation(
            recommended_model=recommended_model,
            confidence=confidence,
            reasoning=reasoning,
            alternative_models=alternative_models if alternative_models else None
        )
    
    def analyze_task_sync(self, task_description: str) -> ModelRecommendation:
        """Synchronous version of analyze_task"""
        
        logger.info(f"Analyzing task (sync): {task_description[:100]}...")
        
        try:
            # Try LLM-based analysis first
            result = self._llm_analyze_sync(task_description)
            return result
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}. Using keyword fallback.")
            # Fallback to keyword-based analysis
            return self._keyword_analyze(task_description)
    
    def _llm_analyze_sync(self, task_description: str) -> ModelRecommendation:
        """Synchronous LLM analysis"""
        
        system_prompt = """Ты - эксперт по машинному обучению. 
Проанализируй описание задачи и определи:
1. Тип задачи: РЕГРЕССИЯ (предсказание числового значения) или КЛАССИФИКАЦИЯ (предсказание категории)
2. Оптимальный тип модели

ВАЖНО: 
- Для РЕГРЕССИИ (стоимость, цена, количество, прогноз) используй: LinR, GRB, RF
- Для КЛАССИФИКАЦИИ (категория, класс, да/нет) используй: RF, LR, GRB, NN

Доступные типы моделей:
- RF (Random Forest): универсальный, для табличных данных (классификация и регрессия)
- LR (Logistic Regression): для бинарной классификации
- GRB (Gradient Boosting): для табличных данных с высокой точностью (классификация и регрессия)
- NN (Neural Network): для изображений, текста, сложных нелинейных задач
- SVM (Support Vector Machine): для небольших датасетов, классификация
- DT (Decision Tree): простой и интерпретируемый
- KNN (K-Nearest Neighbors): для задач с четкими границами
- LinR (Linear Regression): для линейной регрессии (предсказание чисел)

Верни ответ строго в JSON:
{
  "task_type": "РЕГРЕССИЯ" или "КЛАССИФИКАЦИЯ",
  "recommended_model": "код модели (RF/LR/GRB/NN/SVM/DT/KNN/LinR)",
  "confidence": 0.75,
  "reasoning": "краткое обоснование на русском",
  "alternative_models": ["альт1", "альт2"]
}
"""
        
        user_prompt = f"Задача: {task_description}"
        
        try:
            response = self.llm_manager.invoke_with_prompt(
                system_prompt,
                user_prompt,
                temperature=0.5,
                format="json"
            )
            
            # Parse JSON
            result = self._parse_llm_response(response)
            
            # Determine task type and validate model choice
            task_type = result.get("task_type", "").upper()
            recommended_code = result.get("recommended_model", "NN").upper()
            
            # Validate and correct model choice based on task type
            if "РЕГРЕССИЯ" in task_type or "REGRESSION" in task_type:
                # For regression, prefer: LinR, GRB, RF
                regression_models = ["LinR", "GRB", "RF", "NN"]
                if recommended_code not in regression_models:
                    # Auto-correct to appropriate regression model
                    if "стоимость" in task_description.lower() or "цена" in task_description.lower() or "cost" in task_description.lower():
                        recommended_code = "LinR"  # Linear regression for price prediction
                    else:
                        recommended_code = "GRB"  # Gradient boosting for general regression
                    logger.info(f"Auto-corrected to regression model: {recommended_code}")
            elif "КЛАССИФИКАЦИЯ" in task_type or "CLASSIFICATION" in task_type:
                # For classification, prefer: RF, LR, GRB, NN
                classification_models = ["RF", "LR", "GRB", "NN", "SVM", "DT", "KNN"]
                if recommended_code not in classification_models:
                    recommended_code = "RF"  # Default to Random Forest for classification
                    logger.info(f"Auto-corrected to classification model: {recommended_code}")
            else:
                # Try to infer from description
                desc_lower = task_description.lower()
                if any(word in desc_lower for word in ["стоимость", "цена", "cost", "price", "прогноз", "forecast", "регрессия", "regression"]):
                    if recommended_code not in ["LinR", "GRB", "RF", "NN"]:
                        recommended_code = "GRB"
                elif any(word in desc_lower for word in ["класс", "категория", "class", "category", "классификация", "classification"]):
                    if recommended_code not in ["RF", "LR", "GRB", "NN", "SVM"]:
                        recommended_code = "RF"
            
            try:
                recommended_model = ModelType(recommended_code)
            except ValueError:
                logger.warning(f"Invalid model code '{recommended_code}', falling back to GRB")
                recommended_model = ModelType.GRADIENT_BOOSTING
            
            confidence = float(result.get("confidence", 0.5))
            confidence = max(0.3, min(0.95, confidence))
            reasoning = result.get("reasoning", "Рекомендация на основе анализа задачи")
            if task_type:
                reasoning = f"[{task_type}] {reasoning}"
            
            alt_models_raw = result.get("alternative_models", [])
            alternative_models = []
            for alt in alt_models_raw[:2]:
                try:
                    alt_code = str(alt).upper()
                    # Normalize alternative models too
                    paren_match = re.search(r'\(([A-Z]+)\)', alt_code)
                    if paren_match:
                        alt_code = paren_match.group(1)
                    alternative_models.append(ModelType(alt_code))
                except (ValueError, AttributeError):
                    pass
            
            logger.info(f"LLM recommendation: {recommended_model.value} (task: {task_type}), confidence: {confidence:.2f}")
            
            return ModelRecommendation(
                recommended_model=recommended_model,
                confidence=confidence,
                reasoning=reasoning,
                alternative_models=alternative_models if alternative_models else None
            )
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            raise DesignerException(f"LLM analysis failed: {str(e)}")

