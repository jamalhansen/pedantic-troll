from typing import List
from pydantic import BaseModel, Field

class Grievance(BaseModel):
    post_reference: str = Field(..., description="Post title or number")
    quote_snippet: str = Field(..., description="The offending text")
    complaint: str = Field(..., description="The pedantic nitpick")
    severity: str = Field(..., description="nit / error / contradiction")

class TrollReport(BaseModel):
    intro: str = Field(..., description="A smug, pedantic introduction from the Troll")
    grievances: List[Grievance]
    verdict: str = Field(..., description="Final condescending verdict")
