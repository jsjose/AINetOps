import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
from contextlib import asynccontextmanager
import asyncio

from skills.mikrotik_skill import MikroTikSkill
# Ejemplo futuro: from agents.config_agent import ConfigAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instancia global del wrapper MCP
mcp_client = MikroTikSkill()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tareas de inicio
    logger.info("Iniciando AI-NO-MikroTik Super-Orchestrator...")
    try:
        # Intentar establecer conexión con el MCP Server
        # (Se hace como tarea de fondo si el MCP server tarda más en levantar)
        asyncio.create_task(mcp_client.connect())
    except Exception as e:
        logger.warning(f"No se pudo conectar al MCP Server en el arranque: {e}")
    yield
    # Tareas de apagado
    logger.info("Apagando Super-Orchestrator...")
    await mcp_client.disconnect()

app = FastAPI(
    title="AI-NO-MikroTik Super-Orchestrator API",
    description="API Gateway para el orquestador multi-agente de redes MikroTik",
    version="0.1.0",
    lifespan=lifespan
)

class IntentRequest(BaseModel):
    intent: str = Field(..., description="El intent de red en lenguaje natural (Español)", example="Bloquea todo el tráfico entrante desde la IP 10.10.10.5")
    user_id: str = Field(default="admin", description="Usuario que solicita el intent")

class PlanStep(BaseModel):
    step: int
    description: str

class IntentResponse(BaseModel):
    status: str
    message: str
    plan: list[PlanStep] = []

@app.post("/api/v1/intent", response_model=IntentResponse)
async def handle_intent(request: IntentRequest):
    """
    Endpoint principal para recibir intents del usuario.
    Delega la ejecución al agente apropiado (Config, Fault, Monitoreo).
    """
    logger.info(f"Nuevo Intent recibido de {request.user_id}: '{request.intent}'")
    
    # Clasificación básica (mock) del intent para delegar al agente correcto
    intent_lower = request.intent.lower()
    
    if "firewall" in intent_lower or "ip" in intent_lower or "vlan" in intent_lower:
        agent_target = "ConfigAgent"
    elif "lentitud" in intent_lower or "caída" in intent_lower or "error" in intent_lower:
        agent_target = "FaultAgent"
    else:
        agent_target = "MonitoringAgent"
        
    logger.info(f"Delegando tarea al: {agent_target}")
    
    # En el Paso 5 conectaremos esta lógica con la clase real del ConfigAgent usando LangGraph
    # Por ahora devolvemos la planificación de alto nivel.
    
    plan = [
        PlanStep(step=1, description=f"[{agent_target}] Analizar el intent usando LLM y RAG"),
        PlanStep(step=2, description="[MCP Client] Obtener el estado actual del dispositivo (tools de telemetría/config)"),
        PlanStep(step=3, description="[Reasoning] Determinar los comandos RouterOS necesarios"),
        PlanStep(step=4, description="[Execution] Enviar configuración vía MikroTik MCP Server"),
        PlanStep(step=5, description="[Verification] Validar que el intent se cumplió satisfactoriamente")
    ]
    
    return IntentResponse(
        status="processing",
        message=f"Intent interpretado y delegado a {agent_target}. Closed-loop iniciado.",
        plan=plan
    )

@app.get("/health", tags=["System"])
async def health_check():
    """Endpoint para verificar el estado de salud del Orchestrator y sus dependencias."""
    return {
        "status": "ok", 
        "mcp_connected": mcp_client._session is not None
    }

if __name__ == "__main__":
    # Para desarrollo local independiente
    uvicorn.run("orchestrator:app", host="0.0.0.0", port=8000, reload=True)
