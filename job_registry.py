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
    # 新增：存储各阶段的中间输出（跑完后填入）
    panel_data: Dict[str, dict] = Field(
        default_factory=lambda: {"macro": {}, "micro": {}, "price": {}, "strategy": {}}
   )

jobs: Dict[str, JobStatus] = {}
