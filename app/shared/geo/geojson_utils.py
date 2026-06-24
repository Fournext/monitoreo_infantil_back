from typing import Any
from shapely.geometry import shape
from app.core.exceptions import BadRequestException

def validate_polygon_geojson(geojson: dict[str, Any]) -> dict[str, Any]:
    """
    Valida que el diccionario GeoJSON represente un polígono válido y cerrado.
    Si no está cerrado, intenta cerrarlo agregando el primer punto al final.
    """
    if not isinstance(geojson, dict):
        raise BadRequestException("El GeoJSON de área debe ser un objeto JSON.")

    geom_type = geojson.get("type")
    if geom_type != "Polygon":
        raise BadRequestException("El tipo de geometría de área debe ser 'Polygon'.")

    coordinates = geojson.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) == 0:
        raise BadRequestException("Las coordenadas del polígono están ausentes o vacías.")

    # Asegurar que cada anillo esté cerrado y tenga la forma correcta
    for ring_idx, ring in enumerate(coordinates):
        if not isinstance(ring, list) or len(ring) < 4:
            raise BadRequestException(
                f"El anillo {ring_idx} debe contener al menos 4 puntos (incluyendo el de cierre)."
            )
        
        for pt in ring:
            if not isinstance(pt, list) or len(pt) < 2:
                raise BadRequestException("Cada punto de coordenada debe ser una lista de al menos [longitud, latitud].")
            if not all(isinstance(val, (int, float)) for val in pt[:2]):
                raise BadRequestException("Los valores de longitud y latitud deben ser de tipo flotante o entero.")

        # Si el primer punto no coincide con el último, lo cerramos
        if ring[0][:2] != ring[-1][:2]:
            ring.append(ring[0])

    # Validar topología mediante Shapely
    try:
        poly_shape = shape(geojson)
        if not poly_shape.is_valid:
            from shapely.validation import make_valid
            corrected = make_valid(poly_shape)
            if corrected.geom_type == "Polygon":
                poly_shape = corrected
            elif corrected.geom_type == "MultiPolygon":
                # Si se fraccionó en varios polígonos, tomamos el de mayor área
                poly_shape = max(corrected.geoms, key=lambda g: g.area)
            else:
                raise BadRequestException("El polígono es inválido y no pudo corregirse de forma automatizada.")
    except Exception as e:
        raise BadRequestException(f"Geometría inválida: {str(e)}")

    return geojson

def geojson_to_polygon_wkt(geojson: dict[str, Any]) -> str:
    """
    Convierte un diccionario GeoJSON a su representación de texto WKT (Well-Known Text).
    """
    try:
        # Primero validamos/corregimos
        valid_geojson = validate_polygon_geojson(geojson)
        poly_shape = shape(valid_geojson)
        
        # Si por alguna razón sigue siendo inválido, aplicamos make_valid
        if not poly_shape.is_valid:
            from shapely.validation import make_valid
            poly_shape = make_valid(poly_shape)
            if poly_shape.geom_type == "MultiPolygon":
                poly_shape = max(poly_shape.geoms, key=lambda g: g.area)
                
        return poly_shape.wkt
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(f"Error al convertir GeoJSON a WKT: {str(e)}")
