# src/api/verify_api.py
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# ── 导入你的验证核心逻辑 ──────────────────────────────────────────
from News_Verification import (
    FilterResult,
    FilterStatus,
    VerificationResult,
    register_callback,
    unregister_callback,
    verify_statement,
)

router = APIRouter()

# ──────────────────── 请求 / 响应模型 ────────────────────────────
class VerificationRequest(BaseModel):
    statement: str
    use_video: bool = False

class VerificationResponse(BaseModel):
    session_id: str
    message: str

# ──────────────────── WebSocket 连接管理 ──────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def connect(self, ws: WebSocket, sid: str):
        await ws.accept()
        self.active[sid] = ws
        self._locks[sid] = asyncio.Lock()

    def disconnect(self, sid: str):
        self.active.pop(sid, None)
        self._locks.pop(sid, None)

    async def send(self, sid: str, payload: dict):
        if sid not in self.active:
            return
        async with self._locks[sid]:
            await self.active[sid].send_json(payload)

manager = ConnectionManager()
verification_results: Dict[str, VerificationResult] = {}

# ──────────────────── HTTP: 发起验证 ─────────────────────────────
@router.post("", response_model=VerificationResponse)
async def start_verification(req: VerificationRequest):
    sid = str(uuid.uuid4())
    # 后台协程跑真正逻辑（不会阻塞请求）
    asyncio.create_task(run_verification(sid, req.statement, req.use_video))
    return VerificationResponse(session_id=sid, message="Verification started")

# ──────────────────── HTTP: 获取最终结果 ─────────────────────────
@router.get("/results/{sid}")
async def get_results(sid: str):
    if sid not in verification_results:
        raise HTTPException(404, "Session not found")
    res = verification_results[sid]
    return {
        "statement": res.statement,
        "filters": [
            {
                "name": f.name,
                "status": f.status.value,
                "details": f.details,
                "timestamp": f.timestamp,
                "result": f.result,
            }
            for f in res.filters
        ],
        "final_decision": res.final_decision,
        "final_reasoning": res.final_reasoning,
        "reference_links": res.reference_links,
    }

# ──────────────────── WS: 实时推送 ───────────────────────────────
@router.websocket("/ws/{sid}")
async def ws_endpoint(ws: WebSocket, sid: str):
    await manager.connect(ws, sid)

    async def ws_callback(filter_name: str, status: FilterStatus, details: str, result: dict | None = None):
        await manager.send(
            sid,
            {
                "type": "filter_update",
                "filter_name": filter_name,
                "status": status.value,
                "details": details,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    register_callback(sid, ws_callback)

    try:
        while True:
            await ws.receive_text()  # 占位：可接客户端 ping
    except WebSocketDisconnect:
        manager.disconnect(sid)
        unregister_callback(sid)

# ──────────────────── 核心：运行验证流程 ─────────────────────────
async def run_verification(sid: str, statement: str, use_video: bool):
    """
    1. 先通知前端 'verification_started'
    2. 调 verify_statement() — 内部所有耗时同步调用已用 to_thread 包裹
    3. 推送 'verification_completed' 或 'error'
    """
    # STEP 1 ─── started
    await manager.send(
        sid,
        {
            "type": "verification_started",
            "statement": statement,
            "use_video": use_video,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    try:
        # STEP 2 ─── 主分析（加 8 分钟保险超时）
        result: VerificationResult = await asyncio.wait_for(
            verify_statement(statement, sid, use_video), timeout=480
        )

        verification_results[sid] = result

        # STEP 3 ─── completed
        await manager.send(
            sid,
            {
                "type": "verification_completed",
                "final_decision": result.final_decision,
                "final_reasoning": result.final_reasoning,
                "reference_links": result.reference_links,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    except asyncio.TimeoutError:
        await manager.send(
            sid,
            {
                "type": "error",
                "message": "Verification timed out",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    except Exception as e:
        await manager.send(
            sid,
            {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

# ──────────────────── 健康检查 ───────────────────────────────────
@router.get("/health")
async def health():
    return {"status": "healthy", "ts": datetime.utcnow().isoformat()}
