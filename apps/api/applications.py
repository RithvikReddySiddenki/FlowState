"""Owned application CRUD. Multi-record changes commit as one transaction."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.dependencies import current_user
from apps.api.models import Application, ApplicationStatusHistory, User
from apps.api.schemas import (
    ApplicationResponse, CreateApplication, HistoryResponse, Stage, UpdateApplication,
)

router = APIRouter(prefix="/applications", tags=["applications"])


def owned(database: Session, user: User, application_id: int) -> Application:
    application = database.scalar(select(Application).where(
        Application.id == application_id, Application.user_id == user.id
    ))
    if application is None:
        raise HTTPException(404, "Application not found")
    return application


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    q: str = Query("", max_length=255),
    status: Stage | None = None,
    action_required: bool | None = None,
    sort: str = Query("updated_at", pattern="^(updated_at|created_at|company|role)$"),
    direction: str = Query("desc", pattern="^(asc|desc)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    database: Session = Depends(get_db), user: User = Depends(current_user),
):
    query = select(Application).where(Application.user_id == user.id)
    if q.strip():
        # Escape LIKE metacharacters so search terms are literal substrings.
        value = q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(or_(
            func.lower(Application.company).like(f"%{value}%", escape="\\"),
            func.lower(Application.role).like(f"%{value}%", escape="\\"),
        ))
    if status is not None:
        query = query.where(Application.current_status == status.value)
    if action_required is not None:
        query = query.where(Application.action_required == action_required)
    column = getattr(Application, sort)
    order = column.asc() if direction == "asc" else column.desc()
    return database.scalars(query.order_by(order, Application.id).offset(offset).limit(limit)).all()


@router.post("", response_model=ApplicationResponse, status_code=201)
def create_application(
    payload: CreateApplication, database: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    application = Application(user_id=user.id, **payload.model_dump())
    database.add(application)
    database.flush()
    database.add(ApplicationStatusHistory(
        application_id=application.id, current_status=payload.current_status.value,
        source="manual",
    ))
    database.commit()
    database.refresh(application)
    return application


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int, database: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return owned(database, user, application_id)


@router.get("/{application_id}/history", response_model=list[HistoryResponse])
def get_history(
    application_id: int, database: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    application = owned(database, user, application_id)
    return database.scalars(select(ApplicationStatusHistory).where(
        ApplicationStatusHistory.application_id == application.id
    ).order_by(ApplicationStatusHistory.created_at, ApplicationStatusHistory.id)).all()


@router.patch("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int, payload: UpdateApplication,
    database: Session = Depends(get_db), user: User = Depends(current_user),
):
    application = owned(database, user, application_id)
    changes = payload.model_dump(exclude_unset=True)
    new_status = changes.get("current_status")
    if new_status is not None and new_status != application.current_status:
        database.add(ApplicationStatusHistory(
            application_id=application.id, previous_status=application.current_status,
            current_status=new_status.value, source="manual",
        ))
    for field, value in changes.items():
        setattr(application, field, value)
    database.commit()
    database.refresh(application)
    return application


@router.delete("/{application_id}", status_code=204)
def delete_application(
    application_id: int, database: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    application = owned(database, user, application_id)
    database.execute(delete(ApplicationStatusHistory).where(
        ApplicationStatusHistory.application_id == application.id
    ))
    database.delete(application)
    database.commit()
    return Response(status_code=204)
