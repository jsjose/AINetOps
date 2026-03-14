# AI-NO-MikroTik (AI Network Operations para MikroTik)

Este proyecto implementa una arquitectura modular de agentes AI especializados en operaciones de redes, utilizando un esquema MVP enfocado inicialmente en dispositivos MikroTik.
    
## Arquitectura

El sistema está diseñado en capas con un orquestador central (Super Agent) que coordina agentes especializados y se integra con la red usando el protocolo Model Context Protocol (MCP).

1. **User & Intents**: Traducción de lenguaje natural a planes accionables.
2. **Perception & Data**: Qdrant (Vector DB), Redis, PostgreSQL para estado, emulando la capa de datos.
3. **MCP Integration**: Uso del MCP server oficial de MikroTik para exponer "skills" o herramientas.
4. **Agentes (A2A)**: Orchestrator, ConfigAgent, FaultAgent y MonitoringAgent.
5. **Reasoning & Execution**: Planificación LLM y automatización estilo circuito cerrado (ZSM).

## Requisitos

- **Docker** y **Docker Compose**
- Un router MikroTik (virtualizado mediante CHR/GNS3 o un equipo físico) con la API habilitada.
- API Key de un LLM soportado (Groq, Anthropic, OpenAI, etc.).
- Python 3.10+ (si se va a desarrollar o ejecutar localmente sin Docker).

## Instalación y Arranque

1. Clona el repositorio.
2. Crea un archivo `.env` basado en la configuración necesaria:
   ```bash
   ROS_HOST=192.168.88.1
   ROS_USERNAME=admin
   ROS_PASSWORD=tu_password
   ROS_PORT=8728
   LLM_API_KEY=tu_api_key_del_proveedor
   ```
3. Levanta los servicios base con Docker Compose:
   ```bash
   docker compose up -d
   ```

## Ejemplo de uso (Intent)

Puedes probar el sistema enviando un *intent* en español a través de la API o la CLI del orquestador:

> "Optimiza el firewall para bloquear tráfico de una IP"

El Request (ej. HTTP POST al Orchestrator):

```bash
curl -X POST http://localhost:8000/api/v1/intent \
     -H "Content-Type: application/json" \
     -d '{"intent": "Bloquea todo el tráfico entrante desde la IP 10.10.10.5 en el firewall"}'
```

El Orchestrator delegará al `ConfigAgent`, quien utilizará el cliente MCP para enviar la configuración al MikroTik de manera autónoma.
