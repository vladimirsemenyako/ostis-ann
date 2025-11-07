FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/venv

RUN python -m venv $VENV_PATH \
    && $VENV_PATH/bin/pip install --upgrade pip

WORKDIR /workspace

# Копируем requirements для кешируемого слоя зависимостей
COPY problem-solver/py/designer_service/requirements.txt /tmp/requirements.txt
RUN $VENV_PATH/bin/pip install -r /tmp/requirements.txt

# Копируем код сервиса
COPY problem-solver/py/designer_service ./designer_service

ENV PATH="$VENV_PATH/bin:$PATH"

# Переменные окружения
ENV SOLUTION_SEARCH_SERVICE_URL=http://solution-search-service:8001
ENV PORT=8002

EXPOSE 8002

CMD ["uvicorn", "designer_service.main:app", "--host", "0.0.0.0", "--port", "8002"]

