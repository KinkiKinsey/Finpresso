# src/api/main.py
from __future__ import annotations
import pathlib, uuid, json
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Dict, List, Any, Optional
from job_registry import jobs, JobStatus
from Finpresso_Agent import run_analysis, validate_ticker
from .verify_api import router as verify_router
import threading

DATA_DIR = pathlib.Path("ALL_Files/Rating_Json")
GRAPH_DIR = pathlib.Path("ALL_Files/Graph")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 添加并发控制
MAX_CONCURRENT_USERS = 4
current_active_jobs = 0
jobs_lock = threading.Lock()

app = FastAPI(title="Finpresso API")

@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

class ErrorResp(BaseModel):
    error: str
    detail: str

# ---------------- 创建任务 ----------------
@app.post("/api/v1/analysis", response_model=JobStatus, responses={400: {"model": ErrorResp}, 503: {"model": ErrorResp}})
def create_job(req: AnalyzeReq, bg: BackgroundTasks):
    global current_active_jobs
    
    # 检查并发限制
    with jobs_lock:
        if current_active_jobs >= MAX_CONCURRENT_USERS:
            raise HTTPException(
                status_code=503,
                detail=f"Server is at capacity. Maximum {MAX_CONCURRENT_USERS} concurrent analyses allowed. Please try again in a few moments."
            )
        current_active_jobs += 1
    
    ticker = req.ticker.upper()
    
    # Validate ticker before creating job
    if not validate_ticker(ticker):
        with jobs_lock:
            current_active_jobs -= 1  # 释放槽位
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid ticker symbol: {ticker}. Please verify the ticker exists and try again."
        )
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobStatus(job_id=job_id, state="pending")
    bg.add_task(_worker_with_cleanup, ticker, job_id)
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

# ---------------- 获取服务器状态 ----------------
@app.get("/api/v1/server/status")
def get_server_status():
    """获取服务器当前状态"""
    with jobs_lock:
        return {
            "active_jobs": current_active_jobs,
            "max_capacity": MAX_CONCURRENT_USERS,
            "available_slots": MAX_CONCURRENT_USERS - current_active_jobs
        }

# ---------------- 带清理的后台线程 ----------------
def _worker_with_cleanup(ticker: str, job_id: str):
    """包装原有的 worker，添加清理逻辑"""
    global current_active_jobs
    try:
        _worker(ticker, job_id)
    finally:
        # 无论成功还是失败，都要释放槽位
        with jobs_lock:
            current_active_jobs -= 1

# ---------------- 原有的后台线程 ----------------
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

app.include_router(verify_router, prefix="/api/v1/verify")