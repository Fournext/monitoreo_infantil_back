from pydantic import BaseModel, Field
from typing import Literal

class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"] = Field(
        default="Polygon",
        description="El tipo de geometría GeoJSON, que debe ser 'Polygon'."
    )
    coordinates: list[list[list[float]]] = Field(
        ...,
        description="Una lista de anillos de coordenadas. El primer anillo define el límite exterior. Cada coordenada debe ser [longitud, latitud].",
        examples=[
            [
                [-63.1821, -17.7833],
                [-63.1815, -17.7833],
                [-63.1815, -17.7827],
                [-63.1821, -17.7827],
                [-63.1821, -17.7833]
            ]
        ]
    )
