from fastapi import HTTPException, status

class BaseAppException(HTTPException):
    """Excepción base para la aplicación."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundException(BaseAppException):
    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class BadRequestException(BaseAppException):
    def __init__(self, detail: str = "Solicitud incorrecta o parámetros inválidos"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class UnauthorizedException(BaseAppException):
    def __init__(self, detail: str = "No autenticado o token expirado"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class ForbiddenException(BaseAppException):
    def __init__(self, detail: str = "No tiene permisos para realizar esta acción"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class ConflictException(BaseAppException):
    def __init__(self, detail: str = "Conflicto con el estado actual del recurso"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
