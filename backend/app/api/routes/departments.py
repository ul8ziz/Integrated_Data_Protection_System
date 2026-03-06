"""
API routes for departments management (Admin only) - MongoDB version
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.schemas.departments import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.models_mongo.departments import Department
from app.models_mongo.users import User
from app.api.dependencies import get_current_admin
from app.utils.datetime_utils import get_current_time

router = APIRouter(prefix="/api/departments", tags=["Departments"])


@router.get("/list", response_model=List[dict])
async def list_departments_public():
    """
    List department id and name only (no auth). Used for registration form.
    """
    departments = await Department.find({}).sort("name").to_list()
    return [{"id": str(d.id), "name": d.name} for d in departments]


@router.get("/", response_model=List[DepartmentResponse])
async def get_departments(
    current_user: User = Depends(get_current_admin)
):
    """Get all departments (Admin only)."""
    departments = await Department.find({}).sort("name").to_list()
    return [
        DepartmentResponse(
            id=str(d.id),
            name=d.name,
            description=d.description,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in departments
    ]


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: str,
    current_user: User = Depends(get_current_admin)
):
    """Get a department by ID (Admin only)."""
    try:
        department = await Department.get(department_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    return DepartmentResponse(
        id=str(department.id),
        name=department.name,
        description=department.description,
        created_at=department.created_at,
        updated_at=department.updated_at,
    )


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(get_current_admin)
):
    """Create a new department (Admin only)."""
    existing = await Department.find_one({"name": data.name})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department with this name already exists"
        )
    department = Department(
        name=data.name,
        description=data.description,
        created_at=get_current_time(),
    )
    await department.insert()
    return DepartmentResponse(
        id=str(department.id),
        name=department.name,
        description=department.description,
        created_at=department.created_at,
        updated_at=department.updated_at,
    )


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: str,
    data: DepartmentUpdate,
    current_user: User = Depends(get_current_admin)
):
    """Update a department (Admin only)."""
    try:
        department = await Department.get(department_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    if data.name is not None:
        existing = await Department.find_one({"name": data.name})
        if existing and str(existing.id) != department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department with this name already exists"
            )
        department.name = data.name
    if data.description is not None:
        department.description = data.description
    department.updated_at = get_current_time()
    await department.save()
    return DepartmentResponse(
        id=str(department.id),
        name=department.name,
        description=department.description,
        created_at=department.created_at,
        updated_at=department.updated_at,
    )


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: str,
    current_user: User = Depends(get_current_admin)
):
    """Delete a department (Admin only). Fails if any users are assigned to it."""
    try:
        department = await Department.get(department_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    count = await User.find({"department_id": department_id}).count()
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete department: it has users assigned"
        )
    await department.delete()
    return None
