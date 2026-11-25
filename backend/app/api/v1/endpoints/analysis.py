import json
import logging

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.processing_job import ProcessingJob
from app.models.drawing import Drawing
from app.models.project import Project
from app.services.storage.factory import get_storage_service
from app.api.deps import get_current_user


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/jobs/{job_id}/result")
def get_analysis_result(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = (
        db.query(ProcessingJob)
        .join(
            Drawing,
            ProcessingJob.drawing_id == Drawing.id,
        )
        .join(
            Project,
            Drawing.project_id == Project.id,
        )
        .filter(
            ProcessingJob.id == job_id,
            Project.owner_id == current_user.id,
        )
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Processing job not found",
        )

    if job.status != "completed" or not job.result_storage_key:
        raise HTTPException(
            status_code=409,
            detail="Analysis result is not available",
        )

    storage = get_storage_service()

    try:
        with storage.open(job.result_storage_key) as file:
            result = json.load(file)

    except FileNotFoundError:
        logger.exception(
            "Analysis artifact not found for job %s",
            job_id,
        )
        raise HTTPException(
            status_code=404,
            detail="Analysis result artifact not found",
        )

    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.exception(
            "Invalid analysis artifact for job %s",
            job_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Analysis result artifact is invalid",
        )

    print(
        f"[DEBUG] API geometry_elements: "
        f"{len(result.get('geometry_elements', []))}",
        flush=True
    )
    return JSONResponse(content=result)
