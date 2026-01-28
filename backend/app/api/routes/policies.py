"""
API routes for policy management - MongoDB version
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from app.schemas.policies import PolicyCreate, PolicyUpdate, PolicyResponse
from app.models_mongo.policies import Policy
from app.services.mydlp_service import MyDLPService
from app.api.dependencies import get_current_admin
from app.utils.datetime_utils import get_current_time

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
    
    Prevents duplicate policies (same name or same content).
    """
    try:
        # Check if policy with same name exists (including soft-deleted)
        existing = await Policy.find_one({"name": policy.name})
        if existing and not existing.is_deleted:
            raise HTTPException(
                status_code=400, 
                detail="Policy with this name already exists"
            )
        
        # Check for duplicate content (same entity_types, action, and severity)
        # Only check non-deleted policies
        all_policies = await Policy.find({"is_deleted": False}).to_list()
        for existing_policy in all_policies:
            # Check if content is identical
            if (sorted(existing_policy.entity_types) == sorted(policy.entity_types) and
                existing_policy.action == policy.action and
                existing_policy.severity == policy.severity):
                raise HTTPException(
                    status_code=400,
                    detail=f"A policy with the same configuration already exists: {existing_policy.name}"
                )
        
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


@router.get("/", response_model=Dict[str, Any])
async def get_policies(
    enabled: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get all policies with pagination, optionally filtered by enabled status
    
    Returns all non-deleted policies (both enabled and disabled) by default.
    Use 'enabled' parameter to filter by status.
    
    Query parameters:
    - enabled: Filter by enabled status (True/False). If not provided, returns all policies.
    - page: Page number (default: 1)
    - limit: Items per page (default: 10, max: 100)
    """
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Fetching policies - enabled filter: {enabled}, page: {page}, limit: {limit}, user: {current_user.username if current_user else 'None'}")
        
        # Get all non-deleted policies (including those where is_deleted is null/undefined)
        # For Beanie, we need to use a different approach - get all and filter in Python
        # OR use MongoDB query syntax directly
        # First, try to get all policies and filter
        base_query = Policy.find({})  # Get all policies first
        
        # Only filter by enabled if explicitly provided
        if enabled is not None:
            base_query = Policy.find({"enabled": enabled})
        
        # Get all policies and filter out deleted ones in Python
        # This ensures we get policies even if is_deleted field doesn't exist
        all_policies = await base_query.to_list()
        policies_list = [p for p in all_policies if not getattr(p, 'is_deleted', False)]
        
        # Sort by created_at descending
        policies_list = sorted(policies_list, key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination manually
        total_count = len(policies_list)
        skip = (page - 1) * limit
        policies = policies_list[skip:skip + limit]
        
        logger.info(f"Total policies found: {total_count}, showing {len(policies)} on page {page}")
        
        # Convert to result format
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
        
        # Calculate pagination metadata
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        
        logger.info(f"Returning {len(result)} policies successfully (page {page}/{total_pages})")
        
        return {
            "items": result,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
    except HTTPException as http_err:
        logger.error(f"HTTP error in get_policies: {http_err.status_code} - {http_err.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching policies: {e}")
        logger.error(traceback.format_exc())
        # Return empty result instead of raising error to prevent frontend crash
        return {
            "items": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False
        }


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get a specific policy by ID
    
    Only returns non-deleted policies.
    """
    try:
        policy = await Policy.get(policy_id)
        if policy.is_deleted:
            raise HTTPException(status_code=404, detail="Policy not found")
    except HTTPException:
        raise
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
    
    Cannot update deleted policies.
    Prevents duplicate content when updating.
    """
    try:
        try:
            policy = await Policy.get(policy_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        if policy.is_deleted:
            raise HTTPException(status_code=404, detail="Policy not found (deleted)")
        
        # Update fields
        update_data = policy_update.dict(exclude_unset=True)
        
        # Check for duplicate content if entity_types, action, or severity are being updated
        if any(key in update_data for key in ['entity_types', 'action', 'severity']):
            # Get the updated values
            new_entity_types = update_data.get('entity_types', policy.entity_types)
            new_action = update_data.get('action', policy.action)
            new_severity = update_data.get('severity', policy.severity)
            
            # Check for duplicates (excluding current policy)
            all_policies = await Policy.find({"is_deleted": False}).to_list()
            for existing_policy in all_policies:
                if str(existing_policy.id) != policy_id:  # Exclude current policy
                    if (sorted(existing_policy.entity_types) == sorted(new_entity_types) and
                        existing_policy.action == new_action and
                        existing_policy.severity == new_severity):
                        raise HTTPException(
                            status_code=400,
                            detail=f"A policy with the same configuration already exists: {existing_policy.name}"
                        )
        
        for field, value in update_data.items():
            setattr(policy, field, value)
        
        policy.updated_at = get_current_time()
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
    Soft delete a policy (marks as deleted, does not actually delete)
    
    Policies cannot be permanently deleted for audit purposes.
    """
    try:
        try:
            policy = await Policy.get(policy_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        if policy.is_deleted:
            raise HTTPException(status_code=404, detail="Policy already deleted")
        
        # Soft delete: mark as deleted instead of actually deleting
        policy.is_deleted = True
        policy.updated_at = get_current_time()
        await policy.save()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting policy: {str(e)}")


@router.post("/{policy_id}/restore", response_model=PolicyResponse)
async def restore_policy(
    policy_id: str,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Restore a soft-deleted policy
    
    Restores a previously deleted policy by setting is_deleted to False.
    """
    try:
        try:
            policy = await Policy.get(policy_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        if not policy.is_deleted:
            raise HTTPException(status_code=400, detail="Policy is not deleted")
        
        # Restore policy
        policy.is_deleted = False
        policy.updated_at = get_current_time()
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
        raise HTTPException(status_code=500, detail=f"Error restoring policy: {str(e)}")


@router.get("/deleted", response_model=List[PolicyResponse])
async def get_deleted_policies(
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get all deleted policies (Admin only)
    
    Returns only soft-deleted policies for restoration purposes.
    """
    try:
        deleted_policies = await Policy.find({"is_deleted": True}).sort("-updated_at").to_list()
        
        result = []
        for policy in deleted_policies:
            result.append(PolicyResponse(
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
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching deleted policies: {str(e)}")
