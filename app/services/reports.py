from __future__ import annotations

from app.models import IngestionRun


def run_summary(run: IngestionRun) -> str:
    return (
        f"Run {run.id}: {run.status}; documents={run.documents_inserted}/{run.documents_found}; "
        f"chunks={run.chunks_inserted}; duplicates={run.duplicates_skipped}"
    )

