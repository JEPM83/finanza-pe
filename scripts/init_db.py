"""
Script de inicialización de la base de datos.
Crea todas las tablas y precarga datos iniciales.
Ejecutar una sola vez: python scripts/init_db.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from sqlalchemy.orm import Session
from app.database import engine, Base
from app.models import (
    Institucion, Cuenta, Categoria, ReglaCategoria, TipoCambio
)


def crear_tablas():
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente.")


def sembrar_instituciones(db: Session) -> dict[str, Institucion]:
    instituciones_data = [
        {"nombre": "BCP",           "dominios_email": "notificacionesbcp.com.pe"},
        {"nombre": "Yape",          "dominios_email": "yape.pe"},
        {"nombre": "Interbank",     "dominios_email": "netinterbank.com.pe,intercorp.com.pe"},
        {"nombre": "Pichincha",     "dominios_email": "pichincha.pe"},
        {"nombre": "Caja Arequipa", "dominios_email": "cajaarequipa.pe"},
        {"nombre": "Ligo",          "dominios_email": "ligo.pe"},
        {"nombre": "Efectivo",      "dominios_email": ""},
    ]
    instituciones = {}
    for data in instituciones_data:
        inst = Institucion(**data)
        db.add(inst)
        db.flush()
        instituciones[data["nombre"]] = inst
    print(f"  {len(instituciones)} instituciones creadas.")
    return instituciones


def sembrar_cuentas(db: Session, instituciones: dict[str, Institucion]):
    hoy = date.today()
    cuentas_data = [
        # Pichincha
        {"institucion": "Pichincha",     "nombre": "Pichincha Soles",        "tipo": "ahorros",    "moneda": "PEN"},
        {"institucion": "Pichincha",     "nombre": "Pichincha Dólares",       "tipo": "ahorros",    "moneda": "USD"},
        # Interbank
        {"institucion": "Interbank",     "nombre": "Visa Infiniti",           "tipo": "credito",    "moneda": "PEN"},
        # BCP
        {"institucion": "BCP",           "nombre": "BCP Soles",               "tipo": "ahorros",    "moneda": "PEN"},
        {"institucion": "BCP",           "nombre": "BCP Dólares",             "tipo": "ahorros",    "moneda": "USD"},
        {"institucion": "BCP",           "nombre": "Visa Oro BCP",            "tipo": "credito",    "moneda": "PEN"},
        # Yape
        {"institucion": "Yape",          "nombre": "Yape",                    "tipo": "billetera",  "moneda": "PEN"},
        # Caja Arequipa
        {"institucion": "Caja Arequipa", "nombre": "Plazo Fijo Caja Arequipa","tipo": "plazo_fijo", "moneda": "PEN"},
        {"institucion": "Caja Arequipa", "nombre": "Caja Arequipa Soles",     "tipo": "ahorros",    "moneda": "PEN"},
        # Ligo
        {"institucion": "Ligo",          "nombre": "Tarjeta La Mágica",       "tipo": "credito",    "moneda": "PEN"},
        # Efectivo
        {"institucion": "Efectivo",      "nombre": "Efectivo Soles",          "tipo": "efectivo",   "moneda": "PEN"},
    ]
    for data in cuentas_data:
        nombre_inst = data.pop("institucion")
        cuenta = Cuenta(
            **data,
            institucion_id=instituciones[nombre_inst].id,
            fecha_alta=hoy,
        )
        db.add(cuenta)
    print(f"  {len(cuentas_data)} cuentas creadas.")


def sembrar_categorias(db: Session) -> dict[str, Categoria]:
    categorias_data = [
        {"nombre": "Alimentación",       "icono": "🍽️",  "color": "#e74c3c"},
        {"nombre": "Delivery",           "icono": "🛵",  "color": "#e67e22"},
        {"nombre": "Supermercado",       "icono": "🛒",  "color": "#27ae60"},
        {"nombre": "Transporte",         "icono": "🚗",  "color": "#3498db"},
        {"nombre": "Telecomunicaciones", "icono": "📱",  "color": "#9b59b6"},
        {"nombre": "Servicios",          "icono": "💡",  "color": "#1abc9c"},
        {"nombre": "Entretenimiento",    "icono": "🎬",  "color": "#f39c12"},
        {"nombre": "Salud",              "icono": "🏥",  "color": "#2ecc71"},
        {"nombre": "Educación",          "icono": "📚",  "color": "#2980b9"},
        {"nombre": "Compras",            "icono": "🛍️",  "color": "#e91e63"},
        {"nombre": "Viajes",             "icono": "✈️",  "color": "#00bcd4"},
        {"nombre": "Transferencias",     "icono": "💸",  "color": "#95a5a6"},
        {"nombre": "Pago Tarjeta",       "icono": "💳",  "color": "#34495e"},
        {"nombre": "Otros",              "icono": "📦",  "color": "#7f8c8d"},
    ]
    categorias = {}
    for data in categorias_data:
        cat = Categoria(**data)
        db.add(cat)
        db.flush()
        categorias[data["nombre"]] = cat
    print(f"  {len(categorias)} categorías creadas.")
    return categorias


def sembrar_reglas(db: Session, categorias: dict[str, Categoria]):
    reglas_data = [
        # Delivery
        ("Delivery",           "RAPPI",           10),
        ("Delivery",           "UBER EATS",        10),
        ("Delivery",           "PEDIDOS YA",       10),
        ("Delivery",           "DOMINO",           20),
        ("Delivery",           "PIZZA HUT",        20),
        ("Delivery",           "KFC",              20),
        ("Delivery",           "MC DONALD",        20),
        ("Delivery",           "BURGER KING",      20),
        # Supermercado
        ("Supermercado",       "WONG",             10),
        ("Supermercado",       "METRO",            10),
        ("Supermercado",       "PLAZA VEA",        10),
        ("Supermercado",       "TOTTUS",           10),
        ("Supermercado",       "VIVANDA",          10),
        ("Supermercado",       "MASS",             10),
        # Transporte
        ("Transporte",         "UBER",             10),
        ("Transporte",         "BEAT",             10),
        ("Transporte",         "INDRIVER",         10),
        ("Transporte",         "CABIFY",           10),
        ("Transporte",         "APPARKA",          10),
        # Telecomunicaciones
        ("Telecomunicaciones", "CLARO",            10),
        ("Telecomunicaciones", "ENTEL",            10),
        ("Telecomunicaciones", "MOVISTAR",         10),
        ("Telecomunicaciones", "BITEL",            10),
        # Entretenimiento
        ("Entretenimiento",    "NETFLIX",          10),
        ("Entretenimiento",    "SPOTIFY",          10),
        ("Entretenimiento",    "DISNEY",           10),
        ("Entretenimiento",    "AMAZON PRIME",     10),
        ("Entretenimiento",    "CINEMARK",         10),
        ("Entretenimiento",    "CINEPLANET",       10),
        ("Entretenimiento",    "HBO",              10),
        # Salud
        ("Salud",              "INKAFARMA",        10),
        ("Salud",              "MIFARMA",          10),
        ("Salud",              "FARMACIA",         10),
        ("Salud",              "BOTICA",           10),
        ("Salud",              "CLINICA",          10),
        # Compras
        ("Compras",            "FALABELLA",        10),
        ("Compras",            "RIPLEY",           10),
        ("Compras",            "OECHSLE",          10),
        ("Compras",            "SAGA",             10),
        ("Compras",            "AMAZON",           10),
        ("Compras",            "MERCADO LIBRE",    10),
        ("Compras",            "DLC*MICROSOFT",    10),
        ("Compras",            "MICROSOFT",        20),
        ("Compras",            "GOOGLE",           20),
        ("Compras",            "APPLE",            20),
        # Pago Tarjeta
        ("Pago Tarjeta",       "PAGO DE TARJETA",  10),
        ("Pago Tarjeta",       "TARJETA LIGO",     10),
        # Transferencias
        ("Transferencias",     "TRANSFERENCIA",    50),
        ("Transferencias",     "YAPEO",            50),
        ("Transferencias",     "YAPE",             50),
    ]
    for nombre_cat, patron, prioridad in reglas_data:
        regla = ReglaCategoria(
            categoria_id=categorias[nombre_cat].id,
            patron=patron,
            campo="descripcion",
            prioridad=prioridad,
        )
        db.add(regla)
    print(f"  {len(reglas_data)} reglas de categorización creadas.")


def sembrar_tipo_cambio_inicial(db: Session):
    tc = TipoCambio(fecha=date.today(), usd_a_pen=3.7500)
    db.add(tc)
    print("  Tipo de cambio inicial: 1 USD = 3.75 PEN (actualizar manualmente).")


def main():
    print("Inicializando base de datos finanza-pe...")
    crear_tablas()

    from app.database import SessionLocal
    db = SessionLocal()
    try:
        print("\nSembrando datos iniciales:")
        instituciones = sembrar_instituciones(db)
        sembrar_cuentas(db, instituciones)
        categorias = sembrar_categorias(db)
        sembrar_reglas(db, categorias)
        sembrar_tipo_cambio_inicial(db)
        db.commit()
        print("\nBase de datos inicializada correctamente.")
    except Exception as e:
        db.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
