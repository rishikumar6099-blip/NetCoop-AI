"""FastAPI application entry point for NetCoop AI."""

from fastapi import FastAPI

from backend.agents.performance_agent import PerformanceAgent
from backend.agents.infrastructure_agent import InfrastructureHealthAgent
from backend.agents.connectivity_agent import ConnectivityAnalysisAgent
from backend.models.agent_message import AgentMessage
from backend.models.connectivity import ConnectivityTelemetry
from backend.models.diagnosis import DiagnosisRequest, DiagnosisResponse
from backend.models.infrastructure import InfrastructureTelemetryBatch
from backend.models.telemetry import TelemetryBatch
from backend.orchestrator.diagnosis_orchestrator import MultiAgentOrchestrator

app = FastAPI(
    title="NetCoop AI API",
    description="Backend API for the NetCoop AI network fault diagnosis project.",
    version="0.1.0",
)


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
    return MultiAgentOrchestrator().run(request)
