import asyncio
import os
import logging
from typing import Any, Dict, List, Optional
from contextlib import AsyncExitStack

# Se requiere instalar: pip install mcp
try:
    from mcp import ClientSession
    from mcp.client.sse import sse_client
except ImportError:
    logging.warning("Módulo 'mcp' no encontrado. Instala con `pip install mcp`.")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class MikroTikSkill:
    """
    Wrapper para comunicarse con el MikroTik MCP Server (jeff-nasseri/mikrotik-mcp).
    Asume que el servidor expone transporte SSE en MIKROTIK_MCP_URL.
    """
    def __init__(self, mcp_url: Optional[str] = None):
        # Asumimos /sse como endpoint por defecto si no se especifica
        default_url = "http://mikrotik-mcp:5000/sse"
        self.mcp_url = mcp_url or os.getenv("MIKROTIK_MCP_URL", default_url)
        if not self.mcp_url.endswith("/sse") and "5000" in self.mcp_url:
            # Corrección proactiva para añadir /sse si no está
            self.mcp_url = self.mcp_url.rstrip("/") + "/sse"
            
        self._session: Optional['ClientSession'] = None
        self._exit_stack: Optional[AsyncExitStack] = None

    async def connect(self):
        """Inicializa la sesión MCP cliente usando transporte SSE."""
        if self._session:
            return

        self._exit_stack = AsyncExitStack()
        
        try:
            # Configurar transporte SSE
            logger.info(f"Conectando a MikroTik MCP en {self.mcp_url}...")
            sse_transport = await self._exit_stack.enter_async_context(sse_client(self.mcp_url))
            
            # Inicializar sesión cliente
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(sse_transport[0], sse_transport[1])
            )
            
            await self._session.initialize()
            logger.info("¡Conectado exitosamente al MikroTik MCP Server!")
        except Exception as e:
            logger.error(f"Error conectando a {self.mcp_url}: {e}")
            if self._exit_stack:
                await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None
            raise

    async def disconnect(self):
        """Cierra la conexión con el MCP Server."""
        if self._exit_stack:
            await self._exit_stack.aclose()
        self._session = None
        self._exit_stack = None
        logger.info("Desconectado de MikroTik MCP.")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Lista todas las herramientas (tools) disponibles en el MCP Server."""
        if not self._session:
            await self.connect()
        
        response = await self._session.list_tools()
        tools = [
            {
                "name": tool.name, 
                "description": tool.description, 
                "input_schema": tool.inputSchema
            } 
            for tool in response.tools
        ]
        return tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Invoca una tool específica con los argumentos dados."""
        if not self._session:
            await self.connect()
            
        logger.info(f"Ejecutando tool '{name}' con argumentos: {arguments}")
        try:
            result = await self._session.call_tool(name, arguments)
            return result
        except Exception as e:
            logger.error(f"Error ejecutando tool '{name}': {e}")
            raise

# Ejemplo de uso independiente (para pruebas locales)
async def test_mcp():
    # Usando localhost para pruebas si se levanta por separado
    skill = MikroTikSkill("http://localhost:5000/sse")
    try:
        await skill.connect()
        tools = await skill.list_tools()
        print(f"\nSe encontraron {len(tools)} tools disponibles:")
        for t in tools:
            print(f"- {t['name']}: {t['description']}")
    except Exception as e:
        print(f"Error en el test: {e}")
    finally:
        await skill.disconnect()

if __name__ == "__main__":
    asyncio.run(test_mcp())
