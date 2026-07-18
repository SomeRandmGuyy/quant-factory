"""Repository for experiment records."""

from typing import Optional, List
from sqlalchemy.orm import Session
from quant_lab_api.database.models import Experiment


class ExperimentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        kind: str,
        strategy_name: str,
        params: dict | None = None,
        metrics: dict | None = None,
        artifact: dict | None = None,
        name: str | None = None,
        status: str = "completed",
    ) -> Experiment:
        exp = Experiment(
            name=name,
            kind=kind,
            strategy_name=strategy_name,
            params=params,
            metrics=metrics,
            artifact=artifact,
            status=status,
        )
        self.db.add(exp)
        self.db.commit()
        self.db.refresh(exp)
        return exp

    def get_by_id(self, experiment_id: int) -> Optional[Experiment]:
        return self.db.query(Experiment).filter(Experiment.id == experiment_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        kind: Optional[str] = None,
    ) -> List[Experiment]:
        q = self.db.query(Experiment)
        if kind:
            q = q.filter(Experiment.kind == kind)
        return q.order_by(Experiment.created_at.desc()).offset(skip).limit(limit).all()

    def delete(self, experiment_id: int) -> bool:
        exp = self.get_by_id(experiment_id)
        if not exp:
            return False
        self.db.delete(exp)
        self.db.commit()
        return True
