from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.modules.auth.router import router as auth_router
from app.modules.daycares.router import router as daycares_router
from app.modules.guardians.router import router as guardians_router
from app.modules.children.router import router as children_router
from app.modules.devices.router import router as devices_router
from app.modules.tracking_devices.router import router as tracking_devices_router
from app.modules.locations.router import router as locations_router
from app.modules.locations.websocket import router as locations_ws_router
from app.modules.alerts.router import router as alerts_router

app = FastAPI(
    title="SIG Monitoreo Infantil API",
    description="Backend completo para el sistema de monitoreo infantil georreferenciado con PostGIS, WebSockets y FCM.",
    version="1.0.0"
)

# Habilitar CORS para permitir integraciones con la app Web y Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar todos los routers de negocio
app.include_router(auth_router)
app.include_router(daycares_router)
app.include_router(guardians_router)
app.include_router(children_router)
app.include_router(devices_router)
app.include_router(tracking_devices_router)
app.include_router(locations_router)
app.include_router(locations_ws_router) # Incluye WebSockets de tracking y dashboard
app.include_router(alerts_router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "SIG Monitoreo Infantil Backend",
        "docs": "/docs"
    }

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # 1. Documentar WS de tracking
    openapi_schema["paths"]["/ws/tracking/children/{child_code}/location"] = {
        "get": {
            "summary": "WebSocket: Transmisión de ubicación desde el rastreador GPS",
            "description": (
                "Establece una conexión WebSocket persistente para que los dispositivos de "
                "rastreo (TRACKING_DEVICE) envíen la telemetría del niño en tiempo real.\n\n"
                "**Formato del mensaje JSON a enviar periódicamente por el cliente (dispositivo):**\n"
                "```json\n"
                "{\n"
                "  \"latitude\": -17.7833,\n"
                "  \"longitude\": -63.1821,\n"
                "  \"accuracy\": 10.0,\n"
                "  \"speed\": 1.2,\n"
                "  \"heading\": 180.0,\n"
                "  \"received_at\": \"2026-07-04T17:00:00Z\"\n"
                "}\n"
                "```"
            ),
            "tags": ["WebSockets de Monitoreo"],
            "parameters": [
                {
                    "name": "child_code",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": "Código único del niño (ej. NIN-8F42K)"
                },
                {
                    "name": "token",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": "Token JWT del dispositivo con rol TRACKING_DEVICE o ADMIN"
                }
            ],
            "responses": {
                "101": {
                    "description": "Protocol Switching. Conexión WebSocket establecida con éxito."
                }
            }
        }
    }
    
    # 2. Documentar WS del mapa en vivo
    openapi_schema["paths"]["/ws/guardians/me/children/{child_code}/live-location"] = {
        "get": {
            "summary": "WebSocket: Visualización del mapa en vivo (Tutor/Madre)",
            "description": (
                "Establece una conexión WebSocket persistente para que el cliente web o móvil "
                "reciba la ubicación en tiempo real del niño.\n\n"
                "**Respuesta inicial e impulsos del servidor (JSON):**\n"
                "```json\n"
                "{\n"
                "  \"child_code\": \"NIN-8F42K\",\n"
                "  \"child_name\": \"Mateo Vargas\",\n"
                "  \"daycare_code\": \"GUA-SCZ-001\",\n"
                "  \"daycare_name\": \"Guardería Los Pinos\",\n"
                "  \"latitude\": -17.7833,\n"
                "  \"longitude\": -63.1821,\n"
                "  \"accuracy\": 10.0,\n"
                "  \"is_inside_area\": true,\n"
                "  \"monitoring_status\": \"INSIDE_AREA\",\n"
                "  \"received_at\": \"2026-07-04T17:00:00Z\"\n"
                "}\n"
                "```"
            ),
            "tags": ["WebSockets de Monitoreo"],
            "parameters": [
                {
                    "name": "child_code",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": "Código único del niño (ej. NIN-8F42K)"
                },
                {
                    "name": "token",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": "Token JWT del tutor con rol GUARDIAN o ADMIN"
                }
            ],
            "responses": {
                "101": {
                    "description": "Protocol Switching. Conexión WebSocket establecida con éxito."
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
