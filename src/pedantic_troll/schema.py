from datetime import datetime

from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class Grievance(BaseModel):
    post_reference: str = Field(..., description="Post title or number")
    quote_snippet: str = Field(..., description="The offending text")
    complaint: str = Field(..., description="The pedantic nitpick")
    severity: str = Field(..., description="nit / error / contradiction")


class TrollReport(BaseModel):
    intro: str = Field(..., description="A smug, pedantic introduction from the Troll")
    grievances: list[Grievance]
    verdict: str = Field(..., description="Final condescending verdict")


class TrollRecord(SQLModel, table=True):
    """Database record for Troll grievances."""
    
    id: int | None = SQLField(default=None, primary_key=True)
    timestamp: datetime = SQLField(default_factory=datetime.now)
    series_premise: str
    source_location: str # Parent directory of drafts
    
    grievance_count: int
    error_count: int
    contradiction_count: int
    nit_count: int
    
    intro: str
    verdict: str
    all_grievances_json: str # Store as serialized JSON for simplicity
