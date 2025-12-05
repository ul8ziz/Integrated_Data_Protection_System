"""
API routes for text analysis
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, DetectedEntitySchema
from app.services.policy_service import PolicyService
from app.services.presidio_service import PresidioService

router = APIRouter(prefix="/api/analyze", tags=["Analysis"])

# Initialize services
presidio_service = PresidioService()
policy_service = PolicyService()


@router.post("/", response_model=AnalysisResponse)
async def analyze_text(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze text for sensitive data and apply policies
    
    - **text**: Text to analyze
    - **language**: Optional language code
    - **source_ip**: Optional source IP address
    - **source_user**: Optional source user
    - **source_device**: Optional source device
    - **apply_policies**: Whether to automatically apply policies
    """
    try:
        if request.apply_policies:
            # Apply policies (includes Presidio analysis)
            result = policy_service.apply_policy(
                db=db,
                text=request.text,
                source_ip=request.source_ip,
                source_user=request.source_user,
                source_device=request.source_device
            )
            
            # Convert to response format
            detected_entities = [
                DetectedEntitySchema(**entity) 
                for entity in result.get("detected_entities", [])
            ]
            
            return AnalysisResponse(
                sensitive_data_detected=result["sensitive_data_detected"],
                detected_entities=detected_entities,
                actions_taken=result["actions_taken"],
                blocked=result["blocked"],
                alert_created=result.get("alert_created", False)
            )
        else:
            # Only analyze without applying policies
            detected_entities = presidio_service.analyze(
                text=request.text,
                language=request.language
            )
            
            return AnalysisResponse(
                sensitive_data_detected=len(detected_entities) > 0,
                detected_entities=[DetectedEntitySchema(**e) for e in detected_entities],
                actions_taken=[],
                blocked=False,
                alert_created=False
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing text: {str(e)}")


@router.get("/entities", response_model=List[str])
async def get_supported_entities():
    """
    Get list of supported entity types for detection
    """
    return presidio_service.get_supported_entities()

