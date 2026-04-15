from sqlalchemy import Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
from decimal import Decimal
from app.database import Base


class TipoCambio(Base):
    __tablename__ = "tipos_cambio"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    usd_a_pen: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)

    def __repr__(self) -> str:
        return f"<TipoCambio {self.fecha}: 1 USD = {self.usd_a_pen} PEN>"
