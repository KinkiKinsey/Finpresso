# src/api/main.py
from __future__ import annotations
import pathlib, uuid, json, os, re
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Literal, Dict, List, Any, Optional
from job_registry import jobs, JobStatus
from Finpresso_Agent import run_analysis, validate_ticker
from .verify_api import router as verify_router
import threading

DATA_DIR = pathlib.Path("ALL_Files/Rating_Json")
GRAPH_DIR = pathlib.Path("ALL_Files/Graph")  # This is the parent directory containing ticker folders
DATA_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_DIR.mkdir(parents=True, exist_ok=True)  # Ensure the parent directory exists

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

# Add a route to check if a graph file exists
@app.get("/api/v1/check-graph/{path:path}")
async def check_graph_exists(path: str):
    full_path = GRAPH_DIR / path
    exists = os.path.isfile(full_path)
    return {"exists": exists, "path": str(full_path)}

class AnalyzeReq(BaseModel):
    ticker: str

    @validator('ticker')
    def validate_ticker_format(cls, v):
        # Remove all whitespace and ensure uppercase
        cleaned = ''.join(v.split()).upper()
        if not cleaned:
            raise ValueError('Ticker symbol cannot be empty')
        # Basic format validation
        if any(c in cleaned for c in [',', ';', '|']):
            raise ValueError('Invalid ticker symbol format')
        return cleaned

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
    
    # Check concurrent limit
    with jobs_lock:
        if current_active_jobs >= MAX_CONCURRENT_USERS:
            raise HTTPException(
                status_code=503,
                detail=f"Server is at capacity. Maximum {MAX_CONCURRENT_USERS} concurrent analyses allowed. Please try again in a few moments."
            )
        current_active_jobs += 1
    
    # The ticker is already cleaned by the validator
    ticker = req.ticker
    
    # Validate ticker before creating job
    if not validate_ticker(ticker):
        with jobs_lock:
            current_active_jobs -= 1  # Release slot
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid ticker symbol: {ticker}. Please verify the ticker exists and try again."
        )
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobStatus(job_id=job_id, state="pending")
    bg.add_task(_worker_with_cleanup, ticker, job_id)
    return jobs[job_id]

