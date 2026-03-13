"""
API routes for text analysis
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Body
from typing import List, Optional
import tempfile
import os
import logging
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, DetectedEntitySchema, AppliedPolicySchema
from app.services.policy_service import PolicyService
from app.services.presidio_service import PresidioService
from app.services.file_extractor_service import FileTextExtractor
from app.api.dependencies import get_optional_user, get_current_admin
from app.models_mongo.logs import Log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyze", tags=["Analysis"])

# Initialize services
presidio_service = PresidioService()
policy_service = PolicyService()
file_extractor = FileTextExtractor()


async def _log_analysis_activity(
    event_type: str,
    message: str,
    source_ip: Optional[str] = None,
    source_user: Optional[str] = None,
    extra_data: Optional[dict] = None,
):
    """Log analysis activity for User Activity Log."""
    try:
        log = Log(
            event_type=event_type,
            message=message,
            level="INFO",
            source_ip=source_ip,
            source_user=source_user,
            extra_data=extra_data or {},
        )
        await log.insert()
    except Exception as e:
        logger.warning(f"Failed to log analysis activity: {e}")


@router.post("/", response_model=AnalysisResponse)
async def analyze_text(
    request: AnalysisRequest,
    http_request: Request
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
    current_user = await get_optional_user(http_request)
    source_user = request.source_user or (getattr(current_user, "username", None) or (getattr(current_user, "email", None) if current_user else None))
    source_ip = request.source_ip or (http_request.client.host if http_request and getattr(http_request, "client", None) else None)
    try:
        if request.apply_policies:
            # Apply policies (includes Presidio analysis)
            result = await policy_service.apply_policy(
                text=request.text,
                source_ip=source_ip,
                source_user=source_user,
                source_device=request.source_device
            )
            
            # Convert to response format
            detected_entities = [
                DetectedEntitySchema(**entity) 
                for entity in result.get("detected_entities", [])
            ]
            
            # Convert applied policies
            applied_policies = [
                AppliedPolicySchema(**policy)
                for policy in result.get("applied_policies", [])
            ]
            
            # Always log analysis for User Activity Log (so it appears even if policy_service log has no source_user)
            await _log_analysis_activity(
                event_type="analysis",
                message=f"Text analysis with policies: {len(result.get('detected_entities', []))} entities detected",
                source_ip=source_ip,
                source_user=source_user,
                extra_data={
                    "detected_entities_count": len(result.get("detected_entities", [])),
                    "policies_matched": result.get("policies_matched", False),
                    "apply_policies": True,
                },
            )
            
            return AnalysisResponse(
                sensitive_data_detected=result["sensitive_data_detected"],
                detected_entities=detected_entities,
                actions_taken=result["actions_taken"],
                blocked=result["blocked"],
                alert_created=result.get("alert_created", False),
                policies_matched=result.get("policies_matched", False),
                applied_policies=applied_policies,
                encrypted_text=result.get("encrypted_text")
            )
        else:
            # Only analyze without applying policies
            detected_entities = presidio_service.analyze(
                text=request.text,
                language=request.language
            )
            
            # Log for User Activity so text-only analysis appears in User Activity Log
            await _log_analysis_activity(
                event_type="analysis",
                message=f"Text analysis: {len(detected_entities)} entities detected",
                source_ip=source_ip,
                source_user=source_user,
                extra_data={
                    "detected_entities_count": len(detected_entities),
                    "apply_policies": False,
                },
            )
            
            return AnalysisResponse(
                sensitive_data_detected=len(detected_entities) > 0,
                detected_entities=[DetectedEntitySchema(**e) for e in detected_entities],
                actions_taken=[],
                blocked=False,
                alert_created=False,
                policies_matched=False,
                applied_policies=[]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing text: {str(e)}")


@router.post("/file", response_model=AnalysisResponse)
async def analyze_file(
    file: UploadFile = File(...),
    apply_policies: bool = Form(True),
    source_ip: Optional[str] = Form(None),
    source_user: Optional[str] = Form(None),
    source_device: Optional[str] = Form(None),
    http_request: Request = None
):
    """
    Analyze uploaded file for sensitive data
    
    - **file**: File to analyze (PDF, DOCX, TXT, XLSX supported)
    - **apply_policies**: Whether to automatically apply policies
    - **source_ip**: Optional source IP address
    - **source_user**: Optional source user
    - **source_device**: Optional source device
    """
    temp_file_path = None
    try:
        # Check if file format is supported
        if not file_extractor.is_supported(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported formats: {', '.join(file_extractor.get_supported_formats())}"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Create temporary file for extraction
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        # Extract text from file
        try:
            extracted_text = file_extractor.extract_text(temp_file_path, file_content)
        except Exception as e:
            logger.error(f"Error extracting text from file: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to extract text from file: {str(e)}"
            )
        
        if not extracted_text or not extracted_text.strip():
            return AnalysisResponse(
                sensitive_data_detected=False,
                detected_entities=[],
                actions_taken=[],
                blocked=False,
                alert_created=False
            )
        
        # Try to get current user
        current_user = await get_optional_user(http_request) if http_request else None
        # Use current user if logged in and source_user not provided
        final_source_user = source_user or (current_user.username if current_user else None)
        
        # Get client IP if not provided
        if not source_ip and http_request:
            source_ip = http_request.client.host if http_request.client else None
        
        # Log file analysis operation
        try:
            file_log = Log(
                event_type="file_analyzed",
                message=f"File analyzed: {file.filename}",
                level="INFO",
                source_ip=source_ip,
                source_user=final_source_user,
                file_name=file.filename,
                file_size=len(file_content),
                file_type=os.path.splitext(file.filename)[1] if file.filename else None,
                extra_data={
                    "filename": file.filename,
                    "file_size": len(file_content),
                    "apply_policies": apply_policies
                }
            )
            await file_log.insert()
        except Exception as e:
            logger.warning(f"Failed to log file operation: {e}")
        
        # Analyze extracted text
        if apply_policies:
            # Apply policies (includes Presidio analysis)
            result = await policy_service.apply_policy(
                text=extracted_text,
                source_ip=source_ip,
                source_user=final_source_user,
                source_device=source_device
            )
            
            # Convert to response format
            detected_entities = [
                DetectedEntitySchema(**entity) 
                for entity in result.get("detected_entities", [])
            ]
            
            # Convert applied policies
            applied_policies = [
                AppliedPolicySchema(**policy)
                for policy in result.get("applied_policies", [])
            ]
            
            return AnalysisResponse(
                sensitive_data_detected=result["sensitive_data_detected"],
                detected_entities=detected_entities,
                actions_taken=result["actions_taken"],
                blocked=result["blocked"],
                alert_created=result.get("alert_created", False),
                policies_matched=result.get("policies_matched", False),
                applied_policies=applied_policies,
                encrypted_text=result.get("encrypted_text")
            )
        else:
            # Only analyze without applying policies
            detected_entities = presidio_service.analyze(
                text=extracted_text,
                language=None
            )
            
            return AnalysisResponse(
                sensitive_data_detected=len(detected_entities) > 0,
                detected_entities=[DetectedEntitySchema(**e) for e in detected_entities],
                actions_taken=[],
                blocked=False,
                alert_created=False
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing file: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing file: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


@router.get("/entities", response_model=List[str])
async def get_supported_entities():
    """
    Get list of supported entity types for detection
    """
    return presidio_service.get_supported_entities()


@router.get("/file/formats")
async def get_supported_file_formats():
    """
    Get list of supported file formats for file upload
    """
    return {
        "supported_formats": file_extractor.get_supported_formats(),
        "formats_description": {
            ".txt": "Plain text files",
            ".pdf": "PDF documents",
            ".docx": "Microsoft Word documents (2007+)",
            ".xlsx": "Microsoft Excel spreadsheets (2007+)"
        }
    }


@router.post("/decrypt")
async def decrypt_content(
    body: dict = Body(...),
    current_user = Depends(get_current_admin)
):
    """
    Decrypt content that was encrypted by the system (فك التشفير). Admin only.
    Body: { "content": "base64_encrypted_string" }
    """
    content = body.get("content") if isinstance(body, dict) else None
    if not content or not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=400, detail="content is required and must be a non-empty string")
    try:
        # Support mixed content: plain text + Fernet tokens (e.g. pasted email body with one encrypted phone)
        decrypted = policy_service.encryption.decrypt_mixed_content(content.strip())
        return {"decrypted": decrypted}
    except Exception as e:
        logger.warning(f"Decrypt failed: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid or not encrypted content. Paste text encrypted by this system."
        )

