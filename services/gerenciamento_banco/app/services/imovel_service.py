from sqlalchemy.orm import Session

from app.models.imovel import Imovel
from app.utils.car_validator import FormatoCarInvalidoError, validar_codigo_car


class ImovelService:
    """Leitura de imóveis na tabela `imovel` (PostGIS)."""

    def buscar_por_car(self, db: Session, codigo_bruto: str) -> Imovel | None:
        """
        Valida o formato do CAR e consulta por codigo_car.
        Levanta FormatoCarInvalidoError se o formato for inválido.
        """
        codigo = validar_codigo_car(codigo_bruto)
        return (
            db.query(Imovel)
            .filter(Imovel.codigo_car == codigo)
            .first()
        )
