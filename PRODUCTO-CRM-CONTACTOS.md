# Producto — CRM ligero: Ficha de contacto

**Estado:** ✅ CRM-0…5 completo (2026-07-30). MVP CRM ligero cerrado.  
**Fuera de alcance (sigue):** Caja; etiquetas dedicadas (notas cubren MVP).  
**Fuente operativa general:** `CONFIGURACION-ECOSISTEMA-COMPLETO.md`.

### Reglas de trabajo (obligatorias)

- Arquitectura **hexagonal** (domain ← application ← infrastructure)
- **TDD** en use cases
- **Clean Code** + **KISS** (notas + ensure lead vía lead; sin tabla `contacts` aún)
- **Seguridad:** JWT + scope `client_id`; validar/normalizar teléfono; sin secretos en logs
- **UI:** menú **Contactos** = personas finales; **Clientes** = negocios tenants (no mezclar)

### Progreso

| Fase | Entrega | Estado |
|------|---------|--------|
| **CRM-0** | Spec + reglas | ✅ |
| **CRM-1** | API agregación por teléfono + lista | ✅ |
| **CRM-2** | Panel Contactos (lista + ficha) | ✅ |
| **CRM-3** | Notas (+ nombre) editables | ✅ |
| **CRM-4** | Auto-vínculo al agendar / primer WA | ✅ |
| **CRM-5** | Filtro inactivos + marcar contactado | ✅ |
| **Caja** | Fuera de alcance | — |
| Etiquetas dedicadas | Columna/tags propios | ⏳ (después; notas cubren MVP) |

---

## 1. Qué vendemos (modelo claro)

| Capa | Nombre | Qué es |
|------|--------|--------|
| Empresa | **Orinoco** | Agencia que vende servicios (IA, webs, IT…) |
| Producto | **Agencia IA** | SaaS multi-tenant: **WhatsApp IA + agenda + panel + CRM ligero** |

**Frase de venta (producto):**

> Bot en tu WhatsApp que atiende y agenda, y un panel donde ves a **tus clientes** (ficha, chats, citas) — sin Excel.

**No vendemos (aún):** caja/contabilidad completa, Salesforce, helpdesk enterprise.

**CRM ligero =** ficha unificada de la **persona final** (quien escribe al negocio), no el tenant (`clients`).

---

## 2. Dos usos del mismo producto (no mezclar)

| Uso | Quién es la “persona” | Embudo |
|-----|----------------------|--------|
| **Orinoco** | Lead que quiere automatización / demo | `leads` (new → converted) muy útil |
| **Peluquería / clínica** | Cliente habitual del local | Ficha + citas + chat; embudo comercial secundario |

Misma plataforma. Misma **Ficha de contacto**. Distinto tono de uso.

---

## 3. Qué ya tenemos (no tirar)

| Módulo actual | Campo clave | Rol en el CRM |
|---------------|-------------|----------------|
| `leads` | `phone` | Embudo + score + notes |
| `conversations` | `wa_phone_number` | Historial de chat |
| `appointments` | `contact_phone` | Historial de servicio / demos |
| `clients` | (tenant) | **No es** la ficha del cliente final |

Hoy: tres sitios. Mañana: **una ficha** que los lee.

---

## 4. Idea central (sin romper nada)

**Clave de unión:** `(client_id del tenant, teléfono E.164 normalizado)`.

```text
Persona / Contacto
  tenant = peluquería X
  phone  = +34600...
     ├── lead? (si existe)
     ├── conversaciones
     ├── citas
     └── notas / etiquetas (nuevo, mínimo)
```

### Qué NO hacemos en la primera entrega

- No reescribimos el bot ni las tools de agenda.
- No borramos `leads` / `conversations` / `appointments`.
- No montamos caja ni n8n obligatorio.
- No migraciones destructivas: la ficha puede ser **vista agregada** al inicio (API que junta datos por teléfono). Persistencia propia de `contacts` solo si hace falta para notas/tags.

### CRM-4 — Auto-vínculo (hecho)

| Evento | Comportamiento |
|--------|----------------|
| Mensaje WhatsApp entrante | `EnsureContactLead` (`source=whatsapp`) tras persistir conversación |
| Cita creada (panel o tool `agendar_cita`) | `EnsureContactLead` (`source=appointment`); teléfono normalizado E.164 |

Idempotente: no duplica leads. Si ya hay lead, solo rellena nombre vacío / `last_contacted_at` en inbound.

### CRM-5 — Reactivación (hecho)

