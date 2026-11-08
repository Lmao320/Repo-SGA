"""Autenticación (bcrypt + JWT) y autorización por rol."""
import os
import time
import uuid

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

CLAVE_JWT = os.environ.get("SGA_JWT_SECRET", "clave-solo-para-pruebas-cambiar-en-produccion")
DURACION_TOKEN_S = 15 * 60
_tokens_revocados: set[str] = set()  # En producción: Redis (ADR-03)
_esquema = HTTPBearer(auto_error=False)


def hash_contrasena(texto: str) -> bytes:
    return bcrypt.hashpw(texto.encode(), bcrypt.gensalt(rounds=4))


def verificar_contrasena(texto: str, hash_guardado: bytes) -> bool:
    return bcrypt.checkpw(texto.encode(), hash_guardado)


def emitir_token(usuario_id: int, rol: str) -> str:
    ahora = int(time.time())
    datos = {"sub": str(usuario_id), "rol": rol, "iat": ahora,
             "exp": ahora + DURACION_TOKEN_S, "jti": uuid.uuid4().hex}
    return jwt.encode(datos, CLAVE_JWT, algorithm="HS256")


def revocar(jti: str) -> None:
    _tokens_revocados.add(jti)


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(_esquema)) -> dict:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token requerido")
    try:
        datos = jwt.decode(cred.credentials, CLAVE_JWT, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado")
    if datos["jti"] in _tokens_revocados:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token revocado")
    return {"id": int(datos["sub"]), "rol": datos["rol"], "jti": datos["jti"]}


def requiere_rol(*roles: str):
    def _verificar(usuario: dict = Depends(usuario_actual)) -> dict:
        if usuario["rol"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Rol sin permiso para esta operación")
        return usuario
    return _verificar
