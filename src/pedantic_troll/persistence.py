import json
from pathlib import Path
from sqlmodel import Session, SQLModel, create_engine
from local_first_common.db import CONTENT_QUALITY_DB_PATH
from .schema import TrollReport, TrollRecord


def get_engine(db_path: Path = CONTENT_QUALITY_DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_url = f"sqlite:///{db_path}"
    engine = create_engine(sqlite_url)
    SQLModel.metadata.create_all(engine)
    return engine


def save_troll_report(
    report: TrollReport, 
    source_location: str, 
    premise: str,
    db_path: Path = CONTENT_QUALITY_DB_PATH
):
    engine = get_engine(db_path)
    
    error_count = sum(1 for g in report.grievances if g.severity == "error")
    contradiction_count = sum(1 for g in report.grievances if g.severity == "contradiction")
    nit_count = sum(1 for g in report.grievances if g.severity == "nit")
    
    # Simple JSON serialization for grievances
    grievances_json = json.dumps([g.model_dump() for g in report.grievances])
    
    with Session(engine) as session:
        record = TrollRecord(
            series_premise=premise,
            source_location=source_location,
            grievance_count=len(report.grievances),
            error_count=error_count,
            contradiction_count=contradiction_count,
            nit_count=nit_count,
            intro=report.intro,
            verdict=report.verdict,
            all_grievances_json=grievances_json
        )
        session.add(record)
        session.commit()
