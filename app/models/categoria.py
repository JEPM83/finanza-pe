from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    icono: Mapped[str] = mapped_column(String(10), default="📦")
    color: Mapped[str] = mapped_column(String(7), default="#6c757d")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)

    reglas: Mapped[list["ReglaCategoria"]] = relationship(back_populates="categoria")
    transacciones: Mapped[list["Transaccion"]] = relationship(back_populates="categoria")

    def __repr__(self) -> str:
        return f"<Categoria {self.nombre}>"
