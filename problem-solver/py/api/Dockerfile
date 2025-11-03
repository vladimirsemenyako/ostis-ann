FROM python:3.10-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/venv

RUN python -m venv $VENV_PATH \
    && $VENV_PATH/bin/pip install --upgrade pip

WORKDIR /workspace

# Копируем только requirements для кешируемого слоя зависимостей
COPY requirements.txt /tmp/requirements.txt
RUN $VENV_PATH/bin/pip install -r /tmp/requirements.txt

# В рантайме код будет примонтирован томом
ENV PATH="$VENV_PATH/bin:$PATH"


