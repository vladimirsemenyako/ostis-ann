"""
Pydantic models for the unified service
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


# ===== Enums =====

class TaskCategory(str, Enum):
    """Task categories"""
    INFORMATIONAL = "informational"
    BUILD_MODEL = "build_model"
    UNCLEAR = "unclear"


class ChatMode(str, Enum):
    """Chat mode selection"""
    AUTO = "auto"  # Automatic classification
    CONSULTANT = "consultant"  # Force informational/RAG
    DESIGNER = "designer"  # Force build_model


class ModelType(str, Enum):
    """ML model types that designer can recommend"""
    RANDOM_FOREST = "RF"
    LOGISTIC_REGRESSION = "LR"
    GRADIENT_BOOSTING = "GRB"
    NEURAL_NETWORK = "NN"
    SVM = "SVM"
    DECISION_TREE = "DT"
    KNN = "KNN"
    LINEAR_REGRESSION = "LinR"


class AgentStatus(str, Enum):
    """Agent response status"""
    QUESTION = "question"  # Agent needs more information
    COMPLETE = "complete"  # Task completed
    ERROR = "error"  # Error occurred
    PROCESSING = "processing"  # Still processing


# ===== Request Models =====

class ChatRequest(BaseModel):
    """Main chat request"""
    query: str = Field(..., description="User query")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    user_response: Optional[str] = Field(None, description="User response to agent question")
    form_data: Optional[Dict[str, str]] = Field(None, description="Structured form data for build_model tasks")
    chat_mode: Optional[ChatMode] = Field(ChatMode.AUTO, description="Chat mode: auto, consultant, or designer")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Как создать модель для классификации изображений?",
                "session_id": "abc-123",
                "form_data": {"data": "50k изображений"}
            }
        }


class DocumentUploadRequest(BaseModel):
    """Document upload request metadata"""
    filename: str
    file_id: Optional[int] = None


class DeleteDocumentRequest(BaseModel):
    """Document deletion request"""
    file_id: int = Field(..., description="Document ID to delete")


# ===== Response Models =====

class FormField(BaseModel):
    """Description of a structured field requested from the user"""
    name: str
    label: str
    description: Optional[str] = None
    placeholder: Optional[str] = None
    value: Optional[str] = None
    required: bool = True


class ChatResponse(BaseModel):
    """Unified chat response"""
    status: AgentStatus = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    session_id: str = Field(..., description="Session identifier")
    
    # Optional fields depending on task category
    category: Optional[TaskCategory] = Field(None, description="Detected task category")
    collected_data: Optional[Dict[str, str]] = Field(None, description="Collected data for build_model tasks")
    form_fields: Optional[List[FormField]] = Field(None, description="Structured fields for user input")
    
    # Designer recommendation (for build_model tasks)
    recommended_model: Optional[ModelType] = Field(None, description="Recommended ML model")
    confidence: Optional[float] = Field(None, description="Recommendation confidence (0-1)")
    reasoning: Optional[str] = Field(None, description="Reasoning for recommendation")
    alternative_models: Optional[List[ModelType]] = Field(None, description="Alternative model options")
    
    # Code search results (for build_model tasks)
    best_link: Optional[str] = Field(None, description="Best code/model link")
    other_links: Optional[List[str]] = Field(None, description="Alternative links")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "complete",
                "message": "Рекомендуется использовать нейронную сеть",
                "session_id": "abc-123",
                "category": "build_model",
                "collected_data": {"data": "50k изображений"},
                "form_fields": [
                    {"name": "data", "label": "Данные", "value": "50k изображений", "required": True}
                ],
                "recommended_model": "NN",
                "confidence": 0.85
            }
        }


class DocumentInfo(BaseModel):
    """Document information"""
    id: int
    filename: str
    upload_timestamp: datetime
    
    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    message: str
    file_id: int
    filename: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    service: str = "ostis-ann-unified-service"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ===== Internal Models =====

class ModelRecommendation(BaseModel):
    """Model recommendation from designer"""
    recommended_model: ModelType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    alternative_models: Optional[List[ModelType]] = None


class SearchResult(BaseModel):
    """Search result from HuggingFace or GitHub"""
    name: str
    link: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "pytorch/vision",
                "link": "https://github.com/pytorch/vision"
            }
        }


class AgentState(BaseModel):
    """Internal agent state"""
    session_id: str
    category: Optional[TaskCategory] = None
    original_query: Optional[str] = None
    collected_data: Dict[str, str] = Field(default_factory=dict)
    messages: List[Dict[str, str]] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True


class DialogInfo(BaseModel):
    """Metadata for dialog list"""
    session_id: str
    title: Optional[str] = None
    category: Optional[TaskCategory] = None
    chat_mode: Optional[str] = None
    last_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DialogMessage(BaseModel):
    """Normalized dialog message"""
    id: str
    role: str
    content: str
    timestamp: datetime
    category: Optional[TaskCategory] = None
    meta: Optional[Dict[str, Any]] = None


class CreateDialogRequest(BaseModel):
    """Create dialog payload"""
    title: Optional[str] = None
    chat_mode: Optional[ChatMode] = Field(None, description="Chat mode: auto, consultant, or designer")


class UpdateDialogRequest(BaseModel):
    """Update dialog payload"""
    title: Optional[str] = None
    is_active: Optional[bool] = None