| Pieza | Comportamiento |
|-------|----------------|
| Lista | `GET /contacts?inactive_days=30\|60\|90` — filtra por días sin actividad; cada ítem incluye `inactive_days` |
| UI lista | Chips Todos / 30+ / 60+ / 90+ en **Contactos** |
| Acción | `POST /contacts/by-phone/{phone}/mark-contacted` → lead `contacted` + `last_contacted_at` |
| UI ficha | Botón **Marcar contactado** (tras llamar / escribir fuera del bot) |

---

| Fase | Entrega | Riesgo |
|------|---------|--------|
| **CRM-0** | Spec (este doc) | — |
| **CRM-1** | API agregación lead + convs + citas | Bajo (solo lectura) |
| **CRM-2** | Página panel **Contactos** + detalle ficha | Bajo (UI) |
| **CRM-3** | Notas/nombre editables vía lead | Medio |
| **CRM-4** | Al agendar / primer WhatsApp → asegurar lead | Medio |
| **CRM-5** | Inactivo N días + marcar contactado | Bajo |
| **Caja** | Fuera de este doc | Otro módulo |


---

## 5. Contrato de la Ficha (CRM-1 / CRM-2)

### Datos mostrados

| Bloque | Origen |
|--------|--------|
| Teléfono (E.164) | Parámetro / normalizado |
| Nombre | lead.name o último appointment.contact_name o “—” |
| Estado embudo | lead.status si hay lead |
| Score | lead.score |
| Notas | lead.notes (CRM-3: notes en contact) |
| Último contacto | max(lead.last_contacted_at, último mensaje, última cita) |
| Lista conversaciones | `conversations` del tenant + phone |
| Lista citas | `appointments` del tenant + phone |
| Lead id | link a `/app/leads/:id` si existe |

### API (implementada)

```http
GET  /api/v1/contacts?limit=&offset=&inactive_days=
GET  /api/v1/contacts/by-phone/{phone}
PATCH /api/v1/contacts/by-phone/{phone}/notes
POST /api/v1/contacts/by-phone/{phone}/mark-contacted
```

Respuesta (forma):

```json
{
  "client_id": "...",
  "phone": "+34600111222",
  "display_name": "María",
  "lead": { "id": "...", "status": "interested", "score": 70, "notes": "..." },
  "conversations": [ { "id": "...", "status": "active", "updated_at": "..." } ],
  "appointments": [ { "id": "...", "starts_at": "...", "status": "confirmed" } ],
  "last_activity_at": "..."
}
```

Scoped por tenant (mismo patrón JWT que leads/appointments). Superadmin: solo su tenant o filtro existente.

### UI propuesta

- Ruta: `/app/contacts` (lista) y `/app/contacts/:phone` o por id estable luego.
- Desde conversación / cita / lead: botón **Ver ficha**.
- Lista: teléfono, nombre, última actividad, badge estado.

---

## 6. Normalización de teléfono (regla dura)

Todos los módulos deben comparar el **mismo** E.164 (`+` + país + número).  
Hoy puede haber inconsistencias (`34600…` vs `+34600…`).  
En CRM-1: normalizar al leer (helper único). No hace falta backfill masivo el día 1.

---

## 7. Criterio de “hecho” para empezar a vender la capa CRM

- [x] Desde el panel abres una persona y ves **chat + citas (+ lead)** juntos.
- [x] Notas/nombre editables; auto-lead en WA/cita; filtro inactivos + marcar contactado.
- [x] No rompiste E2E Orinoco (WhatsApp → agenda) al añadir Contactos.
- [x] Copy claro: **Contactos** ≠ **Clientes** (negocios).

Oferta: “incluye ficha de clientes (Contactos)”.

---

## 8. Relación con el roadmap actual

| Prioridad | Qué | Bloqueo |
|-----------|-----|---------|
| Externo | Paso 24 — 2º número | Cliente |
| Externo | Paso 21 — plantilla Meta | Meta |
| Producto | **CRM-0…5** ✅ (este doc) | Hecho |
| Aplazado | Hardening secretos | Decisión |
| Después | Etiquetas dedicadas / Caja / n8n CRM externo | Demanda |

---

## 9. Decisiones tomadas

1. CRM-1 solo lectura primero → luego CRM-3…5.
2. Menú: **Contactos** (personas). **Clientes** = negocios tenants.
3. Orinoco usa la misma pantalla para demos.
4. Persistencia de notas vía `leads` (sin tabla `contacts` en el MVP).
