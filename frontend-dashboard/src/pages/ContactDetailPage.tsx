import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarDays,
  ContactRound,
  MessageSquare,
  Phone,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { fetchContactByPhone } from "@/api/contact";

const CARD = "bg-zinc-900 border border-zinc-800 rounded-xl";
const BTN2 =
  "inline-flex items-center justify-center gap-2 px-3 py-2 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-xl border border-zinc-700 hover:bg-zinc-700 hover:text-white transition-all";
const BADGE =
  "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium border";

function formatWhen(iso: string | null | undefined) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function ContactDetailPage() {
  const { phone: phoneParam } = useParams<{ phone: string }>();
  const phone = phoneParam ? decodeURIComponent(phoneParam) : "";
  const navigate = useNavigate();

  const query = useQuery({
    queryKey: ["contact", phone],
    queryFn: () => fetchContactByPhone(phone),
    enabled: !!phone,
  });

  if (query.isLoading) {
    return (
      <div className="p-6 lg:p-8 space-y-4">
        <div className={CARD + " p-6 space-y-3"}>
          <div className="skeleton h-8 w-48" />
          <div className="skeleton h-4 w-32" />
        </div>
      </div>
    );
  }

  if (query.error || !query.data) {
    return (
      <div className="p-6 lg:p-8">
        <div className={CARD + " flex flex-col items-center py-16 text-center"}>
          <AlertTriangle size={40} className="text-amber-400 mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Contacto no encontrado</h3>
          <p className="text-sm text-zinc-500 mb-6">No hay lead, chat ni cita para este teléfono.</p>
          <button type="button" onClick={() => navigate("/app/contacts")} className={BTN2}>
            <ArrowLeft size={14} /> Volver a Contactos
          </button>
        </div>
      </div>
    );
  }

  const c = query.data;

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <button
        type="button"
        onClick={() => navigate("/app/contacts")}
        className="inline-flex items-center gap-1.5 px-3 py-2 text-zinc-400 text-sm font-medium rounded-lg hover:bg-zinc-800/50 hover:text-white"
      >
        <ArrowLeft size={14} /> Volver
      </button>

      <div className={CARD + " p-6"}>
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0">
            <ContactRound size={22} />
          </div>
          <div className="min-w-0 space-y-1">
            <h2 className="text-xl font-bold text-white truncate">{c.display_name}</h2>
            <p className="text-sm text-zinc-400 flex items-center gap-1.5">
              <Phone size={13} /> {c.phone}
            </p>
            <p className="text-xs text-zinc-600">Última actividad: {formatWhen(c.last_activity_at)}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className={CARD + " p-5 space-y-3"}>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <FileText size={14} className="text-amber-400" /> Lead / embudo
          </h3>
          {c.lead ? (
            <div className="space-y-2 text-sm">
              <span className={`${BADGE} bg-amber-500/10 text-amber-400 border-amber-500/20`}>
                {c.lead.status}
              </span>
              <p className="text-zinc-400">Score: {c.lead.score}</p>
              {c.lead.notes && <p className="text-zinc-500 text-xs whitespace-pre-wrap">{c.lead.notes}</p>}
              <button
                type="button"
                className={BTN2 + " w-full mt-2"}
                onClick={() => navigate(`/app/leads/${c.lead!.id}`)}
              >
                Abrir lead
              </button>
            </div>
          ) : (
            <p className="text-xs text-zinc-600">Sin lead en embudo.</p>
          )}
        </section>

        <section className={CARD + " p-5 space-y-3"}>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <MessageSquare size={14} className="text-emerald-400" /> Conversaciones
          </h3>
          {c.conversations.length === 0 ? (
            <p className="text-xs text-zinc-600">Sin chats.</p>
          ) : (
            <ul className="space-y-2">
              {c.conversations.map((conv) => (
                <li key={conv.id}>
                  <button
                    type="button"
                    className="w-full text-left px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-zinc-600 text-sm"
                    onClick={() => navigate(`/app/conversations/${conv.id}`)}
                  >
                    <span className="text-white">{conv.status}</span>
                    <span className="block text-xs text-zinc-500 mt-0.5">
                      {formatWhen(conv.updated_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className={CARD + " p-5 space-y-3"}>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <CalendarDays size={14} className="text-blue-400" /> Citas
          </h3>
          {c.appointments.length === 0 ? (
            <p className="text-xs text-zinc-600">Sin citas.</p>
          ) : (
            <ul className="space-y-2">
              {c.appointments.map((a) => (
                <li
                  key={a.id}
                  className="px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-sm"
                >
                  <span className="text-white">{formatWhen(a.starts_at)}</span>
                  <span className="block text-xs text-zinc-500 mt-0.5">{a.status}</span>
                </li>
              ))}
            </ul>
          )}
          <button type="button" className={BTN2 + " w-full"} onClick={() => navigate("/app/appointments")}>
            Ir a Agenda
          </button>
        </section>
      </div>
    </div>
  );
}
