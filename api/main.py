# src/api/main.py
from __future__ import annotations
import pathlib, uuid, json
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Dict, List, Any, Optional

from job_registry import jobs, JobStatus
from Finpresso_Agent import run_analysis

DATA_DIR  = pathlib.Path("ALL_Files/Rating_Json")
GRAPH_DIR = pathlib.Path("ALL_Files/Graph")
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Finpresso API")

@app.get("/health", include_in_schema=False)
async def _health_check():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/graphs", StaticFiles(directory=GRAPH_DIR), name="graphs")


class AnalyzeReq(BaseModel):
    ticker: str


class StatusResp(BaseModel):
    job_id: str
    state: Literal["pending", "running", "finished", "error"]
    message: Optional[str]
    panel_progress: Dict[str, int]
    panel_data: Dict[str, Any]
    new_logs: List[str]
    next_cursor: int


# ---------------- 创建任务 ----------------

@app.post("/api/v1/analysis", response_model=JobStatus)
def create_job(req: AnalyzeReq, bg: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobStatus(job_id=job_id, state="pending")
    bg.add_task(_worker, req.ticker.upper(), job_id)
    return jobs[job_id]


# ---------------- 轮询状态 ----------------

@app.get("/api/v1/analysis/{job_id}/status", response_model=StatusResp)
def job_status(job_id: str, cursor: int = 0):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    st = jobs[job_id]

    # 拿到新日志
    new_logs = st.log[cursor:]
    next_cursor = cursor + len(new_logs)

    # 把 JobStatus 所有字段 dump 出来，其中就包含了 panel_data
    payload = st.model_dump()
    # 如果不想让 log 也返回，可以：
    payload.pop("log", None)

    # 再拼上 new_logs 和 next_cursor
    payload.update({
        "new_logs": new_logs,
        "next_cursor": next_cursor
    })

    return payload


# ---------------- 结果 ----------------

@app.get("/api/v1/analysis/{job_id}/result")
def job_result(job_id: str):
    f = DATA_DIR / f"{job_id}.json"
    if not f.exists():
        raise HTTPException(404, "Result not ready")
    return json.loads(f.read_text())


# ---------------- 后台线程 ----------------

def _worker(ticker: str, job_id: str):
    try:
        jobs[job_id].state = "running"
        jobs[job_id].message = "Initializing…"

        # 执行分析，拿到完整的 JSON 结构
        full_result = run_analysis(ticker, job_id=job_id)

        # 把整个 JSON 持久化到文件，而不是只截取部分字段
        out_path = DATA_DIR / f"{job_id}.json"
        out_path.write_text(
            json.dumps(full_result, ensure_ascii=False)
        )

        # 标记任务完成
        jobs[job_id].state = "finished"
        jobs[job_id].message = "Analysis completed"
        for k in jobs[job_id].panel_progress:
            jobs[job_id].panel_progress[k] = 100

    except Exception as e:
        jobs[job_id].state = "error"
        jobs[job_id].message = str(e)