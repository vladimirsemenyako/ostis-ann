"""
Client for sending recommendations to solution search service (HF/Github)
"""
import os
import logging
import httpx
from typing import Optional
from .models import ModelRecommendation, ServiceResponse

logger = logging.getLogger(__name__)


class SolutionSearchClient:
    """Client for interacting with solution search service"""
    
    def __init__(self, service_url: Optional[str] = None):
        """
        Initialize client
        
        Args:
            service_url: Solution search service URL.
                       If not provided, taken from SOLUTION_SEARCH_SERVICE_URL environment variable
        """
        self.service_url = service_url or os.getenv(
            "SOLUTION_SEARCH_SERVICE_URL",
            "http://localhost:8001"
        )
        self.timeout = 30.0
    
    async def send_recommendation(
        self,
        task_id: str,
        recommendation: ModelRecommendation,
        task_description: str
    ) -> ServiceResponse:
        """
        Sends model recommendation to solution search service
        
        Args:
            task_id: Task identifier
            recommendation: Model recommendation
            task_description: Original task description
            
        Returns:
            ServiceResponse with solution search result
        """
        endpoint = f"{self.service_url}/api/v1/search-solution"
        
        payload = {
            "task_id": task_id,
            "recommended_model": recommendation.recommended_model.value,
            "confidence": recommendation.confidence,
            "reasoning": recommendation.reasoning,
            "task_description": task_description,
            "alternative_models": [
                alt.value for alt in (recommendation.alternative_models or [])
            ]
        }
        
        logger.info(f"Sending recommendation to {endpoint} for task {task_id}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully received response from search service for task {task_id}")
                
                return ServiceResponse(
                    success=True,
                    message=result.get("message", "Solution found"),
                    solution_url=result.get("solution_url"),
                    solution_details=result.get("solution_details")
                )
        
        except httpx.TimeoutException:
            logger.error(f"Timeout when calling search service for task {task_id}")
            return ServiceResponse(
                success=False,
                message="Timeout when calling solution search service"
            )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} when calling search service: {e}")
            return ServiceResponse(
                success=False,
                message=f"Search service error: {e.response.status_code}"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error when calling search service: {e}")
            return ServiceResponse(
                success=False,
                message=f"Error calling search service: {str(e)}"
            )
    
    def send_recommendation_sync(
        self,
        task_id: str,
        recommendation: ModelRecommendation,
        task_description: str
    ) -> ServiceResponse:
        """
        Synchronous version of sending recommendation
        Used for compatibility if search service doesn't support async yet
        
        Args:
            task_id: Task identifier
            recommendation: Model recommendation
            task_description: Original task description
            
        Returns:
            ServiceResponse with solution search result
        """
        import requests
        
        endpoint = f"{self.service_url}/api/v1/search-solution"
        
        payload = {
            "task_id": task_id,
            "recommended_model": recommendation.recommended_model.value,
            "confidence": recommendation.confidence,
            "reasoning": recommendation.reasoning,
            "task_description": task_description,
            "alternative_models": [
                alt.value for alt in (recommendation.alternative_models or [])
            ]
        }
        
        logger.info(f"Sending recommendation (sync) to {endpoint} for task {task_id}")
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Successfully received response from search service for task {task_id}")
            
            return ServiceResponse(
                success=True,
                message=result.get("message", "Solution found"),
                solution_url=result.get("solution_url"),
                solution_details=result.get("solution_details")
            )
        
        except requests.Timeout:
            logger.error(f"Timeout when calling search service for task {task_id}")
            return ServiceResponse(
                success=False,
                message="Timeout when calling solution search service"
            )
        
        except requests.HTTPError as e:
            logger.error(f"HTTP error when calling search service: {e}")
            return ServiceResponse(
                success=False,
                message=f"Search service error: {response.status_code}"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error when calling search service: {e}")
            return ServiceResponse(
                success=False,
                message=f"Error calling search service: {str(e)}"
            )

