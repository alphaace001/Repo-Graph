"""
Indexing API Router - Endpoints for repository indexing with job tracking.
"""

import os
import uuid
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from logger import setup_logger
from MCP.Indexer.Tools.index_repo import ingest_all_files

# Load environment variables
load_dotenv()
BASE_PATH = os.getenv("BASE_PATH", "D:\\KGassign\\fastapi")

# Setup logger
logger = setup_logger(__name__)

# Create router
router = APIRouter(prefix="/api/index", tags=["Indexing"])


class IndexMode(str, Enum):
    """Indexing mode enumeration."""
    FULL = "full"
    # INCREMENTAL = "incremental"


class JobStatusEnum(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IndexRequest(BaseModel):
    """Request model for triggering indexing."""
    path: Optional[str] = Field(
        default="",
        description="Subdirectory path within the base path (optional, defaults to root)"
    )
    mode: IndexMode = Field(
        default=IndexMode.FULL,
        description="Indexing mode: 'full' for complete re-index, 'incremental' for changes only"
    )


class IndexResponse(BaseModel):
    """Response model for index trigger endpoint."""
    job_id: str
    status: JobStatusEnum
    message: str


class JobStatus(BaseModel):
    """Detailed job status model."""
    job_id: str
    status: JobStatusEnum
    mode: IndexMode
    path: str
    # progress: Optional[JobProgress] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

# Thread-safe job storage
_jobs: dict[str, JobStatus] = {}
_jobs_lock = threading.Lock()


def get_job(job_id: str) -> Optional[JobStatus]:
    """Get job by ID."""
    with _jobs_lock:
        return _jobs.get(job_id)


def update_job(job_id: str, **kwargs):
    """Update job fields."""
    with _jobs_lock:
        if job_id in _jobs:
            job = _jobs[job_id]
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)


def create_job(path: str, mode: IndexMode) -> JobStatus:
    """Create a new job entry."""
    job_id = str(uuid.uuid4())
    job = JobStatus(
        job_id=job_id,
        status=JobStatusEnum.PENDING,
        mode=mode,
        path=path,
        started_at=datetime.now()
    )
    with _jobs_lock:
        _jobs[job_id] = job
    return job


def run_indexing_job(job_id: str, full_path: str, mode: IndexMode):
    """Background worker to run indexing."""
    try:
        update_job(job_id, status=JobStatusEnum.RUNNING)
        logger.info(f"Starting indexing job {job_id} with mode={mode} path={full_path}")

        if mode == IndexMode.FULL:
            # Full indexing: process all files
            ingest_all_files(full_path)

        update_job(
            job_id,
            status=JobStatusEnum.COMPLETED,
            completed_at=datetime.now()
        )
        logger.info(f"Indexing job {job_id} completed successfully")

    except Exception as e:
        error_msg = str(e)
        update_job(
            job_id,
            status=JobStatusEnum.FAILED,
            completed_at=datetime.now(),
            error=error_msg
        )
        logger.error(f"Indexing job {job_id} failed: {error_msg}")


@router.post("/index", response_model=IndexResponse)
async def trigger_index(request: IndexRequest):
    """
    Trigger repository indexing.

    Starts an async indexing job and returns a job ID for status tracking.
    Supports both 'full' and 'incremental' indexing modes.
    """
    # Construct full path
    path_clean = request.path.lstrip("/\\") if request.path else ""
    if path_clean:
        full_path = str(Path(BASE_PATH) / path_clean)
    else:
        full_path = BASE_PATH

    # Validate path exists
    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=400,
            detail=f"Path does not exist: {full_path}"
        )

    # Create job entry
    job = create_job(path=request.path or "", mode=request.mode)

    # Start background thread for indexing
    thread = threading.Thread(
        target=run_indexing_job,
        args=(job.job_id, full_path, request.mode),
        daemon=True
    )
    thread.start()

    logger.info(f"Indexing job {job.job_id} queued with mode={request.mode}")

    return IndexResponse(
        job_id=job.job_id,
        status=JobStatusEnum.PENDING,
        message=f"Indexing job started with mode '{request.mode.value}'"
    )


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_index_status(job_id: str):
    """
    Get the status of an indexing job.

    Returns detailed information about the job including its current status,
    progress, timestamps, and any errors that occurred.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )
    return job
