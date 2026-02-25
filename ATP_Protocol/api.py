from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from db import init_db, ATPToolRegistry, ATPExecutionLog

app = FastAPI(title="ATP Guardian API", description="Observability backend for Agent Tool Protocol")

# Initialize DB connection
engine, SessionLocal = init_db()

# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "ATP Guardian API is running"}

@app.get("/tools", response_model=List[Dict[str, Any]])
def get_tools(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve all registered tools from the ATP Registry."""
    tools = db.query(ATPToolRegistry).offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(tool.id),
            "mcp_server_name": tool.mcp_server_name,
            "tool_name": tool.tool_name,
            "manifest_hash": tool.manifest_hash,
            "success_rate": tool.success_rate,
            "created_at": tool.created_at
        }
        for tool in tools
    ]

@app.get("/logs", response_model=List[Dict[str, Any]])
def get_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve execution logs of agent-tool interactions."""
    logs = db.query(ATPExecutionLog, ATPToolRegistry.tool_name).join(
        ATPToolRegistry, ATPExecutionLog.tool_id == ATPToolRegistry.id
    ).order_by(ATPExecutionLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(log.ATPExecutionLog.id),
            "tool_id": str(log.ATPExecutionLog.tool_id),
            "tool_name": log.tool_name,
            "agent_framework": log.ATPExecutionLog.agent_framework,
            "input_arguments": log.ATPExecutionLog.input_arguments,
            "execution_result": log.ATPExecutionLog.execution_result,
            "is_anomaly": log.ATPExecutionLog.is_anomaly,
            "timestamp": log.ATPExecutionLog.timestamp
        }
        for log in logs
    ]

from pydantic import BaseModel

class LogCreate(BaseModel):
    tool_name: str
    agent_framework: str
    input_arguments: Dict[str, Any]
    execution_result: str
    is_anomaly: bool = False

@app.post("/logs", response_model=Dict[str, Any])
def create_log(log_req: LogCreate, db: Session = Depends(get_db)):
    """Record a new execution log from an agent/translator interceptor."""
    # Find matching tool
    tool = db.query(ATPToolRegistry).filter_by(tool_name=log_req.tool_name).first()
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {log_req.tool_name} not found in registry")
        
    new_log = ATPExecutionLog(
        tool_id=tool.id,
        agent_framework=log_req.agent_framework,
        input_arguments=log_req.input_arguments,
        execution_result=log_req.execution_result,
        is_anomaly=log_req.is_anomaly
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    return {"status": "success", "log_id": str(new_log.id)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
