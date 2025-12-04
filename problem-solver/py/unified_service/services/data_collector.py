"""
Deterministic data collector for build_model tasks.
"""
import logging
from typing import Dict, Tuple, List, Optional

logger = logging.getLogger(__name__)


class DataCollector:
    """Rule-based service for gathering ML design requirements."""
    
    REQUIRED_FIELDS = ["data", "features", "output", "metric_goal"]
    FIELD_METADATA = {
        "data": {
            "label": "Данные для обучения",
            "description": "Источник, объем и формат датасета",
            "placeholder": "Например: 25k jpg изображений котов и собак из Kaggle"
        },
        "features": {
            "label": "Признаки / характеристики",
            "description": "Какие признаки будут использоваться моделью",
            "placeholder": "Например: сырые пиксели, цветовые гистограммы, аугментации"
        },
        "output": {
            "label": "Целевая переменная",
            "description": "Что должна предсказывать модель",
            "placeholder": "Например: класс 'кот' или 'собака'"
        },
        "metric_goal": {
            "label": "Целевая метрика",
            "description": "Каким критерием оцениваем успешность",
            "placeholder": "Например: accuracy ≥ 0.9 или F1 ≥ 0.85"
        }
    }
    
    def __init__(self):
        logger.info("DataCollector initialized with form-based flow")
    
    async def collect_data(
        self,
        collected_data: Dict[str, str],
        text_response: Optional[str] = None
    ) -> Tuple[Dict[str, str], List[Dict[str, Optional[str]]], bool, str]:
        return self._collect(collected_data, text_response)
    
    def collect_data_sync(
        self,
        collected_data: Dict[str, str],
        text_response: Optional[str] = None
    ) -> Tuple[Dict[str, str], List[Dict[str, Optional[str]]], bool, str]:
        return self._collect(collected_data, text_response)
    
    def _collect(
        self,
        collected_data: Dict[str, str],
        text_response: Optional[str] = None
    ) -> Tuple[Dict[str, str], List[Dict[str, Optional[str]]], bool, str]:
        data = self.sanitize_data(collected_data)
        logger.info("Collecting data. Existing keys: %s", list(data.keys()))
        
        if text_response:
            self._fill_first_missing(data, text_response)
        
        form_fields = self._build_form_fields(data)
        missing = [field for field in self.REQUIRED_FIELDS if not data.get(field)]
        is_complete = len(missing) == 0
        
        if is_complete:
            message = "Все данные собраны! Начинаю подбор модели..."
            logger.info("Data collection complete")
        else:
            first_missing = self.FIELD_METADATA[missing[0]]["label"]
            message = f"Заполните обязательные поля (например, «{first_missing}»), чтобы продолжить."
            logger.info("Data collection requires more inputs: %s", missing)
        
        return data, form_fields, is_complete, message
    
    def sanitize_data(self, data: Dict[str, str]) -> Dict[str, str]:
        """Normalize whitespace and remove None values."""
        sanitized = {}
        for key, value in (data or {}).items():
            if value:
                sanitized[key] = value.strip()
        return sanitized
    
    def _fill_first_missing(self, data: Dict[str, str], answer: str) -> None:
        answer = answer.strip()
        if not answer:
            return
        for field in self.REQUIRED_FIELDS:
            if not data.get(field):
                data[field] = answer
                logger.info("Mapped textual answer to field '%s'", field)
                break
    
    def _build_form_fields(self, data: Dict[str, str]) -> List[Dict[str, Optional[str]]]:
        fields: List[Dict[str, Optional[str]]] = []
        for name in self.REQUIRED_FIELDS:
            meta = self.FIELD_METADATA[name]
            fields.append({
                "name": name,
                "label": meta["label"],
                "description": meta["description"],
                "placeholder": meta["placeholder"],
                "value": data.get(name),
                "required": True
            })
        return fields

