import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.drawing import Drawing
from app.models.processing_job import ProcessingJob
from app.services.processing.runner import run_dxf_pipeline


logger = logging.getLogger(__name__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_stage_progress(db, job_id: UUID, event: dict) -> None:
    """
    Persist one pipeline stage event.

    Each update replaces the JSON value rather than modifying
    a nested JSON object in place, ensuring SQLAlchemy detects it.
    """
    try:
        job = db.get(ProcessingJob, job_id)

        if job is None:
            logger.error(
                "Cannot save progress: processing job %s not found",
                job_id,
            )
            return

        progress = dict(job.stage_progress or {})
        stages = list(progress.get("stages", []))

        stage_name = event["name"]

        # Find an existing entry for this stage.
        stage_index = next(
            (
                index
                for index, stage in enumerate(stages)
                if stage.get("name") == stage_name
            ),
            None,
        )

        # Store stage data without the event discriminator.
        stage_data = {
            key: value
            for key, value in event.items()
            if key != "event"
        }

        if stage_index is None:
            stages.append(stage_data)
        else:
            stages[stage_index] = stage_data

        overall_status = (
            "failed"
            if event["status"] == "failed"
            else "processing"
        )

        progress.update({
            "current_stage": (
                stage_name
                if event["status"] in ("running", "failed")
                else stage_name
            ),
            "overall_status": overall_status,
            "stages": stages,
            "updated_at": utc_now(),
        })

        job.stage_progress = progress

        db.commit()

    except Exception:
        db.rollback()

        # Progress persistence must not interrupt DXF analysis.
        logger.exception(
            "Failed to save pipeline progress for job %s",
            job_id,
        )


@celery_app.task(
    bind=True,
    name="app.worker.tasks.process_drawing",
)
def process_drawing(self, job_id: str):
    """
    Execute one drawing processing job.

    job_id is a UUID string.
    """

    db = SessionLocal()

    try:
        parsed_job_id = UUID(job_id)

        job = db.execute(
            select(ProcessingJob)
            .where(ProcessingJob.id == parsed_job_id)
            .with_for_update()
        ).scalar_one_or_none()

        if job is None:
            return {
                "status": "not_found",
                "job_id": job_id,
            }

        # Ignore duplicate deliveries for terminal jobs.
        if job.status in ("completed", "failed"):
            return {
                "status": job.status,
                "job_id": job_id,
            }

        drawing = db.get(Drawing, job.drawing_id)

        if drawing is None:
            job.status = "failed"
            job.error_message = "Drawing record not found."
            job.completed_at = datetime.now(timezone.utc)

            job.stage_progress = {
                "current_stage": None,
                "overall_status": "failed",
                "stages": [],
                "updated_at": utc_now(),
                "error": job.error_message,
            }

            db.commit()

            return {
                "status": "failed",
                "job_id": job_id,
                "error": job.error_message,
            }

        # Mark job as processing.
        job.status = "processing"
        job.attempt_count += 1
        job.started_at = datetime.now(timezone.utc)
        job.completed_at = None
        job.error_message = None

        drawing.status = "processing"

        job.stage_progress = {
            "current_stage": None,
            "overall_status": "processing",
            "stages": [],
            "updated_at": utc_now(),
        }

        db.commit()

        # The DXF engine calls this whenever a stage changes state.
        def progress_callback(event: dict) -> None:
            save_stage_progress(
                db=db,
                job_id=parsed_job_id,
                event=event,
            )

        try:
            result = run_dxf_pipeline(
                drawing_id=drawing.id,
                storage_key=drawing.storage_key,
                progress_callback=progress_callback,
            )

            job.result_storage_key = result["result_storage_key"]
            job.result_summary = result["summary"]

            job.status = "completed"
            job.error_message = None

            drawing.status = "completed"

            progress = dict(job.stage_progress or {})
            progress.update({
                "current_stage": None,
                "overall_status": "completed",
                "updated_at": utc_now(),
            })
            job.stage_progress = progress

        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)[:5000]

            drawing.status = "failed"

            progress = dict(job.stage_progress or {})
            progress.update({
                "overall_status": "failed",
                "updated_at": utc_now(),
                "error": job.error_message,
            })
            job.stage_progress = progress

            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            # Keep Celery's task result consistent with the failure.
            raise

        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "status": "completed",
            "job_id": job_id,
            "drawing_id": str(drawing.id),
            "result": job.result_summary,
        }

    finally:
        db.close()