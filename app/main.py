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
