import os
import shutil
import uuid
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.pricing import calculate_estimated_price
from app.db.session import get_db
from app.models.print_job import PaymentStatus, PrintJob, PrintStatus
from app.models.user import User, UserRole
from app.schemas.print_job import (
    PrintJobPaginationResponse,
    PrintJobResponse,
    PrintPriceEstimateResponse,
)

router = APIRouter(prefix="/prints", tags=["Print Orders"])


@router.get(
    "/estimate",
    response_model=PrintPriceEstimateResponse,
    summary="Estimate price based on weight and time",
)
def estimate_price(
    estimated_weight_g: float = Query(..., ge=0, description="Estimated filament weight in grams"),
    estimated_time_hours: float = Query(..., ge=0, description="Estimated print duration in hours"),
):
    """Calculate an estimated print price using the server-side pricing formula."""
    estimated_price = calculate_estimated_price(
        estimated_weight_g=estimated_weight_g,
        estimated_time_hours=estimated_time_hours,
    )
    return PrintPriceEstimateResponse(
        estimated_weight_g=estimated_weight_g,
        estimated_time_hours=estimated_time_hours,
        estimated_price=estimated_price,
        currency="PLN",
    )


@router.post(
    "",
    response_model=PrintJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a 3D model and create a print order",
)
def create_print_order(
    title: str = Form(..., min_length=1, max_length=150),
    notes: Optional[str] = Form(None, max_length=1000),
    material: str = Form("PLA", max_length=50),
    estimated_weight_g: float = Form(..., ge=0),
    estimated_time_hours: float = Form(..., ge=0),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a 3D model file and submit a new print job to the queue."""
    # 1. Validate file extension
    filename = file.filename or "model.stl"
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    if ext_lower not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' is not allowed. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    # 2. Save file to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_filename = f"{uuid.uuid4().hex}_{os.path.basename(filename)}"
    destination_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    file_size_bytes = 0
    with open(destination_path, "wb") as buffer:
        while chunk := file.file.read(1024 * 1024):  # 1MB chunks
            file_size_bytes += len(chunk)
            if file_size_bytes > settings.MAX_FILE_SIZE_BYTES:
                buffer.close()
                if os.path.exists(destination_path):
                    os.remove(destination_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
                )
            buffer.write(chunk)

    # 3. Calculate estimated price server-side
    estimated_price = calculate_estimated_price(
        estimated_weight_g=estimated_weight_g,
        estimated_time_hours=estimated_time_hours,
    )

    # 4. Save PrintJob record
    print_job = PrintJob(
        title=title,
        notes=notes,
        material=material,
        file_path=destination_path,
        original_filename=filename,
        file_size_bytes=file_size_bytes,
        estimated_weight_g=estimated_weight_g,
        estimated_time_hours=estimated_time_hours,
        estimated_price=estimated_price,
        final_price=None,
        currency="PLN",
        status=PrintStatus.PENDING_REVIEW.value,
        payment_status=PaymentStatus.PENDING.value,
        user_id=current_user.id,
    )
    db.add(print_job)
    db.commit()
    db.refresh(print_job)

    return print_job


@router.get(
    "/my",
    response_model=PrintJobPaginationResponse,
    summary="List all print jobs ordered by current user",
)
def list_my_print_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[PrintStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all print orders placed by the currently authenticated user."""
    query = db.query(PrintJob).filter(PrintJob.user_id == current_user.id)

    if status_filter:
        query = query.filter(PrintJob.status == status_filter.value)

    total = query.count()
    items = query.order_by(PrintJob.created_at.desc()).offset(skip).limit(limit).all()

    return PrintJobPaginationResponse(
        total=total,
        items=items,
        limit=limit,
        skip=skip,
    )


@router.get(
    "/{print_id}",
    response_model=PrintJobResponse,
    summary="Get details of a print job",
)
def get_print_job(
    print_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get details of a specific print job. Accessible by the job owner or an administrator."""
    job = db.query(PrintJob).filter(PrintJob.id == print_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Print job not found",
        )

    if job.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this print job",
        )

    return job


@router.get(
    "/{print_id}/file",
    summary="Download the print file",
)
def download_print_file(
    print_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the uploaded 3D model file. Accessible by the job owner or an administrator."""
    job = db.query(PrintJob).filter(PrintJob.id == print_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Print job not found",
        )

    if job.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to download this file",
        )

    if not os.path.exists(job.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage server",
        )

    return FileResponse(
        path=job.file_path,
        filename=job.original_filename,
        media_type="application/octet-stream",
    )


@router.delete(
    "/{print_id}",
    response_model=PrintJobResponse,
    summary="Cancel a print job (if still in pending_review)",
)
def cancel_print_job(
    print_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a print order. Users can only cancel orders that are still pending review."""
    job = db.query(PrintJob).filter(PrintJob.id == print_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Print job not found",
        )

    if job.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel this print job",
        )

    if job.status != PrintStatus.PENDING_REVIEW.value and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a job with status '{job.status}'. Please contact an administrator.",
        )

    job.status = PrintStatus.CANCELLED.value
    db.commit()
    db.refresh(job)
    return job
