# Producto — CRM ligero: Ficha de contacto

**Estado:** 🔄 CRM-1…4 hechos (2026-07-30). Siguiente: CRM-5 reactivación (opcional).  
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
| **CRM-5** | Reactivación inactivos | ⏳ |
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

---

| Fase | Entrega | Riesgo |
|------|---------|--------|
| **CRM-0** | Spec (este doc) | — |
| **CRM-1** | API `GET /contacts/{phone}` o `GET /contacts?phone=` → agrega lead + convs + citas | Bajo (solo lectura) |
| **CRM-2** | Página panel **Contactos** + detalle ficha | Bajo (UI) |
| **CRM-3** | Notas/etiquetas editables (tabla `contacts` o ampliar lead) | Medio |
| **CRM-4** | Al agendar / primer WhatsApp → asegurar lead/contacto | Medio |
| **CRM-5** | (Opcional) “Inactivo N días” + reactivación | Más adelante |
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

### API propuesta (borrador)

```http
GET /contacts?limit=&offset=
GET /contacts/by-phone/{phone}
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

- [ ] Desde el panel abres una persona y ves **chat + citas (+ lead)** juntos.
- [ ] No rompiste E2E Orinoco (WhatsApp → agenda).
- [ ] Un dueño de peluquería entiende la pantalla en &lt; 1 minuto.

Cuando eso esté → ya puedes decir en la oferta: “incluye ficha de clientes”.

---

## 8. Relación con el roadmap actual

| Prioridad | Qué | Bloqueo |
|-----------|-----|---------|
| Externo | Paso 24 — 2º número | Cliente |
| Externo | Paso 21 — plantilla Meta | Meta |
| Producto siguiente | **CRM-1 + CRM-2** (este doc) | Nosotros, cuando digamos play código |
| Aplazado | Hardening secretos | Decisión |
| Después | Caja / n8n CRM externo | Demanda |

---

## 9. Decisión de arranque (checklist antes de codear)

Cuando empecemos implementación, confirmar:

1. ¿CRM-1 solo lectura (agregación) primero? → **Sí (recomendado).**
2. ¿Nombre en menú: “Contactos” o “Clientes finales”? → evitar confusión con tenant “Clientes”.
3. ¿Orinoco usa la misma pantalla para demos? → **Sí.**

**Recomendación de copy en el menú:** `Contactos` (personas).  
`Clientes` = negocios tenants (como ahora).
