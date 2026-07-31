import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, ContactRound, MessageSquare, Phone, Search } from "lucide-react";
import { fetchContacts } from "@/api/contact";
import TenantSelect, { useTenantClientId } from "@/components/TenantSelect";
import PageShell, { EmptyPanel, PageHeader } from "@/components/PageShell";

const CARD =
  "bg-zinc-900 border border-zinc-800 rounded-xl transition-all duration-200 hover:border-zinc-700";
const BADGE =
  "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium border";
const FILTER =
  "px-2.5 py-1 text-[11px] font-medium rounded-md border transition-all";

const FILTERS: { label: string; days: number | null }[] = [
  { label: "Todos", days: null },
  { label: "Inactivos 30+ días", days: 30 },
  { label: "60+ días", days: 60 },
  { label: "90+ días", days: 90 },
];

function statusLabel(status: string | null) {
  if (!status) return null;
  const map: Record<string, string> = {
    new: "Nuevo",
    contacted: "Contactado",
    interested: "Interesado",
    not_interested: "No interesado",
    converted: "Convertido",
    archived: "Archivado",
  };
  return map[status] ?? status;
}

function formatWhen(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function ContactsPage() {
  const navigate = useNavigate();
  const [inactiveDays, setInactiveDays] = useState<number | null>(null);
  const { isSuperadmin, clientId, setClientId, ready } = useTenantClientId();

  const query = useQuery({
    queryKey: ["contacts", inactiveDays, clientId],
    queryFn: () =>
      fetchContacts(100, 0, inactiveDays, isSuperadmin ? clientId : undefined),
    enabled: ready,
  });

  const items = query.data?.items ?? [];

  return (
    <PageShell>
      <PageHeader
        title="Contactos"
        description="Personas que escriben o agendan (no confundir con Clientes = negocios)."
      />

      {isSuperadmin && (
        <TenantSelect value={clientId} onChange={setClientId} />
      )}

      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map((f) => {
          const active = inactiveDays === f.days;
          return (
            <button
              key={f.label}
              type="button"
              onClick={() => setInactiveDays(f.days)}
              className={
                FILTER +
                (active
                  ? " bg-amber-500 text-black border-amber-500"
                  : " bg-zinc-900 text-zinc-400 border-zinc-800 hover:border-zinc-600 hover:text-white")
              }
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {!ready && isSuperadmin && (
        <EmptyPanel title="Selecciona un negocio">Para ver sus contactos</EmptyPanel>
      )}

      {ready && query.isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className={CARD + " p-3"}>
              <div className="skeleton h-4 w-36 mb-1.5" />
              <div className="skeleton h-2.5 w-24" />
            </div>
          ))}
        </div>
      )}

      {ready && query.error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2.5 text-xs text-red-400">
          No se pudieron cargar los contactos.{" "}
          <button className="underline" onClick={() => query.refetch()}>
            Reintentar
          </button>
        </div>
      )}

      {ready && !query.isLoading && !query.error && items.length === 0 && (
        <EmptyPanel
          icon={ContactRound}
          title={inactiveDays ? "Nadie inactivo con ese filtro" : "Aún no hay contactos"}
        >
          {inactiveDays
            ? "Prueba otro periodo o vuelve a Todos."
            : "Aparecerán cuando alguien escriba por WhatsApp, sea lead o tenga una cita."}
        </EmptyPanel>
      )}

      {ready && !query.isLoading && items.length > 0 && (
        <div className="space-y-1.5">
          {items.map((c) => (
            <button
              key={c.phone}
              type="button"
              onClick={() => {
                const q =
                  isSuperadmin && clientId
                    ? `?client_id=${encodeURIComponent(clientId)}`
                    : "";
                navigate(`/app/contacts/${encodeURIComponent(c.phone)}${q}`);
              }}
              className={CARD + " w-full p-3 text-left cursor-pointer"}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0 flex items-start gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0">
                    <ContactRound size={15} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm text-white font-medium truncate">{c.display_name}</p>
                    <p className="text-[11px] text-zinc-500 flex items-center gap-1 mt-0.5">
                      <Phone size={9} /> {c.phone}
                    </p>
                    <p className="text-[11px] text-zinc-600 mt-0.5">
                      Última actividad: {formatWhen(c.last_activity_at)}
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 justify-end shrink-0">
                  {c.inactive_days != null && c.inactive_days >= 30 && (
                    <span className={`${BADGE} bg-orange-500/10 text-orange-400 border-orange-500/20`}>
                      {c.inactive_days}d inactivo
                    </span>
                  )}
                  {c.lead_status && (
                    <span className={`${BADGE} bg-amber-500/10 text-amber-400 border-amber-500/20`}>
                      {statusLabel(c.lead_status)}
                    </span>
                  )}
                  {c.has_conversation && (
                    <span className={`${BADGE} bg-emerald-500/10 text-emerald-400 border-emerald-500/20`}>
                      <MessageSquare size={9} /> Chat
                    </span>
                  )}
                  {c.has_appointments && (
                    <span className={`${BADGE} bg-blue-500/10 text-blue-400 border-blue-500/20`}>
                      <CalendarDays size={9} /> Cita
                    </span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {ready && !query.isLoading && items.length > 0 && (
        <p className="text-[11px] text-zinc-600 flex items-center gap-1">
          <Search size={11} /> {query.data?.total ?? items.length} contacto
          {(query.data?.total ?? items.length) === 1 ? "" : "s"}
        </p>
      )}
    </PageShell>
  );
}
