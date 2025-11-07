"""
FastAPI application for Designer Service
Microservice for neural network design
"""
import time
import uuid
import logging
from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .models import DesignTaskRequest, DesignTaskResponse, ModelRecommendation
from .designer import ModelDesigner
from .client import SolutionSearchClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="[%d-%b-%y %H:%M:%S]"
)
logger = logging.getLogger(__name__)

designer: ModelDesigner = None
solution_client: SolutionSearchClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global designer, solution_client
    
    logger.info("Initializing Designer Service...")
    designer = ModelDesigner()
    solution_client = SolutionSearchClient()
    logger.info("Designer Service ready")
    
    yield
    
    logger.info("Stopping Designer Service...")


app = FastAPI(
    title="Designer Service",
    description="Microservice for neural network design. Determines optimal model type for solving user task.",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "designer-service",
        "version": "0.1.0"
    }


@app.post("/api/v1/design", response_model=DesignTaskResponse)
async def design_model(request: DesignTaskRequest):
    """
    Main endpoint for model design
    
    Accepts user task description, analyzes it
    and determines optimal model type (RF, LR, GRB, NN, etc.)
    """
    start_time = time.time()
    
    task_id = request.task_id or str(uuid.uuid4())
    
    logger.info(f"Received design request for task {task_id}")
    
    try:
        if not request.task_description or not request.task_description.strip():
            raise HTTPException(
                status_code=400,
                detail="Task description cannot be empty"
            )
        
        recommendation = await designer.analyze_task(request.task_description)
        
        search_response = await solution_client.send_recommendation(
            task_id=task_id,
            recommendation=recommendation,
            task_description=request.task_description
        )
        
        if not search_response.success:
            logger.warning(
                f"Failed to send recommendation to search service for task {task_id}: "
                f"{search_response.message}"
            )
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"Task {task_id} processed. Recommendation: {recommendation.recommended_model.value}, "
            f"time: {processing_time:.2f}ms"
        )
        
        return DesignTaskResponse(
            task_id=task_id,
            recommendation=recommendation,
            processing_time_ms=processing_time
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/api/v1/models")
async def list_available_models():
    """Returns list of available model types"""
    from .models import ModelType
    
    return {
        "available_models": [
            {
                "code": model.value,
                "name": model.name
            }
            for model in ModelType
        ]
    }


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(
        "designer_service.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

