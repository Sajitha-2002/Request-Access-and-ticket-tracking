from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import RequestType, User
from ..schemas import RequestTypeCreate, RequestTypeOut, RequestTypeUpdate
from ..auth import get_current_user, require_admin

router = APIRouter(prefix="/api/request-types", tags=["Request Types"])


@router.get("/", response_model=List[RequestTypeOut])
def list_request_types(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(RequestType).filter(RequestType.is_active == True).all()


@router.get("/all", response_model=List[RequestTypeOut])
def list_all_request_types(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return db.query(RequestType).all()


@router.post("/", response_model=RequestTypeOut, status_code=201)
def create_request_type(
    payload: RequestTypeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(RequestType).filter(RequestType.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Request type with this name already exists")
    rt = RequestType(**payload.model_dump())
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


@router.put("/{rt_id}", response_model=RequestTypeOut)
def update_request_type(
    rt_id: int,
    payload: RequestTypeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rt = db.query(RequestType).filter(RequestType.id == rt_id).first()
    if not rt:
        raise HTTPException(status_code=404, detail="Request type not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(rt, field, value)
    db.commit()
    db.refresh(rt)
    return rt
