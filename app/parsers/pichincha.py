import re
from datetime import datetime
from app.parsers.base import BaseParser, EmailData, TransaccionParseada


class PichinchaParser(BaseParser):

    dominios = ["pichincha.pe"]

    ASUNTOS_IGNORAR = [
        "bienvenido",
        "actualización",
        "seguridad",
    ]

    def puede_parsear(self, email: EmailData) -> bool:
        if not self._es_remitente_valido(email.remitente):
            return False
        if self._es_asunto_ignorable(email.asunto):
            return False
        asunto = email.asunto.lower()
        keywords = ["transferencia", "pago", "depósito", "débito", "comprobante"]
        return any(k in asunto for k in keywords)

    def parsear(self, email: EmailData) -> list[TransaccionParseada]:
        texto = self._html_a_texto(email.cuerpo_html) if email.cuerpo_html else email.cuerpo_texto
        asunto = email.asunto.lower()

        if "transferencia" in asunto:
            return self._parsear_transferencia(texto, email.fecha_recibido)

        return []

    def _parsear_transferencia(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        # Detectar moneda
        es_usd = "DOLARES" in texto.upper() or "USD" in texto.upper() or "$ " in texto

        if es_usd:
            monto = self._extraer_monto(texto, [
                r"Monto transferido\s+\$\s*([\d,]+\.?\d*)",
                r"Monto debitado\s+\$\s*([\d,]+\.?\d*)",
            ])
            moneda = "USD"
            cuenta = "Pichincha Dólares"
        else:
            monto = self._extraer_monto(texto, [
                r"Monto transferido\s+S/\s*([\d,]+\.?\d*)",
            ])
            moneda = "PEN"
            cuenta = "Pichincha Soles"

        if not monto:
            return []

        # Destino
        destino = self._extraer_campo(texto, r"Cuenta destino\s+([^\n]+?)(?:\s+Descripcion|$)")
        op = self._extraer_campo(texto, r"N°\s*Operación\s+(\w+)")
        descripcion = self._extraer_campo(texto, r"Descripcion de la operación\s+([^\n]+?)(?:\s+¿|$)")
        fecha = self._extraer_fecha_pichincha(texto) or fecha_fallback

        return [TransaccionParseada(
            cuenta_nombre=cuenta,
            fecha=fecha, monto=monto, moneda=moneda, tipo="cargo",
            descripcion=f"Transferencia Pichincha: {descripcion or destino or 'Sin datos'}",
            numero_operacion=op,
        )]

    def _extraer_fecha_pichincha(self, texto: str) -> datetime | None:
        # Formato: "1 Mayo 2025 - 09:11"
        meses = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
            "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
            "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        }
        patron = r"(\d{1,2})\s+(\w+)\s+(\d{4})\s*[-–]\s*(\d{1,2}):(\d{2})"
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            dia, mes_str, anio, hora, minuto = m.groups()
            mes = meses.get(mes_str.lower())
            if mes:
                return datetime(int(anio), mes, int(dia), int(hora), int(minuto))
        return None

    @staticmethod
    def _extraer_campo(texto: str, patron: str) -> str | None:
        m = re.search(patron, texto, re.IGNORECASE)
        return m.group(1).strip() if m else None
