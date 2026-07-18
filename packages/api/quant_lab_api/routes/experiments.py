"""Experiment history API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from quant_lab_api.database.base import get_db
from quant_lab_api.repositories.experiment_repository import ExperimentRepository

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("")
def list_experiments(
    skip: int = 0,
    limit: int = 50,
    kind: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    repo = ExperimentRepository(db)
    rows = repo.get_all(skip=skip, limit=limit, kind=kind)
    return [
        {
            "id": r.id,
            "name": r.name,
            "kind": r.kind,
            "strategy_name": r.strategy_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "params": r.params,
            "metrics": r.metrics,
            "status": r.status,
        }
        for r in rows
    ]


@router.get("/{experiment_id}")
def get_experiment(experiment_id: int, db: Session = Depends(get_db)) -> dict:
    repo = ExperimentRepository(db)
    r = repo.get_by_id(experiment_id)
    if not r:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {
        "id": r.id,
        "name": r.name,
        "kind": r.kind,
        "strategy_name": r.strategy_name,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "params": r.params,
        "metrics": r.metrics,
        "artifact": r.artifact,
        "status": r.status,
    }


@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: int, db: Session = Depends(get_db)) -> dict:
    repo = ExperimentRepository(db)
    if not repo.delete(experiment_id):
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"message": "deleted"}
