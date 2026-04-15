from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Categoria

router = APIRouter()


@router.get("/")
def listar_categorias(db: Session = Depends(get_db)):
    cats = db.query(Categoria).filter(Categoria.activa == True).order_by(Categoria.nombre).all()  # noqa: E712
    return [{"id": c.id, "nombre": c.nombre, "icono": c.icono, "color": c.color} for c in cats]
