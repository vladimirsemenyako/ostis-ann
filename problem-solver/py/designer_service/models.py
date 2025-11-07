"""
Pydantic models for Designer Service
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class ModelType(str, Enum):
    """Model types that designer can recommend"""
    RANDOM_FOREST = "RF"
    LOGISTIC_REGRESSION = "LR"
    GRADIENT_BOOSTING = "GRB"
    NEURAL_NETWORK = "NN"
    SVM = "SVM"
    DECISION_TREE = "DT"
    KNN = "KNN"
    LINEAR_REGRESSION = "LinR"


class DesignTaskRequest(BaseModel):
    """Request for neural network design"""
    task_description: str = Field(..., description="Text description of the task from user")
    task_id: Optional[str] = Field(None, description="Unique task identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ModelRecommendation(BaseModel):
    """Model recommendation from designer"""
    recommended_model: ModelType = Field(..., description="Recommended model type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in recommendation (0-1)")
    reasoning: str = Field(..., description="Reasoning for model selection")
    alternative_models: Optional[list[ModelType]] = Field(None, description="Alternative options")


class DesignTaskResponse(BaseModel):
    """Designer response with recommendation"""
    task_id: str = Field(..., description="Task identifier")
    recommendation: ModelRecommendation = Field(..., description="Model recommendation")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")


class ServiceResponse(BaseModel):
    """Response from solution search service (HF/Github)"""
    success: bool
    message: str
    solution_url: Optional[str] = None
    solution_details: Optional[Dict[str, Any]] = None

