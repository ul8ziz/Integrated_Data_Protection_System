"""
API routes for policy management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.policies import PolicyCreate, PolicyUpdate, PolicyResponse
from app.models.policies import Policy
from app.services.mydlp_service import MyDLPService

router = APIRouter(prefix="/api/policies", tags=["Policies"])

mydlp_service = MyDLPService()


@router.post("/", response_model=PolicyResponse, status_code=201)
async def create_policy(
    policy: PolicyCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new data protection policy
    """
    try:
        # Check if policy with same name exists
        existing = db.query(Policy).filter(Policy.name == policy.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Policy with this name already exists")
        
        # Create policy
        db_policy = Policy(**policy.dict())
        db.add(db_policy)
        db.commit()
        db.refresh(db_policy)
        
        # Sync with MyDLP if enabled
        if mydlp_service.is_enabled():
            mydlp_service.create_policy({
                "name": policy.name,
                "entity_types": policy.entity_types,
                "action": policy.action
            })
        
        return PolicyResponse.model_validate(db_policy)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating policy: {str(e)}")


@router.get("/", response_model=List[PolicyResponse])
async def get_policies(
    enabled: bool = None,
    db: Session = Depends(get_db)
):
    """
    Get all policies, optionally filtered by enabled status
    """
    try:
        query = db.query(Policy)
        if enabled is not None:
            query = query.filter(Policy.enabled == enabled)
        policies = query.all()
        return [PolicyResponse.model_validate(p) for p in policies]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching policies: {str(e)}")


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific policy by ID
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return PolicyResponse.model_validate(policy)


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: int,
    policy_update: PolicyUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing policy
    """
    try:
        policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        # Update fields
        update_data = policy_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(policy, field, value)
        
        db.commit()
        db.refresh(policy)
        
        return PolicyResponse.model_validate(policy)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating policy: {str(e)}")


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a policy
    """
    try:
        policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        db.delete(policy)
        db.commit()
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting policy: {str(e)}")

