"""Smoke lifecycle agenda Orinoco: disponib → crear → mis citas → reprogramar → cancelar.

Usa teléfono de prueba +34999900001 para no mezclar con clientes reales.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.infrastructure.ai.tools import execute_tool

CLIENT_ID = "a1111111-1111-1111-1111-111111111111"
PHONE = "+34999900001"
CTX = {
    "id": CLIENT_ID,
    "phone": PHONE,
    "contact_phone": PHONE,
    "contact_name": "Smoke Test",
}


def _next_monday_11() -> str:
    tz = ZoneInfo("Europe/Madrid")
    now = datetime.now(tz)
    days = (0 - now.weekday() + 7) % 7
    if days == 0:
        days = 7
    d = (now + timedelta(days=days)).date()
    return f"{d.isoformat()}T11:00"


def _next_monday_12() -> str:
    return _next_monday_11().replace("T11:00", "T12:00")


async def main() -> None:
    fecha = _next_monday_11()[:10]
    print("1) DISPONIBILIDAD", fecha)
    avail = await execute_tool("consultar_disponibilidad", {"fecha": fecha}, CTX)
    print(avail[:200])
    assert "11:00" in avail, avail

    print("2) AGENDAR", _next_monday_11())
    booked = await execute_tool(
        "agendar_cita",
        {
            "fecha_hora": _next_monday_11(),
            "nombre": "Smoke Test",
            "telefono": PHONE,
            "notas": "smoke lifecycle",
        },
        CTX,
    )
    print(booked)
    assert "agendada correctamente" in booked.lower(), booked

    print("3) MIS CITAS")
    mine = await execute_tool("consultar_mis_citas", {}, CTX)
    print(mine)
    assert "ref=" in mine.lower() or "referencia" in mine.lower() or PHONE[-4:] in mine or "11:00" in mine or "T11" in mine

    print("4) REPROGRAMAR → 12:00")
    moved = await execute_tool(
        "reprogramar_cita",
        {"nueva_fecha_hora": _next_monday_12()},
        CTX,
    )
    print(moved)
    assert "reprogramada" in moved.lower(), moved

    print("5) CANCELAR")
    cancelled = await execute_tool("cancelar_cita", {"referencia": PHONE}, CTX)
    print(cancelled)
    assert "cancelada" in cancelled.lower(), cancelled

    print("6) MIS CITAS tras cancelar")
    mine2 = await execute_tool("consultar_mis_citas", {}, CTX)
    print(mine2)
    assert "no tienes citas" in mine2.lower(), mine2

    print("LIFECYCLE_OK")


if __name__ == "__main__":
    asyncio.run(main())
