import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.drawing import Drawing
from app.models.project import Project
from app.models.processing_job import ProcessingJob
from app.schemas.processing_job import (
    ProcessingJobResponse,
    ProcessingJobListResponse,
)

from app.worker.tasks import process_drawing

# Adjust this import to your existing authentication dependency.
from app.api.deps import get_current_user


router = APIRouter(tags=["Processing"])


def get_owned_drawing(
    db: Session,
    drawing_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Drawing:
    drawing = db.scalar(
        select(Drawing)
        .join(Project, Drawing.project_id == Project.id)
        .where(
            Drawing.id == drawing_id,
            Project.owner_id == user_id,
        )
    )

    if not drawing:
        raise HTTPException(404, "Drawing not found.")

    return drawing


def enqueue_job(job: ProcessingJob, db: Session):
    """
    Submit a committed job to Celery.

    The database record is committed before dispatch so that
    the worker can load it immediately.
    """

    try:
        process_drawing.apply_async(
            args=[str(job.id)],
            task_id=str(job.id),
        )

    except Exception as exc:
        job.status = "failed"
        job.error_message = (
            f"Unable to submit task to worker: {str(exc)}"
        )

        drawing = db.get(Drawing, job.drawing_id)

        if drawing:
            drawing.status = "failed"

        db.commit()

        raise HTTPException(
            status_code=503,
            detail="Unable to submit processing task. Check Redis and Celery.",
        )


@router.post(
    "/drawings/{drawing_id}/process",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_drawing_processing(
    drawing_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    drawing = get_owned_drawing(
        db,
        drawing_id,
        current_user.id,
    )

    # Prevent duplicate active jobs.
    active_job = db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.drawing_id == drawing_id,
            ProcessingJob.status.in_(["queued", "processing"]),
        )
    )

    if active_job:
        return active_job

    job = ProcessingJob(
        id=uuid.uuid4(),
        drawing_id=drawing.id,
        submitted_by=current_user.id,
        status="queued",
        task_id=None,
        attempt_count=0,
    )

    drawing.status = "queued"

    db.add(job)
    db.commit()
    db.refresh(job)

    # Use the database job UUID as the Celery task UUID.
    job.task_id = str(job.id)
    db.commit()
    db.refresh(job)

    enqueue_job(job, db)

    return job


@router.get(
    "/jobs/{job_id}",
    response_model=ProcessingJobResponse,
)
def get_processing_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(ProcessingJob, job_id)

    if not job:
        raise HTTPException(404, "Processing job not found.")

    get_owned_drawing(
        db,
        job.drawing_id,
        current_user.id,
    )

    return job


@router.get(
    "/jobs/{job_id}/progress",
)
def get_processing_job_progress(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return actual pipeline progress for an owned processing job.
    """

    job = db.get(ProcessingJob, job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Processing job not found.",
        )

    # Verify that the authenticated user owns the drawing's project.
    get_owned_drawing(
        db,
        job.drawing_id,
        current_user.id,
    )

    return {
        "job_id": str(job.id),
        "drawing_id": str(job.drawing_id),
        "status": job.status,
        "attempt_count": job.attempt_count,
        "created_at": (
            job.created_at.isoformat()
            if job.created_at else None
        ),
        "started_at": (
            job.started_at.isoformat()
            if job.started_at else None
        ),
        "completed_at": (
            job.completed_at.isoformat()
            if job.completed_at else None
        ),
        "error_message": job.error_message,
        "stage_progress": job.stage_progress,
    }


@router.get(
    "/drawings/{drawing_id}/jobs",
    response_model=ProcessingJobListResponse,
)
def list_drawing_jobs(
    drawing_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_drawing(
        db,
        drawing_id,
        current_user.id,
    )

    query = (
        select(ProcessingJob)
        .where(ProcessingJob.drawing_id == drawing_id)
        .order_by(ProcessingJob.created_at.desc())
    )

    items = list(db.scalars(query).all())

    total = db.scalar(
        select(func.count())
        .select_from(ProcessingJob)
        .where(ProcessingJob.drawing_id == drawing_id)
    ) or 0

    return ProcessingJobListResponse(
        items=items,
        total=total,
    )


@router.post(
    "/jobs/{job_id}/retry",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_processing_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(ProcessingJob, job_id)

    if not job:
        raise HTTPException(404, "Processing job not found.")

    drawing = get_owned_drawing(
        db,
        job.drawing_id,
        current_user.id,
    )

    if job.status != "failed":
        raise HTTPException(
            status_code=409,
            detail="Only failed jobs can be retried.",
        )

    job.status = "queued"
    job.error_message = None
    job.started_at = None
    job.completed_at = None

    drawing.status = "queued"

    db.commit()
    db.refresh(job)

    enqueue_job(job, db)

    return job
