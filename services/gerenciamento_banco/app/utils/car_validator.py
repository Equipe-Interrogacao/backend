"""Validação de formato de código CAR (camada de serviço)."""

from __future__ import annotations

import re

# CAR estadual: somente dígitos (tamanho típico 11–20, conforme estados)
_CAR_NUMERICO = re.compile(r"^\d{11,20}$")
# CAR federal (ex.: SP-3525300-44AA2FE43D774264B9F18E55658E70FA)
_CAR_FEDERAL = re.compile(
    r"^[A-Za-z]{2}-\d{7}-[A-Fa-f0-9]{32}$",
    re.ASCII,
)


class FormatoCarInvalidoError(ValueError):
    """Código CAR com formato inválido (HTTP 400)."""

    def __init__(self, message: str = "Formato de código CAR inválido"):
        super().__init__(message)


def normalizar_codigo_car(codigo: str) -> str:
    """Remove espaços nas extremidades; não altera o conteúdo válido."""
    if codigo is None:
        raise FormatoCarInvalidoError("Código CAR não informado")
    return codigo.strip()


def validar_codigo_car(codigo: str) -> str:
    """
    Valida e retorna o código normalizado.
    Levanta FormatoCarInvalidoError se inválido.
    """
    c = normalizar_codigo_car(codigo)
    if not c:
        raise FormatoCarInvalidoError("Código CAR vazio")
    if _CAR_NUMERICO.match(c):
        return c
    if _CAR_FEDERAL.match(c):
        return f"{c[:2].upper()}{c[2:]}"
    raise FormatoCarInvalidoError()
