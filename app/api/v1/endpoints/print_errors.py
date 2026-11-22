from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.print_error import PrintError
from app.models.print_job import PrintJob
from app.models.user import User, UserRole
from app.schemas.print_error import PrintErrorCreate, PrintErrorResponse

router = APIRouter(prefix="/print-errors", tags=["Print Errors"])


@router.post(
    "",
    response_model=PrintErrorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a failed print",
)
def create_print_error(
    payload: PrintErrorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(PrintJob).filter(PrintJob.id == payload.job_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Print job not found",
        )

    if job.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to report an error for this print job",
        )

    print_error = PrintError(
        job_id=job.id,
        error_type=payload.error_type.value,
        description=payload.description,
        reported_by_user_id=current_user.id,
    )
    job.status = "FAILED"
    db.add(print_error)
    db.commit()
    db.refresh(print_error)
    return print_error


@router.get(
    "",
    response_model=List[PrintErrorResponse],
    summary="List reported print errors",
)
def list_print_errors(
    job_id: Optional[int] = Query(None, gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(PrintError)
    if current_user.role != UserRole.ADMIN.value:
        query = query.join(PrintJob).filter(PrintJob.user_id == current_user.id)
    if job_id is not None:
        query = query.filter(PrintError.job_id == job_id)

    return query.order_by(PrintError.created_at.desc(), PrintError.id.desc()).all()
