"""
Тестовый клиент для проверки работы Designer Service
"""
import requests
import json

BASE_URL = "http://localhost:8002"


def test_health():
    """Проверка здоровья сервиса"""
    print("=" * 50)
    print("Тест 1: Проверка здоровья сервиса")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()


def test_list_models():
    """Получение списка доступных моделей"""
    print("=" * 50)
    print("Тест 2: Получение списка моделей")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/v1/models")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()


def test_design_task(task_description: str):
    """Тест проектирования модели"""
    print("=" * 50)
    print(f"Тест 3: Проектирование модели")
    print(f"Описание задачи: {task_description}")
    print("=" * 50)
    
    payload = {
        "task_description": task_description
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/design",
        json=payload
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Task ID: {result['task_id']}")
        print(f"Рекомендуемая модель: {result['recommendation']['recommended_model']}")
        print(f"Уверенность: {result['recommendation']['confidence']:.2f}")
        print(f"Обоснование: {result['recommendation']['reasoning']}")
        if result['recommendation']['alternative_models']:
            print(f"Альтернативы: {result['recommendation']['alternative_models']}")
        print(f"Время обработки: {result['processing_time_ms']:.2f}ms")
    else:
        print(f"Error: {response.text}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Тестирование Designer Service")
    print("=" * 50 + "\n")
    
    try:
        # Тест 1: Health check
        test_health()
        
        # Тест 2: List models
        test_list_models()
        
        # Тест 3: Design tasks
        test_cases = [
            "Мне нужно создать модель для классификации изображений кошек и собак",
            "Нужна модель для предсказания цен на недвижимость на основе характеристик",
            "Классификация текстовых отзывов на положительные и отрицательные",
            "Распознавание речи и преобразование в текст",
            "Анализ табличных данных для определения категории клиента"
        ]
        
        for i, task in enumerate(test_cases, 1):
            print(f"\n--- Тест 3.{i} ---\n")
            test_design_task(task)
        
        print("\n" + "=" * 50)
        print("Все тесты завершены!")
        print("=" * 50)
        
    except requests.exceptions.ConnectionError:
        print("Ошибка: Не удалось подключиться к сервису.")
        print("Убедитесь, что сервис запущен на http://localhost:8002")
    except Exception as e:
        print(f"Ошибка: {e}")

