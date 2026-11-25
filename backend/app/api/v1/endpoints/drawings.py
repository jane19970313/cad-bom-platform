import hashlib
import uuid
from pathlib import PurePath
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from io import BytesIO

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.models.drawing import Drawing
from app.schemas.drawing import (
    DrawingResponse,
    DrawingListResponse,
)
from app.services.drawing_validator import DrawingValidator
from app.services.storage.factory import get_storage_service

# Adjust this import to match your existing auth module.
from app.api.deps import get_current_user


router = APIRouter(prefix="/drawings", tags=["Drawings"])

MAX_FILE_SIZE = settings.MAX_DXF_FILE_SIZE_MB * 1024 * 1024

def iter_file_chunks(file_stream, chunk_size: int = 1024 * 1024):
    """Read a binary file in fixed-size chunks instead of line by line."""
    try:
        while True:
            chunk = file_stream.read(chunk_size)

            if not chunk:
                break

            yield chunk
    finally:
        file_stream.close()

def get_user_project(
    db: Session,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Project:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == user_id,
        )
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    return project


@router.post(
    "/projects/{project_id}/upload",
    response_model=DrawingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_drawing(
    project_id: uuid.UUID,
    file: Annotated[UploadFile, File(...)],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_project(db, project_id, current_user.id)

    filename = PurePath(file.filename or "").name

    if not filename:
        raise HTTPException(400, "Filename is required.")

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.MAX_DXF_FILE_SIZE_MB} MB limit.",
        )

    validation = DrawingValidator.validate(filename, content)

    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail=validation.message,
        )

    checksum = hashlib.sha256(content).hexdigest()
    drawing_id = uuid.uuid4()

    # Generated key: user/project/drawing-id.dxf
    storage_key = (
        f"{current_user.id}/"
        f"{project_id}/"
        f"{drawing_id}.dxf"
    )

    storage = get_storage_service()

    try:
        storage.save(BytesIO(content), storage_key)

        drawing = Drawing(
            id=drawing_id,
            project_id=project_id,
            uploaded_by=current_user.id,
            original_filename=filename,
            storage_key=storage_key,
            file_size=len(content),
            mime_type="application/dxf",
            checksum_sha256=checksum,
            status="uploaded",
        )

        db.add(drawing)
        db.commit()
        db.refresh(drawing)

        return drawing

    except Exception:
        db.rollback()

        # Avoid leaving an orphaned file if database insertion fails.
        try:
            storage.delete(storage_key)
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail="Unable to save drawing.",
        )


@router.get(
    "/projects/{project_id}",
    response_model=DrawingListResponse,
)
def list_project_drawings(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_project(db, project_id, current_user.id)

    query = (
        select(Drawing)
        .where(Drawing.project_id == project_id)
        .order_by(Drawing.created_at.desc())
    )

    items = list(db.scalars(query).all())

    total = db.scalar(
        select(func.count())
        .select_from(Drawing)
        .where(Drawing.project_id == project_id)
    ) or 0

    return DrawingListResponse(items=items, total=total)


@router.get(
    "/{drawing_id}",
    response_model=DrawingResponse,
)
def get_drawing(
    drawing_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    drawing = db.get(Drawing, drawing_id)

    if not drawing:
        raise HTTPException(404, "Drawing not found.")

    get_user_project(db, drawing.project_id, current_user.id)

    return drawing


@router.get("/{drawing_id}/download")
def download_drawing(
    drawing_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    drawing = db.get(Drawing, drawing_id)

    if not drawing:
        raise HTTPException(404, "Drawing not found.")

    get_user_project(db, drawing.project_id, current_user.id)

    storage = get_storage_service()

    try:
        file_stream = storage.open(drawing.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Drawing file is missing from storage.",
        )

    safe_filename = (
        drawing.original_filename
        .replace('"', "")
        .replace("\r", "")
        .replace("\n", "")
    )

    return StreamingResponse(
        iter_file_chunks(file_stream),
        media_type="application/dxf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{safe_filename}"'
            ),
            "Content-Length": str(drawing.file_size),
        },
    )


@router.delete(
    "/{drawing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_drawing(
    drawing_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    drawing = db.get(Drawing, drawing_id)

    if not drawing:
        raise HTTPException(404, "Drawing not found.")

    get_user_project(db, drawing.project_id, current_user.id)

    storage = get_storage_service()

    try:
        storage.delete(drawing.storage_key)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to delete drawing file.",
        )

    db.delete(drawing)
    db.commit()

    return None