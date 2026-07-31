import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarDays,
  ContactRound,
  MessageSquare,
  Phone,
  FileText,
  AlertTriangle,
  Loader2,
  Save,
  UserCheck,
} from "lucide-react";
import { fetchContactByPhone, updateContactNotes, markContactContacted } from "@/api/contact";
import { useToast } from "@/components/Toast";

const CARD = "bg-zinc-900 border border-zinc-800 rounded-xl";
const BTN =
  "inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-amber-500 text-black text-xs font-semibold rounded-lg hover:bg-amber-400 transition-all disabled:opacity-50";
const BTN2 =
  "inline-flex items-center justify-center gap-1.5 px-2.5 py-1.5 bg-zinc-800 text-zinc-300 text-xs font-medium rounded-lg border border-zinc-700 hover:bg-zinc-700 hover:text-white transition-all";
const INPUT =
  "w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-white text-sm placeholder:text-zinc-600 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/10";
const BADGE =
  "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium border";

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
  const [searchParams] = useSearchParams();
  const tenantClientId = searchParams.get("client_id");
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const query = useQuery({
    queryKey: ["contact", phone, tenantClientId],
    queryFn: () => fetchContactByPhone(phone, tenantClientId),
    enabled: !!phone,
  });

  const [displayName, setDisplayName] = useState("");
  const [notes, setNotes] = useState("");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (query.data && !hydrated) {
      setDisplayName(query.data.display_name || "");
      setNotes(query.data.lead?.notes || "");
      setHydrated(true);
    }
  }, [query.data, hydrated]);

  useEffect(() => {
    setHydrated(false);
  }, [phone, tenantClientId]);

  const mutation = useMutation({
    mutationFn: () =>
      updateContactNotes(
        phone,
        {
          notes,
          display_name: displayName.trim() || null,
        },
        tenantClientId,
      ),
    onSuccess: (data) => {
      toast("success", "Notas guardadas");
      queryClient.setQueryData(["contact", phone, tenantClientId], data);
      setDisplayName(data.display_name);
      setNotes(data.lead?.notes || "");
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
    onError: (err: Error) => toast("error", err.message),
  });

  const markMutation = useMutation({
    mutationFn: () => markContactContacted(phone, tenantClientId),
    onSuccess: (data) => {
      toast("success", "Marcado como contactado");
      queryClient.setQueryData(["contact", phone, tenantClientId], data);
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
    onError: (err: Error) => toast("error", err.message),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    mutation.mutate();
  }

  const inactiveDays = (() => {
    if (!query.data?.last_activity_at) return null;
    const last = new Date(query.data.last_activity_at).getTime();
    if (Number.isNaN(last)) return null;
    return Math.max(0, Math.floor((Date.now() - last) / (1000 * 60 * 60 * 24)));
  })();

  if (query.isLoading) {
    return (
      <div className="page-shell">
        <div className={CARD + " p-6 space-y-3"}>
          <div className="skeleton h-8 w-48" />
          <div className="skeleton h-4 w-32" />
        </div>
      </div>
    );
  }

  if (query.error || !query.data) {
    return (
      <div className="page-shell">
        <div className={CARD + " flex flex-col items-center py-8 text-center"}>
          <AlertTriangle size={22} className="text-amber-400 mb-3" />
          <h3 className="text-sm font-semibold text-white mb-1">Contacto no encontrado</h3>
          <p className="text-xs text-zinc-500 mb-4">No hay lead, chat ni cita para este teléfono.</p>
          <button type="button" onClick={() => navigate("/app/contacts")} className={BTN2}>
            <ArrowLeft size={14} /> Volver a Contactos
          </button>
        </div>
      </div>
    );
  }

  const c = query.data;

  return (
    <div className="page-shell">
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
            {inactiveDays != null && inactiveDays >= 30 && (
              <p className="text-xs text-orange-400 mt-1">{inactiveDays} días sin actividad</p>
            )}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => markMutation.mutate()}
            disabled={markMutation.isPending}
            className={BTN2}
          >
            {markMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <UserCheck size={14} />
            )}
            Marcar contactado
          </button>
          <p className="text-xs text-zinc-600 self-center">
            Tras llamar o escribir por Business App / WhatsApp.
          </p>
        </div>
      </div>

      <form onSubmit={onSubmit} className={CARD + " p-5 space-y-4"}>
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <FileText size={14} className="text-amber-400" /> Notas del contacto
        </h3>
        <p className="text-xs text-zinc-500">
          Nombre y notas visibles en la ficha. Se guardan en el lead (si no existe, se crea).
        </p>
        <label className="block space-y-1.5">
          <span className="text-xs text-zinc-400">Nombre</span>
          <input
            className={INPUT}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={200}
            placeholder="Ej. María García"
          />
        </label>
        <label className="block space-y-1.5">
          <span className="text-xs text-zinc-400">Notas</span>
          <textarea
            className={INPUT + " min-h-[120px] resize-y"}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={5000}
            placeholder="Preferencias, alergias, historial breve…"
          />
        </label>
        <button type="submit" disabled={mutation.isPending} className={BTN}>
          {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Guardar notas
        </button>
      </form>

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
              <button
                type="button"
                className={BTN2 + " w-full mt-2"}
                onClick={() => navigate(`/app/leads/${c.lead!.id}`)}
              >
                Abrir lead
              </button>
            </div>
          ) : (
            <p className="text-xs text-zinc-600">Sin lead en embudo (al guardar notas se crea).</p>
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
