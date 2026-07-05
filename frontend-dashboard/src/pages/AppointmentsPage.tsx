import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Calendar,
  CalendarDays,
  List,
  Plus,
  Clock,
  Phone,
  User,
  X,
  Loader2,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import {
  fetchAppointments,
  cancelAppointment,
  type AppointmentData,
  type AppointmentFilters,
} from "@/api/appointment";
import AppointmentForm from "@/components/AppointmentForm";
import { useToast } from "@/components/Toast";

// ---------- helpers de fecha ----------

function ymd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Lunes de la semana que contiene `d`. */
function startOfWeek(d: Date): Date {
  const copy = new Date(d);
  const dow = (copy.getDay() + 6) % 7; // 0 = lunes
  copy.setDate(copy.getDate() - dow);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

function addDays(d: Date, n: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + n);
  return copy;
}

const DAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

const STATUS_META: Record<string, { label: string; className: string }> = {
  pending: { label: "Pendiente", className: "bg-amber-500/10 text-amber-400" },
  confirmed: { label: "Confirmada", className: "bg-emerald-500/10 text-emerald-400" },
  cancelled: { label: "Cancelada", className: "bg-red-500/10 text-red-400" },
  completed: { label: "Completada", className: "bg-blue-500/10 text-blue-400" },
};

function statusMeta(status: string) {
  return STATUS_META[status] ?? { label: status, className: "bg-zinc-800 text-zinc-400" };
}

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

