"""FastAPI application entry point for NetCoop AI."""

import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.agents.performance_agent import PerformanceAgent
from backend.agents.infrastructure_agent import InfrastructureHealthAgent
from backend.agents.connectivity_agent import ConnectivityAnalysisAgent
from backend.models.agent_message import AgentMessage
from backend.models.connectivity import ConnectivityTelemetry
from backend.models.diagnosis import DiagnosisRequest, DiagnosisResponse
from backend.models.history import DiagnosisHistoryResponse, DiagnosisRecord
from backend.models.infrastructure import InfrastructureTelemetryBatch
from backend.models.telemetry import TelemetryBatch
from backend.orchestrator.diagnosis_orchestrator import MultiAgentOrchestrator
from backend.storage.repository import DiagnosisRepository

app = FastAPI(
    title="NetCoop AI API",
    description="Backend API for the NetCoop AI network fault diagnosis project.",
    version="1.0.0",
)

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in allowed_origins else allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
def root_status() -> dict[str, str]:
    """Report API readiness and documentation link."""
    return {
        "status": "online",
        "service": "NetCoop AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Report that the API process is ready."""
    return {"status": "ok"}


@app.post("/api/performance", response_model=AgentMessage, tags=["performance"])
def analyze_performance(telemetry: TelemetryBatch) -> AgentMessage:
    """Analyze supplied performance telemetry without running other agents."""
    return PerformanceAgent().analyze(telemetry)


@app.post("/api/infrastructure", response_model=AgentMessage, tags=["infrastructure"])
def analyze_infrastructure(telemetry: InfrastructureTelemetryBatch) -> AgentMessage:
    """Analyze supplied infrastructure telemetry without running other agents."""
    return InfrastructureHealthAgent().analyze(telemetry)


@app.post("/api/connectivity", response_model=AgentMessage, tags=["connectivity"])
def analyze_connectivity(telemetry: ConnectivityTelemetry) -> AgentMessage:
    """Analyze supplied topology without running other agents."""
    return ConnectivityAnalysisAgent().analyze(telemetry)


@app.post("/api/diagnose", response_model=DiagnosisResponse, tags=["diagnosis"])
def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    """Run the five-agent workflow for one network diagnosis request."""
    response = MultiAgentOrchestrator().run(request)
    repo = DiagnosisRepository()
    repo.save_diagnosis(request, response, replace=True)
    return response


@app.get("/api/diagnoses", response_model=DiagnosisHistoryResponse, tags=["history"])
def get_diagnosis_history(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum items to return"),
    offset: int = Query(default=0, ge=0, description="Items to skip for pagination"),
) -> DiagnosisHistoryResponse:
    """Retrieve newest-first paginated diagnosis history."""
    repo = DiagnosisRepository()
    result = repo.list_diagnoses(limit=limit, offset=offset)
    return DiagnosisHistoryResponse.model_validate(result)


@app.get("/api/diagnoses/{diagnosis_id}", response_model=DiagnosisRecord, tags=["history"])
def get_diagnosis_by_id(diagnosis_id: str) -> DiagnosisRecord:
    """Retrieve full record for a specific diagnosis by ID."""
    repo = DiagnosisRepository()
    record = repo.get_diagnosis(diagnosis_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Diagnosis '{diagnosis_id}' not found",
        )
    return DiagnosisRecord.model_validate(record)


from backend.models.interoperability import (
    InteropValidationRequest,
    InteropValidationResponse,
)
from backend.services.interoperability import validate_interoperability


@app.post(
    "/api/interop/validate",
    response_model=InteropValidationResponse,
    tags=["interoperability"],
)
def validate_telemetry_interoperability(
    request: InteropValidationRequest,
) -> InteropValidationResponse:
    """Validate schema, detect aliases, and test unit normalizations without executing diagnosis."""
    result = validate_interoperability(
        payload=request.payload,
        domain=request.domain,
        schema_version=request.schema_version,
    )
    return InteropValidationResponse.model_validate(result)
