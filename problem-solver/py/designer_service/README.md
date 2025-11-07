# Designer Service

Microservice that determines optimal ML model type from task description using LLM.

## API

**POST** `/api/v1/design`
```json
{
  "task_description": "classify images"
}
```

**GET** `/health`

**GET** `/api/v1/models`

## Models

RF, LR, GRB, NN, SVM, DT, KNN, LinR