function dayHeading(iso: string): string {
  return new Date(iso).toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

type ViewMode = "list" | "week";

const STATUS_FILTERS = ["", "pending", "confirmed", "completed", "cancelled"] as const;

export default function AppointmentsPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [view, setView] = useState<ViewMode>("list");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [weekAnchor, setWeekAnchor] = useState<Date>(() => startOfWeek(new Date()));
  const [formOpen, setFormOpen] = useState(false);
  const [rescheduleTarget, setRescheduleTarget] = useState<AppointmentData | null>(null);
  const [cancelTarget, setCancelTarget] = useState<AppointmentData | null>(null);

  // En vista semana acotamos por rango; en lista traemos las próximas.
  const filters: AppointmentFilters =
    view === "week"
      ? {
          dateFrom: ymd(weekAnchor),
          dateTo: ymd(addDays(weekAnchor, 7)),
          status: statusFilter || undefined,
          limit: 200,
        }
      : { status: statusFilter || undefined, limit: 100 };

  const appointmentsQuery = useQuery({
    queryKey: ["appointments", view, statusFilter, view === "week" ? ymd(weekAnchor) : "list"],
    queryFn: () => fetchAppointments(filters),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => cancelAppointment(id),
    onSuccess: () => {
      toast("success", "Cita cancelada");
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      setCancelTarget(null);
    },
    onError: (err: Error) => {
      toast("error", err.message || "No se pudo cancelar la cita");
      setCancelTarget(null);
    },
  });

  const items = appointmentsQuery.data?.items ?? [];

  // Agrupar por día (YYYY-MM-DD), ordenado.
  const grouped = groupByDay(items);

  return (
    <div className="p-6 space-y-6 relative">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-white">Agenda</h2>
          <p className="text-sm text-zinc-500 mt-1">Citas de tu negocio</p>
        </div>
        <button
          onClick={() => {
            setRescheduleTarget(null);
            setFormOpen(true);
          }}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
        >
          <Plus size={16} />
          Nueva cita
        </button>
      </div>

      {/* Controls */}
      <div className="relative z-10 flex items-center justify-between flex-wrap gap-3">
        {/* View toggle */}
        <div className="inline-flex bg-zinc-900 border border-zinc-800 rounded-lg p-1">
          <button
            onClick={() => setView("list")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
              view === "list" ? "bg-amber-500 text-black font-semibold" : "text-zinc-400 hover:text-white"
            }`}
          >
            <List size={14} /> Lista
          </button>
          <button
            onClick={() => setView("week")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
              view === "week" ? "bg-amber-500 text-black font-semibold" : "text-zinc-400 hover:text-white"
            }`}
          >
            <CalendarDays size={14} /> Semana
          </button>
        </div>

        {/* Status filter */}
        <div className="inline-flex flex-wrap gap-1.5">
          {STATUS_FILTERS.map((s) => {
            const active = statusFilter === s;
            const label = s === "" ? "Todas" : statusMeta(s).label;
            return (
              <button
                key={s || "all"}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                  active
                    ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                    : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-white"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Week navigation */}
      {view === "week" && (
        <div className="relative z-10 flex items-center justify-center gap-4">
          <button
            onClick={() => setWeekAnchor(addDays(weekAnchor, -7))}
            className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
            aria-label="Semana anterior"
          >
            <ChevronLeft size={18} />
          </button>
          <span className="text-sm text-zinc-300 font-medium">
            {weekAnchor.toLocaleDateString("es-ES", { day: "numeric", month: "short" })} —{" "}
            {addDays(weekAnchor, 6).toLocaleDateString("es-ES", { day: "numeric", month: "short" })}
          </span>
          <button
            onClick={() => setWeekAnchor(addDays(weekAnchor, 7))}
            className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
            aria-label="Semana siguiente"
          >
            <ChevronRight size={18} />
          </button>
          <button
            onClick={() => setWeekAnchor(startOfWeek(new Date()))}
            className="text-xs text-zinc-500 hover:text-amber-400 underline transition-colors"
          >
            Hoy
          </button>
        </div>
      )}

      {/* Loading */}
      {appointmentsQuery.isLoading && (
        <div className="relative z-10 space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 animate-pulse h-20" />
          ))}
        </div>
      )}

      {/* Error */}
      {appointmentsQuery.isError && (
        <div className="relative z-10 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400 flex items-center justify-between gap-3">
          <span>No se pudieron cargar las citas. Revisa tu conexión.</span>
          <button
            onClick={() => appointmentsQuery.refetch()}
            className="underline hover:text-red-300 shrink-0"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Empty */}
      {!appointmentsQuery.isLoading && !appointmentsQuery.isError && items.length === 0 && (
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6">
            <Calendar size={32} className="text-amber-500 stroke-[1.5]" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Sin citas</h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto mb-6">
            {statusFilter
              ? "No hay citas con este filtro."
              : "Aún no tienes citas agendadas. El agente las creará automáticamente por WhatsApp, o puedes añadirlas a mano."}
          </p>
          <button
            onClick={() => {
              setRescheduleTarget(null);
              setFormOpen(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
          >
            <Plus size={16} /> Nueva cita
          </button>
        </div>
      )}

      {/* List view */}
      {!appointmentsQuery.isLoading && !appointmentsQuery.isError && items.length > 0 && view === "list" && (
        <div className="relative z-10 space-y-6">
          {grouped.map(([day, dayItems]) => (
            <div key={day}>
              <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-2 capitalize">
                {dayHeading(dayItems[0].starts_at)}
              </h3>
              <div className="space-y-2">
                {dayItems.map((appt) => (
                  <AppointmentRow
                    key={appt.id}
                    appt={appt}
                    onReschedule={() => {
                      setRescheduleTarget(appt);
                      setFormOpen(true);
                    }}
                    onCancel={() => setCancelTarget(appt)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Week view */}
      {!appointmentsQuery.isLoading && !appointmentsQuery.isError && view === "week" && (
        <div className="relative z-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-3">
          {Array.from({ length: 7 }).map((_, i) => {
            const day = addDays(weekAnchor, i);
            const key = ymd(day);
            const dayItems = items
              .filter((a) => a.starts_at.slice(0, 10) === key)
              .sort((a, b) => a.starts_at.localeCompare(b.starts_at));
            const isToday = key === ymd(new Date());
            return (
              <div
                key={key}
                className={`bg-zinc-900 border rounded-xl p-3 min-h-[120px] ${
                  isToday ? "border-amber-500/40" : "border-zinc-800"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-xs font-semibold ${isToday ? "text-amber-400" : "text-zinc-400"}`}>
                    {DAY_LABELS[i]} {day.getDate()}
                  </span>
                </div>
                <div className="space-y-1.5">
                  {dayItems.length === 0 && (
                    <p className="text-[11px] text-zinc-600">—</p>
                  )}
                  {dayItems.map((appt) => (
                    <button
                      key={appt.id}
                      onClick={() => {
                        setRescheduleTarget(appt);
                        setFormOpen(true);
                      }}
                      className="w-full text-left bg-zinc-950 border border-zinc-800 rounded-lg px-2 py-1.5 hover:border-amber-500/40 transition-colors"
                    >
                      <div className="flex items-center gap-1 text-[11px] text-white font-medium">
                        <Clock size={10} className="text-amber-400/70" />
                        {timeLabel(appt.starts_at)}
                      </div>
                      <p className="text-[11px] text-zinc-400 truncate">
                        {appt.contact_name || appt.contact_phone}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create / reschedule modal */}
      <AppointmentForm
        isOpen={formOpen}
        onClose={() => {
          setFormOpen(false);
          setRescheduleTarget(null);
        }}
        appointment={rescheduleTarget ?? undefined}
      />

      {/* Cancel confirmation */}
      {cancelTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-sm mx-4 shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
              <h3 className="text-lg font-semibold text-white">Cancelar cita</h3>
              <button
                onClick={() => setCancelTarget(null)}
                className="text-zinc-500 hover:text-white transition-colors"
                aria-label="Cerrar"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-zinc-400">
                ¿Seguro que quieres cancelar la cita de{" "}
                <span className="text-white font-medium">
                  {cancelTarget.contact_name || cancelTarget.contact_phone}
                </span>{" "}
                del{" "}
                <span className="text-white font-medium">
                  {new Date(cancelTarget.starts_at).toLocaleString("es-ES", {
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                ?
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setCancelTarget(null)}
                  className="flex-1 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg border border-zinc-700 hover:bg-zinc-700 hover:text-white transition-colors"
                >
                  Volver
                </button>
                <button
                  onClick={() => cancelMutation.mutate(cancelTarget.id)}
                  disabled={cancelMutation.isPending}
                  className="flex-1 px-4 py-2.5 bg-red-500 text-white text-sm font-semibold rounded-lg hover:bg-red-400 transition-colors disabled:opacity-50 inline-flex items-center justify-center gap-2"
                >
                  {cancelMutation.isPending && <Loader2 size={14} className="animate-spin" />}
                  Cancelar cita
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------- subcomponentes ----------

function AppointmentRow({
  appt,
  onReschedule,
  onCancel,
}: {
  appt: AppointmentData;
  onReschedule: () => void;
  onCancel: () => void;
}) {
  const meta = statusMeta(appt.status);
  const isCancelled = appt.status === "cancelled";

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center gap-4 flex-wrap">
      <div className="flex items-center gap-2 text-white font-semibold min-w-[120px]">
        <Clock size={14} className="text-amber-400" />
        {timeLabel(appt.starts_at)}
        <span className="text-zinc-600">–</span>
        <span className="text-zinc-400 font-normal">{timeLabel(appt.ends_at)}</span>
      </div>

      <div className="flex-1 min-w-[160px]">
        <div className="flex items-center gap-1.5 text-sm text-white">
          <User size={13} className="text-zinc-500" />
          {appt.contact_name || "Sin nombre"}
        </div>
        <div className="flex items-center gap-1.5 text-xs text-zinc-500 mt-0.5">
          <Phone size={12} />
          {appt.contact_phone}
        </div>
        {appt.notes && <p className="text-xs text-zinc-500 mt-1 line-clamp-1">{appt.notes}</p>}
      </div>

      <span className={`text-xs px-2.5 py-1 rounded-md font-medium ${meta.className}`}>
        {meta.label}
      </span>

      {!isCancelled && (
        <div className="flex items-center gap-2">
          <button
            onClick={onReschedule}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 text-zinc-300 border border-zinc-700 hover:text-white hover:bg-zinc-700 transition-colors"
          >
            Reprogramar
          </button>
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-xs font-medium rounded-lg text-zinc-400 hover:text-red-400 hover:bg-red-500/5 transition-colors"
          >
            Cancelar
          </button>
        </div>
      )}
    </div>
  );
}

function groupByDay(items: AppointmentData[]): [string, AppointmentData[]][] {
  const map = new Map<string, AppointmentData[]>();
  for (const a of items) {
    const key = a.starts_at.slice(0, 10);
    const arr = map.get(key) ?? [];
    arr.push(a);
    map.set(key, arr);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, arr]) => [
      day,
      arr.sort((x, y) => x.starts_at.localeCompare(y.starts_at)),
    ]);
}
