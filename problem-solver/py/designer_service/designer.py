"""
Main logic for neural network designer
Analyzes user task and determines optimal model type
Uses LLM for deep task analysis
"""
import re
import json
import logging
from typing import Dict, List, Tuple, Optional
from .models import ModelType, ModelRecommendation
from .llm_utils import LLMAnalyzer

logger = logging.getLogger(__name__)


class ModelDesigner:
    """Class for task analysis and optimal model determination"""
    
    KEYWORDS = {
        ModelType.RANDOM_FOREST: [
            "random forest", "случайный лес", "rf", "дерево решений", "ensemble",
            "classification", "классификация", "tabular", "табличные данные"
        ],
        ModelType.LOGISTIC_REGRESSION: [
            "logistic regression", "логистическая регрессия", "lr", "binary",
            "бинарная", "probability", "вероятность", "linear", "линейная"
        ],
        ModelType.GRADIENT_BOOSTING: [
            "gradient boosting", "градиентный бустинг", "grb", "xgboost", "lightgbm",
            "catboost", "ensemble", "ансамбль", "performance", "производительность"
        ],
        ModelType.NEURAL_NETWORK: [
            "neural network", "нейронная сеть", "nn", "deep learning", "глубокое обучение",
            "image", "изображение", "image recognition", "распознавание изображений",
            "nlp", "natural language", "естественный язык", "sequence", "последовательность",
            "cnn", "rnn", "lstm", "transformer"
        ],
        ModelType.SVM: [
            "svm", "support vector machine", "машина опорных векторов", "kernel",
            "ядерный метод", "small dataset", "маленький датасет"
        ],
        ModelType.DECISION_TREE: [
            "decision tree", "дерево решений", "dt", "interpretable", "интерпретируемый",
            "simple", "простой"
        ],
        ModelType.KNN: [
            "knn", "k-nearest neighbors", "k ближайших соседей", "lazy learning",
            "ленивое обучение", "similarity", "похожесть"
        ],
        ModelType.LINEAR_REGRESSION: [
            "linear regression", "линейная регрессия", "regression", "регрессия",
            "continuous", "непрерывный", "prediction", "прогнозирование"
        ]
    }
    
    def __init__(self, use_llm: bool = True):
        """
        Initialize designer
        
        Args:
            use_llm: Whether to use LLM for analysis (default True)
        """
        self.use_llm = use_llm
        if self.use_llm:
            try:
                self.llm_analyzer = LLMAnalyzer()
                logger.info("LLM analyzer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM analyzer: {e}. Using keyword fallback.")
                self.use_llm = False
                self.llm_analyzer = None
        else:
            self.llm_analyzer = None
        
        self._compile_patterns()
    
    def _compile_patterns(self):
        self.patterns = {}
        for model_type, keywords in self.KEYWORDS.items():
            pattern = re.compile(
                r'\b(?:' + '|'.join(re.escape(kw) for kw in keywords) + r')\b',
                re.IGNORECASE
            )
            self.patterns[model_type] = pattern
    
    async def analyze_task(self, task_description: str) -> ModelRecommendation:
        """
        Analyzes task and determines optimal model
        Uses LLM if available, otherwise falls back to keyword matching
        
        Args:
            task_description: Text description of the task
            
        Returns:
            ModelRecommendation with model recommendation
        """
        logger.info(f"Analyzing task: {task_description[:100]}...")
        
        if self.use_llm and self.llm_analyzer:
            try:
                llm_result = await self.llm_analyzer.analyze_task(task_description)
                
                recommended_model = ModelType(llm_result.get("recommended_model", "NN"))
                
                raw_confidence = float(llm_result.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, raw_confidence))
                
                if confidence < 0.3:
                    confidence = 0.3
                elif confidence > 0.95:
                    confidence = 0.95
                
                reasoning = llm_result.get("reasoning", "Рекомендация на основе LLM анализа")
                
                alt_models = llm_result.get("alternative_models", [])
                alternative_models = [
                    ModelType(alt) for alt in alt_models 
                    if alt in [m.value for m in ModelType]
                ]
                
                logger.info(f"LLM recommendation: {recommended_model.value}, confidence: {confidence:.2f}")
                
                return ModelRecommendation(
                    recommended_model=recommended_model,
                    confidence=confidence,
                    reasoning=reasoning,
                    alternative_models=alternative_models[:2] if alternative_models else None
                )
            
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                logger.debug(f"LLM did not return valid JSON, using keyword fallback.")
            except Exception as e:
                logger.warning(f"Error using LLM analysis: {type(e).__name__}. Using keyword fallback.")
        
        return self._analyze_with_keywords(task_description)
    
    def _analyze_with_keywords(self, task_description: str) -> ModelRecommendation:
        """
        Fallback method: keyword-based analysis
        
        Args:
            task_description: Text description of the task
            
        Returns:
            ModelRecommendation with model recommendation
        """
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
            recommended_model, confidence, reasoning = self._fallback_analysis(normalized_text)
        else:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            recommended_model = sorted_scores[0][0]
            max_score = scores[recommended_model]
            total_score = sum(scores.values())
            
            score_ratio = max_score / max(total_score, 1)
            
            if max_score == 1:
                match_base = 0.6
            elif max_score == 2:
                match_base = 0.75
            else:
                match_base = 0.9
            
            if len(sorted_scores) > 1:
                second_score = sorted_scores[1][1]
                gap_ratio = (max_score - second_score) / max(max_score, 1)
                competition_factor = 0.7 + (gap_ratio * 0.3)
            else:
                competition_factor = 0.95
            
            if len(scores) == 1:
                diversity_factor = 1.0
            elif len(scores) == 2:
                diversity_factor = 0.9
            else:
                diversity_factor = 0.8
            
            confidence = (
                match_base * 0.5 +
                score_ratio * 0.2 +
                competition_factor * 0.2 +
                diversity_factor * 0.1
            )
            
            confidence = max(0.55, min(confidence, 0.95))
            confidence = round(confidence, 2)
            
            reasoning = self._generate_reasoning(
                recommended_model, 
                matches[recommended_model],
                scores
            )
        
        sorted_models = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        alternative_models = [
            model for model, score in sorted_models[1:3]
            if score > 0
        ]
        
        logger.info(f"Recommendation (keywords): {recommended_model.value}, confidence: {confidence:.2f}")
        
        return ModelRecommendation(
            recommended_model=recommended_model,
            confidence=confidence,
            reasoning=reasoning,
            alternative_models=alternative_models[:2] if alternative_models else None
        )
    
    def _fallback_analysis(self, text: str) -> Tuple[ModelType, float, str]:
        """
        Fallback analysis when no explicit keyword matches found
        
        Args:
            text: Normalized task text
            
        Returns:
            Tuple (model, confidence, reasoning)
        """
        image_keywords = ["image", "изображение", "изображений", "изображениями", "picture", "photo", "картинка", "картинки", "видео", "video", "фото"]
        image_matches = sum(1 for word in image_keywords if word in text)
        if image_matches > 0:
            confidence = 0.55 + (min(image_matches - 1, 2) * 0.1)
            return ModelType.NEURAL_NETWORK, confidence, f"Задача связана с изображениями (найдено {image_matches} ключевых слов) - рекомендуется нейронная сеть (CNN)"
        
        text_keywords = ["text", "текст", "language", "язык", "nlp", "word", "слово", "речь", "speech"]
        text_matches = sum(1 for word in text_keywords if word in text)
        if text_matches > 0:
            confidence = 0.5 + (min(text_matches, 3) * 0.1)
            return ModelType.NEURAL_NETWORK, confidence, f"Задача связана с текстом (найдено {text_matches} ключевых слов) - рекомендуется нейронная сеть (RNN/LSTM/Transformer)"
        
        table_keywords = ["table", "таблица", "csv", "dataframe", "column", "столбец", "данные", "data", "характеристик", "характеристики"]
        table_matches = sum(1 for word in table_keywords if word in text)
        if table_matches > 0:
            confidence = 0.5 + (min(table_matches - 1, 2) * 0.1)
            return ModelType.GRADIENT_BOOSTING, confidence, f"Задача связана с табличными данными (найдено {table_matches} ключевых слов) - рекомендуется градиентный бустинг"
        
        regression_keywords = ["regression", "регрессия", "predict", "предсказания", "предсказание", "прогноз", "forecast", "цена", "price", "стоимость", "недвижимость"]
        regression_matches = sum(1 for word in regression_keywords if word in text)
        if regression_matches > 0:
            confidence = 0.5 + (min(regression_matches - 1, 2) * 0.1)
            return ModelType.LINEAR_REGRESSION, confidence, f"Задача регрессии (найдено {regression_matches} ключевых слов) - рекомендуется линейная регрессия или градиентный бустинг"
        
        classification_keywords = ["classification", "классификация", "classify", "категория", "category"]
        classification_matches = sum(1 for word in classification_keywords if word in text)
        if classification_matches > 0:
            confidence = 0.5 + (min(classification_matches - 1, 2) * 0.1)
            return ModelType.RANDOM_FOREST, confidence, f"Задача классификации (найдено {classification_matches} ключевых слов) - рекомендуется случайный лес"
        
        return ModelType.NEURAL_NETWORK, 0.35, "На основе общего анализа рекомендуется нейронная сеть как универсальное решение (низкая уверенность из-за неопределенности задачи)"
    
    def _generate_reasoning(
        self, 
        model: ModelType, 
        matches: List[str], 
        all_scores: Dict[ModelType, float]
    ) -> str:
        """
        Generates text reasoning for model selection
        
        Args:
            model: Selected model
            matches: Found keywords
            all_scores: Scores for all models
            
        Returns:
            Text reasoning
        """
        model_names = {
            ModelType.RANDOM_FOREST: "Случайный лес (Random Forest)",
            ModelType.LOGISTIC_REGRESSION: "Логистическая регрессия",
            ModelType.GRADIENT_BOOSTING: "Градиентный бустинг",
            ModelType.NEURAL_NETWORK: "Нейронная сеть",
            ModelType.SVM: "Машина опорных векторов (SVM)",
            ModelType.DECISION_TREE: "Дерево решений",
            ModelType.KNN: "K ближайших соседей",
            ModelType.LINEAR_REGRESSION: "Линейная регрессия"
        }
        
        reasoning_parts = [
            f"Рекомендуется {model_names[model]}."
        ]
        
        if matches:
            reasoning_parts.append(f"Найдены ключевые слова: {', '.join(matches[:3])}.")
        
        sorted_alternatives = sorted(
            [(m, s) for m, s in all_scores.items() if m != model],
            key=lambda x: x[1],
            reverse=True
        )
        
        if sorted_alternatives and sorted_alternatives[0][1] > 0:
            alt_model, alt_score = sorted_alternatives[0]
            reasoning_parts.append(
                f"Альтернатива: {model_names[alt_model]} "
                f"(балл: {alt_score} vs {all_scores[model]})"
            )
        
        return " ".join(reasoning_parts)