# ---------------- 轮询状态 ----------------
def transform_price_data(price_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform price data from backend format to frontend format."""
    if not price_data:
        return {}
    
    # 获取 ticker
    ticker = None
    
    # 从各种可能的地方尝试获取 ticker
    # 1. 从 job context 获取
    for job_id, job in jobs.items():
        if hasattr(job, 'panel_data') and job.panel_data.get('macro', {}).get('ticker'):
            ticker = job.panel_data['macro']['ticker']
            break
    
    # 2. 从 price_data 的路径中提取
    if not ticker:
        for key in ['risk_reward', 'sma_crossovers', 'ema_crossovers', 'vw_macd']:
            if key in price_data and isinstance(price_data[key], dict) and 'graph_path' in price_data[key]:
                path = str(price_data[key]['graph_path'])
                if '_' in path:
                    ticker = path.split('/')[-1].split('_')[0]
                    break
    
    print(f"[DEBUG] transform_price_data - ticker: {ticker}")
    
    graph_paths = {}
    summaries = {}
    
    # 如果有 ticker，直接从文件系统查找最新的图片
    if ticker:
        graph_dir = GRAPH_DIR / f"{ticker}_Graph"
        
        if graph_dir.exists():
            print(f"[DEBUG] Checking graph directory: {graph_dir}")
            
            # 为每种图表类型查找最新的文件
            for key in ['risk_reward', 'sma_crossovers', 'ema_crossovers', 'vw_macd']:
                # 查找该类型的所有图片文件
                pattern1 = f"{ticker}_{key}_*.png"
                pattern2 = f"{ticker}_{key}.png"
                
                files = list(graph_dir.glob(pattern1))
                simple_file = graph_dir / pattern2
                
                if simple_file.exists():
                    files.append(simple_file)
                
                if files:
                    # 使用最新修改的文件
                    latest_file = max(files, key=lambda f: f.stat().st_mtime)
                    rel_path = f"{ticker}_Graph/{latest_file.name}"
                    graph_paths[key] = rel_path
                    print(f"[DEBUG] Found graph for {key}: {rel_path}")
                else:
                    print(f"[DEBUG] No graph found for {key}")
                
                # 获取摘要
                if key in price_data and isinstance(price_data[key], dict):
                    if 'summary' in price_data[key]:
                        summaries[f'{key}_summary'] = price_data[key]['summary']
        else:
            print(f"[DEBUG] Graph directory does not exist: {graph_dir}")
    else:
        print("[DEBUG] No ticker found, using original logic")
        
        # 原有的逻辑作为备用
        for key in ['risk_reward', 'sma_crossovers', 'ema_crossovers', 'vw_macd']:
            if key in price_data and isinstance(price_data[key], dict):
                if 'summary' in price_data[key]:
                    summaries[f'{key}_summary'] = price_data[key]['summary']
                
                if 'graph_path' in price_data[key]:
                    graph_path = str(price_data[key]['graph_path'])
                    
                    # 提取相对路径
                    if '/Graph/' in graph_path:
                        rel_path = graph_path.split('/Graph/')[-1]
                    elif '\\Graph\\' in graph_path:
                        rel_path = graph_path.split('\\Graph\\')[-1].replace('\\', '/')
                    else:
                        rel_path = graph_path
                    
                    # 检查文件是否存在
                    full_path = GRAPH_DIR / rel_path
                    if full_path.exists():
                        graph_paths[key] = rel_path
    
    transformed = {
        'graph_paths': graph_paths,
        **summaries,
        'analysis': {
            'summary': price_data.get('analysis', {}).get('summary', '')
        } if 'analysis' in price_data else None
    }
    
    print(f"[DEBUG] Final transformed data:")
    print(f"  - graph_paths: {graph_paths}")
    print(f"  - summaries keys: {list(summaries.keys())}")
    
    return transformed


    """Transform price data from backend format to frontend format."""
    if not price_data:
        return {}
    
    graph_paths = {}
    summaries = {}
    
    for key in ['risk_reward', 'sma_crossovers', 'ema_crossovers', 'vw_macd']:
        if key in price_data and isinstance(price_data[key], dict):
            # 获取路径
            if 'graph_path' in price_data[key]:
                path = str(price_data[key]['graph_path'])
                
                # 提取相对路径
                if '/Graph/' in path:
                    rel_path = path.split('/Graph/')[-1]
                elif '\\Graph\\' in path:
                    rel_path = path.split('\\Graph\\')[-1].replace('\\', '/')
                else:
                    rel_path = path
                
                # 直接使用，不检查文件是否存在
                # 让前端处理加载错误
                graph_paths[key] = rel_path
                    
            # 获取摘要
            if 'summary' in price_data[key]:
                summaries[f'{key}_summary'] = price_data[key]['summary']
    
    return {
        'graph_paths': graph_paths,
        **summaries,
        'ana'
        'ysis': price_data.get('analysis', {})
    }
@app.get("/api/v1/analysis/{job_id}/status", response_model=StatusResp)
def job_status(job_id: str, cursor: int = 0):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    st = jobs[job_id]
    # Get new logs
    new_logs = st.log[cursor:]
    next_cursor = cursor + len(new_logs)
    # Get all fields from JobStatus
    payload = st.model_dump()
    # Remove log if not needed
    payload.pop("log", None)
    
    # Transform price data if it exists
    if 'panel_data' in payload and 'price' in payload['panel_data']:
        price_data = transform_price_data(payload['panel_data']['price'])
        payload['panel_data']['price'] = price_data
        print(f"DEBUG: Transformed price data: {json.dumps(price_data.get('graph_paths', {}))}")
    
    # Add new_logs and next_cursor
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
        full_result["Ticker"] = ticker
        # 把整个 JSON 持久化到文件，而不是只截取部分字段
        out_path = DATA_DIR / f"{job_id}.json"
        out_path.write_text(
            json.dumps(full_result, ensure_ascii=False)
        )
        # Update panel_data with the analysis results
        jobs[job_id].panel_data = {
            "macro": full_result.get("Macro", {}),
            "micro": full_result.get("Micro", {}),
            "price": full_result.get("Price", {}),
            "strategy": full_result.get("Strategy", {})
        }
        # 标记任务完成
        jobs[job_id].state = "finished"
        jobs[job_id].message = "Analysis completed"
        for k in jobs[job_id].panel_progress:
            jobs[job_id].panel_progress[k] = 100
    except Exception as e:
        jobs[job_id].state = "error"
        jobs[job_id].message = str(e)

app.include_router(verify_router, prefix="/api/v1/verify")