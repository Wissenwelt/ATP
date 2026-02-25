import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, sessionmaker

# Handle SQLite fallbacks for UUID and JSONB if not using PostgreSQL
from sqlalchemy.types import TypeDecorator, CHAR, TypeEngine
from sqlalchemy.dialects.sqlite import JSON

class GUID(TypeDecorator):
    """Platform-independent GUID type."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value

class JSONType(TypeDecorator):
    """Platform independent JSON type."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        elif dialect.name == 'sqlite':
            return dialect.type_descriptor(JSON())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if dialect.name in ['postgresql', 'sqlite']:
            return value
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if dialect.name in ['postgresql', 'sqlite']:
            return value
        if value is not None:
            return json.loads(value)
        return value

Base = declarative_base()

class ATPToolRegistry(Base):
    __tablename__ = 'atp_tool_registry'

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    mcp_server_name = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)
    manifest_hash = Column(String, unique=True, nullable=False)
    
    # The Contract
    raw_mcp_schema = Column(JSONType(), nullable=False)
    pydantic_schema_code = Column(Text, nullable=True) # Could store generated code string
    
    # Behavioral Score
    success_rate = Column(Float, default=1.0)
    last_anomaly_log = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_mcp_tool_hash', 'manifest_hash'),
    )

class ATPExecutionLog(Base):
    __tablename__ = 'atp_execution_log'

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    tool_id = Column(GUID(), nullable=False) # References ATPToolRegistry.id
    agent_framework = Column(String, nullable=False) # e.g., 'crewai', 'langchain'
    
    input_arguments = Column(JSONType(), nullable=False)
    execution_result = Column(Text, nullable=True)
    is_anomaly = Column(Boolean, default=False)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def init_db(db_url: str = "sqlite:///atp_registry.db"):
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        
    engine = create_engine(db_url, echo=False, connect_args=connect_args)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal

def generate_manifest_hash(server_name: str, tool_name: str, schema: dict) -> str:
    """Generates a stable hash for a tool manifest."""
    manifest_str = f"{server_name}:{tool_name}:{json.dumps(schema, sort_keys=True)}"
    return hashlib.sha256(manifest_str.encode('utf-8')).hexdigest()

if __name__ == "__main__":
    print("Initializing ATP Registry Database schemas...")
    _, SessionLocal = init_db()
    
    print("Checking database connection...")
    session = SessionLocal()
    try:
        count = session.query(ATPToolRegistry).count()
        print(f"Success! Current registered tools: {count}")
    finally:
        session.close()
