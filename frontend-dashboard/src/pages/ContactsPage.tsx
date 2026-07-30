import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, ContactRound, MessageSquare, Phone, Search } from "lucide-react";
import { fetchContacts } from "@/api/contact";

const CARD =
  "bg-zinc-900 border border-zinc-800 rounded-xl transition-all duration-300 ease-out hover:border-zinc-700 hover:shadow-lg hover:shadow-black/20";
const BADGE =
  "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium border";

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
  const query = useQuery({
    queryKey: ["contacts"],
    queryFn: () => fetchContacts(100, 0),
  });

  const items = query.data?.items ?? [];

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="space-y-1 animate-fade-in">
        <h2 className="text-2xl font-bold text-white tracking-tight">Contactos</h2>
        <p className="text-sm text-zinc-500">
          Personas que escriben o agendan (no confundir con Clientes = negocios).
        </p>
      </div>

      {query.isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className={CARD + " p-4"}>
              <div className="skeleton h-5 w-40 mb-2" />
              <div className="skeleton h-3 w-28" />
            </div>
          ))}
        </div>
      )}

      {query.error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400">
          No se pudieron cargar los contactos.{" "}
          <button className="underline" onClick={() => query.refetch()}>
            Reintentar
          </button>
        </div>
      )}

      {!query.isLoading && !query.error && items.length === 0 && (
        <div className={CARD + " flex flex-col items-center justify-center py-16 text-center"}>
          <ContactRound size={36} className="text-zinc-600 mb-4" />
          <p className="text-white font-medium mb-1">Aún no hay contactos</p>
          <p className="text-sm text-zinc-500 max-w-sm">
            Aparecerán cuando alguien escriba por WhatsApp, sea lead o tenga una cita.
          </p>
        </div>
      )}

      {!query.isLoading && items.length > 0 && (
        <div className="space-y-2">
          {items.map((c) => (
            <button
              key={c.phone}
              type="button"
              onClick={() => navigate(`/app/contacts/${encodeURIComponent(c.phone)}`)}
              className={CARD + " w-full p-4 text-left cursor-pointer"}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0 flex items-start gap-3">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0">
                    <ContactRound size={18} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white font-semibold truncate">{c.display_name}</p>
                    <p className="text-xs text-zinc-500 flex items-center gap-1 mt-0.5">
                      <Phone size={10} /> {c.phone}
                    </p>
                    <p className="text-xs text-zinc-600 mt-1">
                      Última actividad: {formatWhen(c.last_activity_at)}
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5 justify-end shrink-0">
                  {c.lead_status && (
                    <span className={`${BADGE} bg-amber-500/10 text-amber-400 border-amber-500/20`}>
                      {statusLabel(c.lead_status)}
                    </span>
                  )}
                  {c.has_conversation && (
                    <span className={`${BADGE} bg-emerald-500/10 text-emerald-400 border-emerald-500/20`}>
                      <MessageSquare size={10} /> Chat
                    </span>
                  )}
                  {c.has_appointments && (
                    <span className={`${BADGE} bg-blue-500/10 text-blue-400 border-blue-500/20`}>
                      <CalendarDays size={10} /> Cita
                    </span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {!query.isLoading && items.length > 0 && (
        <p className="text-xs text-zinc-600 flex items-center gap-1">
          <Search size={12} /> {query.data?.total ?? items.length} contacto
          {(query.data?.total ?? items.length) === 1 ? "" : "s"}
        </p>
      )}
    </div>
  );
}
