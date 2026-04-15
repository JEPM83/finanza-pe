import re
from datetime import datetime
from decimal import Decimal
from app.parsers.base import BaseParser, EmailData, TransaccionParseada


class BCPParser(BaseParser):

    dominios = ["notificacionesbcp.com.pe"]

    ASUNTOS_IGNORAR = [
        "tus compras por internet",
        "bienvenido",
        "activación",
    ]

    # Mapeo: últimos 4 dígitos o nombre de cuenta → nombre en el sistema
    _MAPA_CUENTAS = {
        "9879": "Visa Oro BCP",
        "2683": "BCP Soles",
        "0106": "BCP Dólares",
        "4168": "BCP Soles",
        "7023": "BCP Dólares",
        "7059": "BCP Soles",
        "clasica": "BCP Soles",
        "cuenta corriente": "BCP Soles",
        "cuenta premio": "BCP Dólares",
        "cuenta de ahorros": "BCP Soles",
    }

    def _resolver_cuenta(self, texto: str) -> str:
        texto_lower = texto.lower()
        for clave, nombre in self._MAPA_CUENTAS.items():
            if clave in texto_lower:
                return nombre
        return "BCP Soles"  # fallback

    def puede_parsear(self, email: EmailData) -> bool:
        if not self._es_remitente_valido(email.remitente):
            return False
        if self._es_asunto_ignorable(email.asunto):
            return False
        asunto = email.asunto.lower()
        keywords = ["consumo", "transferencia", "yapeo", "pago", "constancia"]
        return any(k in asunto for k in keywords)

    def parsear(self, email: EmailData) -> list[TransaccionParseada]:
        texto = self._html_a_texto(email.cuerpo_html) if email.cuerpo_html else email.cuerpo_texto
        asunto = email.asunto.lower()

        if "consumo" in asunto and "crédito" in asunto:
            return self._parsear_consumo_tc(texto, email.fecha_recibido)
        if "consumo" in asunto and "débito" in asunto:
            return self._parsear_consumo_td(texto, email.fecha_recibido)
        if "pago de tarjeta" in asunto or "pago de tarjeta" in texto.lower():
            return self._parsear_pago_tarjeta(texto, email.fecha_recibido)
        if "transferencia entre mis cuentas" in asunto:
            return self._parsear_transferencia_propia(texto, email.fecha_recibido)
        if "transferencia a terceros" in asunto:
            return self._parsear_transferencia_terceros(texto, email.fecha_recibido)
        if "yapeo" in asunto and "recepción" in asunto:
            return self._parsear_yapeo_recibido(texto, email.fecha_recibido)
        if "pago de servicio" in asunto or "pago de servicios" in texto.lower():
            return self._parsear_pago_servicio(texto, email.fecha_recibido)

        return []

    def _parsear_consumo_tc(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        monto = self._extraer_monto(texto, [
            r"consumo de\s+(?:S/|S\./)?\s*([\d,]+\.?\d*)",
            r"Monto Total del consumo\s+S/\s*([\d,]+\.?\d*)",
        ])
        if not monto:
            return []
        empresa = self._extraer_campo(texto, r"Empresa\s+([^\n]+?)(?:\s+Número|$)")
        op = self._extraer_campo(texto, r"Número de operación\s+(\w+)")
        fecha = self._extraer_fecha_bcp(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre="Visa Oro BCP",
            fecha=fecha, monto=monto, moneda="PEN", tipo="cargo",
            descripcion=f"Consumo TC BCP: {empresa or 'Sin datos'}",
            comercio=empresa, numero_operacion=op,
        )]

    def _parsear_consumo_td(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        monto = self._extraer_monto(texto, [
            r"consumo de\s+S/\s*([\d,]+\.?\d*)",
            r"Monto Total del consumo\s+S/\s*([\d,]+\.?\d*)",
        ])
        if not monto:
            return []
        empresa = self._extraer_campo(texto, r"Empresa\s+([^\n]+?)(?:\s+Número|$)")
        op = self._extraer_campo(texto, r"Número de operación\s+(\w+)")
        fecha = self._extraer_fecha_bcp(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre="BCP Soles",
            fecha=fecha, monto=monto, moneda="PEN", tipo="cargo",
            descripcion=f"Consumo TD BCP: {empresa or 'Sin datos'}",
            comercio=empresa, numero_operacion=op,
        )]

    def _parsear_pago_tarjeta(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        # Determinar moneda
        moneda = "USD" if "dólares" in texto.lower() else "PEN"
        simbolo = r"\$" if moneda == "USD" else r"S/"
        monto = self._extraer_monto(texto, [
            rf"Monto pagado\s+{simbolo}\s*([\d,]+\.?\d*)",
            rf"pago a tu tarjeta de\s+{simbolo}\s*([\d,]+\.?\d*)",
        ])
        if not monto:
            return []
        cuenta_origen = self._resolver_cuenta(texto)
        op = self._extraer_campo(texto, r"Número de operación\s+(\w+)")
        fecha = self._extraer_fecha_bcp(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre=cuenta_origen,
            fecha=fecha, monto=monto, moneda=moneda, tipo="cargo",
            descripcion="Pago tarjeta de crédito BCP",
            numero_operacion=op,
        )]

    def _parsear_transferencia_propia(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        # Detectar si involucra tipo de cambio (PEN→USD o viceversa)
        tiene_tc = "tipo de cambio" in texto.lower()
        if tiene_tc:
            monto_pen = self._extraer_monto(texto, [r"Monto transferido\s+S/\s*([\d,]+\.?\d*)"])
            monto_usd = self._extraer_monto(texto, [r"Total cobrado al tipo de cambio\s+\$\s*([\d,]+\.?\d*)"])
            cuenta_origen = self._resolver_cuenta(texto)
            op = self._extraer_campo(texto, r"Número de operación\s+(\w+)")
            fecha = self._extraer_fecha_bcp(texto) or fecha_fallback
            txs = []
            if monto_pen:
                txs.append(TransaccionParseada(
                    cuenta_nombre=cuenta_origen, fecha=fecha,
                    monto=monto_pen, moneda="PEN", tipo="cargo",
                    descripcion="Transferencia entre cuentas BCP (cargo PEN)",
                    numero_operacion=op,
                ))
            if monto_usd:
                txs.append(TransaccionParseada(
                    cuenta_nombre="BCP Dólares", fecha=fecha,
                    monto=monto_usd, moneda="USD", tipo="abono",
                    descripcion="Transferencia entre cuentas BCP (abono USD)",
                    numero_operacion=op,
                ))
            return txs
        else:
            monto = self._extraer_monto(texto, [r"Monto transferido\s+S/\s*([\d,]+\.?\d*)"])
            if not monto:
                return []
            cuenta_origen = self._resolver_cuenta(texto)
            op = self._extraer_campo(texto, r"Número de operación\s+(\w+)")
            fecha = self._extraer_fecha_bcp(texto) or fecha_fallback
            return [TransaccionParseada(
                cuenta_nombre=cuenta_origen, fecha=fecha,
                monto=monto, moneda="PEN", tipo="cargo",
                descripcion="Transferencia entre mis cuentas BCP",
                numero_operacion=op,
            )]

    def _parsear_transferencia_terceros(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        monto = self._extraer_monto(texto, [r"Monto transferido\s+S/\s*([\d,]+\.?\d*)"])
        if not monto:
            return []
        destinatario = self._extraer_campo(texto, r"Enviado a\s+([^\n*]+?)(?:\s+\*|$)")
        cuenta_origen = self._resolver_cuenta(texto)
        op = self._extraer_campo(texto, r"Número de operación\s+(\w+)")
        fecha = self._extraer_fecha_bcp(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre=cuenta_origen, fecha=fecha,
            monto=monto, moneda="PEN", tipo="cargo",
            descripcion=f"Transferencia a {destinatario or 'tercero'} (BCP)",
            numero_operacion=op,
        )]

    def _parsear_yapeo_recibido(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        monto = self._extraer_monto(texto, [
            r"yapeo de\s+S/\s*([\d,]+\.?\d*)",
            r"Monto recibido\s+S/\s*([\d,]+\.?\d*)",
        ])
        if not monto:
            return []
        enviado_por = self._extraer_campo(texto, r"Enviado por\s+([^\n]+?)(?:\s+¿|$)")
        fecha = self._extraer_fecha_bcp(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre="BCP Soles",
            fecha=fecha, monto=monto, moneda="PEN", tipo="abono",
            descripcion=f"Yapeo recibido de {enviado_por or 'contacto'}",
        )]

    def _parsear_pago_servicio(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        monto = self._extraer_monto(texto, [r"Monto total:\s+S/\s*([\d,]+\.?\d*)"])
        if not monto:
            return []
        empresa = self._extraer_campo(texto, r"Empresa:\s+([^\n]+?)(?:\s+Servicio|$)")
        cuenta_origen = self._resolver_cuenta(texto)
        op = self._extraer_campo(texto, r"Número de operación:\s+(\w+)")
        fecha = self._extraer_fecha_bcp(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre=cuenta_origen, fecha=fecha,
            monto=monto, moneda="PEN", tipo="cargo",
            descripcion=f"Pago servicio: {empresa or 'Sin datos'}",
            comercio=empresa, numero_operacion=op,
        )]

    @staticmethod
    def _extraer_campo(texto: str, patron: str) -> str | None:
        m = re.search(patron, texto, re.IGNORECASE)
        return m.group(1).strip() if m else None
