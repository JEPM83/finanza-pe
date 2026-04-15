from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ReglaCategoria(Base):
    __tablename__ = "reglas_categoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"))
    # Texto a buscar (case-insensitive): "RAPPI", "UBER EATS", "WONG"
    patron: Mapped[str] = mapped_column(String(200), nullable=False)
    # descripcion | comercio
    campo: Mapped[str] = mapped_column(String(20), default="descripcion")
    # Menor número = mayor prioridad
    prioridad: Mapped[int] = mapped_column(Integer, default=100)

    categoria: Mapped["Categoria"] = relationship(back_populates="reglas")

    def __repr__(self) -> str:
        return f"<ReglaCategoria '{self.patron}' → {self.categoria_id}>"
