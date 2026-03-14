import os
import json
import logging
from typing import Any, Dict, List
import asyncio
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI # o ChatAnthropic/ChatGroq dependiendo del LLM_API_KEY
from skills.mikrotik_skill import MikroTikSkill

logger = logging.getLogger(__name__)

class ConfigAgent:
    """
    Agente de configuración que interactúa con un LLM y el MikroTik MCP Server
    para planificar y ejecutar intents de red como crear VLANs o reglas de firewall.
    """
    def __init__(self, llm_model: str = "gpt-4o"):
        api_key = os.getenv("LLM_API_KEY", "")
        if not api_key:
            logger.warning("LLM_API_KEY no encontrada. El agente no podrá planificar.")
            
        # Nota: Puedes cambiar ChatOpenAI por ChatGroq(model="llama3-70b-8192") o ChatAnthropic
        self.llm = ChatOpenAI(model=llm_model, api_key=api_key, temperature=0.0) if api_key else None
        self.mcp_client = MikroTikSkill()
        
        self.system_prompt = """Eres un experto en redes MikroTik (RouterOS) y un agente autónomo.
Tu trabajo es cumplir el "intent" de red del usuario usando las herramientas proporcionadas.
Reglas:
1. Analiza el intent y decide qué herramientas (tools) del MikroTik MCP necesitas ejecutar.
2. Si un intent pide configurar una VLAN o un Firewall, ejecuta la herramienta correspondiente con los parámetros exactos.
3. Si ocurre un error, evalúalo e intenta corregirlo.
4. Siempre devuelve una respuesta clara de lo que has configurado.
"""

    async def _format_mcp_to_lc_tools(self) -> List[Dict]:
        """
        Lee las tools del servidor MCP y las formatea para que el LLM (OpenAI style)
        las entienda como funciones llamables (function calling schema).
        """
        mcp_tools = await self.mcp_client.list_tools()
        lc_tools = []<
        for t in mcp_tools:
            # Convertimos el JSON Schema de MCP al formato de OpenAI Tools
            lc_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"]
                }
            })
        return lc_tools

    async def execute_intent(self, intent: str) -> Dict[str, Any]:
        """
        Bucle de razonamiento iterativo (ReAct / Tool Calling) para cumplir el intent.
        Closed-loop logic.
        """
        logger.info(f"[ConfigAgent] Procesando intent: {intent}")
        await self.mcp_client.connect()
        
        if not self.llm:
            return {"status": "error", "message": "No hay LLM configurado (API Key faltante)."}

        # 1. Obtener herramientas disponibles desde el MCP Server
        tools_schema = await self._format_mcp_to_lc_tools()
        llm_with_tools = self.llm.bind_tools(tools_schema) if tools_schema else self.llm

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=intent)
        ]

        # 2. Bucle de ejecución (max 5 iteraciones para evitar loops infinitos)
        max_iterations = 5
        for i in range(max_iterations):
            logger.info(f"[ConfigAgent] Iteración {i+1} de razonamiento...")
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            # Si el modelo no llamó a ninguna herramienta, ha terminado su análisis
            if not response.tool_calls:
                logger.info("[ConfigAgent] Finalizó la ejecución sin más tool calls.")
                break

            # 3. Ejecutar las herramientas solicitadas por el LLM
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]
                
                logger.info(f"[ConfigAgent] LLM solicita ejecutar MCP Tool: {tool_name} con {tool_args}")
                
                try:
                    result = await self.mcp_client.call_tool(tool_name, tool_args)
                    result_str = json.dumps(result)
                    logger.info(f"[ConfigAgent] Resultado de la tool: {result_str}")
                except Exception as e:
                    logger.error(f"[ConfigAgent] Error ejecutando {tool_name}: {e}")
                    result_str = f"Error execution tool: {str(e)}"
                
                # Devolver el resultado de la tool al LLM
                messages.append(ToolMessage(
                    tool_call_id=tool_call_id,
                    content=result_str,
                    name=tool_name
                ))

        await self.mcp_client.disconnect()
        
        return {
            "status": "success",
            "message": response.content,
            "iterations": i + 1
        }

# Prueba local independiente
async def test_agent():
    agent = ConfigAgent()
    # Mockeamos una key para inicializar si no la hay solo para test
    if not agent.llm:
         print("Necesitas configurar LLM_API_KEY para ejecutar el test real.")
         return
         
    intent = "Crea una VLAN llamada 'GuestVLAN' con ID 100 en la interfaz 'ether1', y optimiza el firewall para bloquear tráfico de la IP 10.10.10.5"
    print(f"\n--- Iniciando Prueba de ConfigAgent con Intent ---\n{intent}\n")
    try:
        result = await agent.execute_intent(intent)
        print("\n--- Resultado Final ---")
        print(result["message"])
    except Exception as e:
        print(f"Error en el agente: {e}")

if __name__ == "__main__":
    asyncio.run(test_agent())
