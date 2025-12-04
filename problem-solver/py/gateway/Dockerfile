FROM python:3.11-slim

WORKDIR /gateway

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libssl-dev && rm -rf /var/lib/apt/lists/*

COPY gateway/requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY gateway/app ./app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers"]
