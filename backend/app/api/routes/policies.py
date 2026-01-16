"""
API routes for policy management - MongoDB version
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.schemas.policies import PolicyCreate, PolicyUpdate, PolicyResponse
from app.models_mongo.policies import Policy
from app.services.mydlp_service import MyDLPService
from app.api.dependencies import get_current_admin
from datetime import datetime

router = APIRouter(prefix="/api/policies", tags=["Policies"])

mydlp_service = MyDLPService()


@router.get("/test")
async def test_policies_endpoint():
    """Test endpoint to verify policies route is accessible"""
    return {"status": "ok", "message": "Policies endpoint is working"}


@router.post("/", response_model=PolicyResponse, status_code=201)
async def create_policy(
    policy: PolicyCreate,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Create a new data protection policy
    """
    try:
        # Check if policy with same name exists
        existing = await Policy.find_one({"name": policy.name})
        if existing:
            raise HTTPException(status_code=400, detail="Policy with this name already exists")
        
        # Create policy
        policy_dict = policy.dict()
        policy_dict["created_by"] = str(current_user.id) if hasattr(current_user, 'id') else None
        db_policy = Policy(**policy_dict)
        await db_policy.insert()
        
        # Sync with MyDLP if enabled
        if mydlp_service.is_enabled():
            mydlp_service.create_policy({
                "name": policy.name,
                "entity_types": policy.entity_types,
                "action": policy.action
            })
        
        return PolicyResponse(
            id=str(db_policy.id),
            name=db_policy.name,
            description=db_policy.description,
            entity_types=db_policy.entity_types,
            action=db_policy.action,
            severity=db_policy.severity,
            enabled=db_policy.enabled,
            apply_to_network=db_policy.apply_to_network,
            apply_to_devices=db_policy.apply_to_devices,
            apply_to_storage=db_policy.apply_to_storage,
            gdpr_compliant=db_policy.gdpr_compliant,
            hipaa_compliant=db_policy.hipaa_compliant,
            created_at=db_policy.created_at,
            updated_at=db_policy.updated_at,
            created_by=db_policy.created_by
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating policy: {str(e)}")


@router.get("/", response_model=List[PolicyResponse])
async def get_policies(
    enabled: Optional[bool] = Query(None),
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get all policies, optionally filtered by enabled status
    """
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Fetching policies - enabled filter: {enabled}, user: {current_user.username if current_user else 'None'}")
        
        query = {}
        if enabled is not None:
            query["enabled"] = enabled
        
        logger.info(f"Query: {query}")
        
        # Try to fetch policies
        try:
            if query:
                policies = await Policy.find(query).to_list()
            else:
                policies = await Policy.find({}).to_list()
        except Exception as db_error:
            logger.error(f"Database error fetching policies: {db_error}")
            logger.error(traceback.format_exc())
            # Return empty list if database error
            return []
        
        logger.info(f"Found {len(policies)} policies from database")
        
        result = []
        for p in policies:
            try:
                result.append(PolicyResponse(
                    id=str(p.id),
                    name=p.name,
                    description=p.description,
                    entity_types=p.entity_types,
                    action=p.action,
                    severity=p.severity,
                    enabled=p.enabled,
                    apply_to_network=p.apply_to_network,
                    apply_to_devices=p.apply_to_devices,
                    apply_to_storage=p.apply_to_storage,
                    gdpr_compliant=p.gdpr_compliant,
                    hipaa_compliant=p.hipaa_compliant,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    created_by=p.created_by
                ))
            except Exception as e:
                logger.error(f"Error processing policy {p.id}: {e}")
                logger.error(traceback.format_exc())
                continue
        
        logger.info(f"Returning {len(result)} policies successfully")
        return result
        
    except HTTPException as http_err:
        logger.error(f"HTTP error in get_policies: {http_err.status_code} - {http_err.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching policies: {e}")
        logger.error(traceback.format_exc())
        # Return empty list instead of raising error to prevent frontend crash
        return []


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get a specific policy by ID
    """
    try:
        policy = await Policy.get(policy_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return PolicyResponse(
        id=str(policy.id),
        name=policy.name,
        description=policy.description,
        entity_types=policy.entity_types,
        action=policy.action,
        severity=policy.severity,
        enabled=policy.enabled,
        apply_to_network=policy.apply_to_network,
        apply_to_devices=policy.apply_to_devices,
        apply_to_storage=policy.apply_to_storage,
        gdpr_compliant=policy.gdpr_compliant,
        hipaa_compliant=policy.hipaa_compliant,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        created_by=policy.created_by
    )


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: str,
    policy_update: PolicyUpdate,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Update an existing policy
    """
    try:
        try:
            policy = await Policy.get(policy_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        # Update fields
        update_data = policy_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(policy, field, value)
        
        policy.updated_at = datetime.utcnow()
        await policy.save()
        
        return PolicyResponse(
            id=str(policy.id),
            name=policy.name,
            description=policy.description,
            entity_types=policy.entity_types,
            action=policy.action,
            severity=policy.severity,
            enabled=policy.enabled,
            apply_to_network=policy.apply_to_network,
            apply_to_devices=policy.apply_to_devices,
            apply_to_storage=policy.apply_to_storage,
            gdpr_compliant=policy.gdpr_compliant,
            hipaa_compliant=policy.hipaa_compliant,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
            created_by=policy.created_by
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating policy: {str(e)}")


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: str,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Delete a policy
    """
    try:
        try:
            policy = await Policy.get(policy_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        await policy.delete()
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting policy: {str(e)}")
