import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_admin
from app.db.session import get_db
from app.models.print_job import PaymentStatus, PrintJob, PrintStatus
from app.models.user import User
from app.schemas.print_job import (
    PrintJobAdminUpdate,
    PrintJobPaginationResponse,
    PrintJobResponse,
)

router = APIRouter(
    prefix="/admin/prints",
    tags=["Admin - Print Queue Management"],
    dependencies=[Depends(get_current_active_admin)],
)


@router.get(
    "/queue",
    response_model=PrintJobPaginationResponse,
    summary="List all print jobs in queue with filters and search",
)
def get_print_queue(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[PrintStatus] = Query(None, alias="status"),
    payment_status_filter: Optional[PaymentStatus] = Query(None, alias="payment_status"),
    user_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, description="Search in print title or user details"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """Retrieve all print jobs across all users with filtering, searching, and pagination."""
    query = db.query(PrintJob).join(User, PrintJob.user_id == User.id)

    if status_filter:
        query = query.filter(PrintJob.status == status_filter.value)

    if payment_status_filter:
        query = query.filter(PrintJob.payment_status == payment_status_filter.value)

    if user_id is not None:
        query = query.filter(PrintJob.user_id == user_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                PrintJob.title.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern),
            )
        )

    total = query.count()
    items = query.order_by(PrintJob.created_at.asc()).offset(skip).limit(limit).all()

    return PrintJobPaginationResponse(
        total=total,
        items=items,
        limit=limit,
        skip=skip,
    )


@router.patch(
    "/{print_id}",
    response_model=PrintJobResponse,
    summary="Update print job status, payment status, or correct price",
)
def update_print_job(
    print_id: int,
    payload: PrintJobAdminUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """Update a print job's status, payment status, notes, or override/correct its final price."""
    job = db.query(PrintJob).filter(PrintJob.id == print_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Print job not found",
        )

    if payload.final_price is not None:
        job.final_price = payload.final_price

    if payload.status is not None:
        job.status = payload.status.value

    if payload.payment_status is not None:
        job.payment_status = payload.payment_status.value

    if payload.notes is not None:
        job.notes = payload.notes

    db.commit()
    db.refresh(job)
    return job


@router.delete(
    "/{print_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a print job and associated file",
)
def delete_print_job(
    print_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    """Delete a print job from the queue and remove the stored model file from disk."""
    job = db.query(PrintJob).filter(PrintJob.id == print_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Print job not found",
        )

    # Delete physical file if exists
    if job.file_path and os.path.exists(job.file_path):
        try:
            os.remove(job.file_path)
        except OSError:
            pass

    db.delete(job)
    db.commit()
    return None
