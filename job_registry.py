from typing import Dict, Literal
from pydantic import BaseModel, Field   

class JobStatus(BaseModel):
    job_id: str
    state: Literal["pending", "running", "finished", "error"]
    message: str | None = None
    panel_progress: Dict[str, int] = Field(
        default_factory=lambda: {"macro": 0, "micro": 0, "price": 0, "strategy": 0}
    )

    log: list[str] = Field(default_factory=list)

jobs: Dict[str, JobStatus] = {}
