from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Mapea child_code -> lista de conexiones de tutores (madres/padres)
        self.guardian_connections: dict[str, list[WebSocket]] = {}
        # Mapea child_code -> conexión del dispositivo rastreador del niño
        self.tracker_connections: dict[str, WebSocket] = {}

    async def connect_guardian(self, child_code: str, websocket: WebSocket):
        """Acepta y registra la conexión WebSocket de un tutor monitoreando a un niño."""
        await websocket.accept()
        if child_code not in self.guardian_connections:
            self.guardian_connections[child_code] = []
        self.guardian_connections[child_code].append(websocket)

    def disconnect_guardian(self, child_code: str, websocket: WebSocket):
        """Remueve la conexión del tutor."""
        if child_code in self.guardian_connections:
            if websocket in self.guardian_connections[child_code]:
                self.guardian_connections[child_code].remove(websocket)
            if not self.guardian_connections[child_code]:
                del self.guardian_connections[child_code]

    async def broadcast_to_guardians(self, child_code: str, data: dict):
        """Envía información de ubicación en tiempo real a todos los tutores conectados al mapa del niño."""
        if child_code in self.guardian_connections:
            # Creamos una copia para evitar problemas de concurrencia al remover sockets cerrados
            for connection in list(self.guardian_connections[child_code]):
                try:
                    await connection.send_json(data)
                except Exception:
                    # Si el envío falla, desconectamos el socket inactivo
                    self.disconnect_guardian(child_code, connection)

    async def connect_tracker(self, child_code: str, websocket: WebSocket):
        """Acepta la conexión del dispositivo del niño."""
        await websocket.accept()
        self.tracker_connections[child_code] = websocket

    def disconnect_tracker(self, child_code: str):
        """Remueve el dispositivo del niño."""
        if child_code in self.tracker_connections:
            del self.tracker_connections[child_code]

manager = ConnectionManager()
