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
import TenantSelect, { useTenantClientId } from "@/components/TenantSelect";
import { useToast } from "@/components/Toast";
import PageShell, { EmptyPanel, PageHeader } from "@/components/PageShell";

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
  const { isSuperadmin, clientId, setClientId, ready } = useTenantClientId();

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
          clientId: isSuperadmin ? clientId : undefined,
        }
      : {
          status: statusFilter || undefined,
          limit: 100,
          clientId: isSuperadmin ? clientId : undefined,
        };

  const appointmentsQuery = useQuery({
    queryKey: [
      "appointments",
      view,
      statusFilter,
      view === "week" ? ymd(weekAnchor) : "list",
      clientId,
    ],
    queryFn: () => fetchAppointments(filters),
    enabled: ready,
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) =>
      cancelAppointment(id, isSuperadmin ? clientId : undefined),
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
    <PageShell>
      <PageHeader
        title="Agenda"
        description="Citas del negocio (superadmin: elige el tenant abajo)"
        actions={
          <button
            onClick={() => {
              setRescheduleTarget(null);
              setFormOpen(true);
            }}
            disabled={!ready}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-amber-500 text-black text-xs font-semibold rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-50"
          >
            <Plus size={14} />
            Nueva cita
          </button>
        }
      />

      {isSuperadmin && <TenantSelect value={clientId} onChange={setClientId} />}

      <div className="flex items-center justify-between flex-wrap gap-2">
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
        <div className="flex items-center justify-center gap-3">
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

      {appointmentsQuery.isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-3 animate-pulse h-16" />
          ))}
        </div>
      )}

      {appointmentsQuery.isError && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2.5 text-xs text-red-400 flex items-center justify-between gap-2">
          <span>No se pudieron cargar las citas.</span>
          <button
            onClick={() => appointmentsQuery.refetch()}
            className="underline hover:text-red-300 shrink-0"
          >
            Reintentar
          </button>
        </div>
      )}

      {!appointmentsQuery.isLoading && !appointmentsQuery.isError && items.length === 0 && (
        <EmptyPanel
          icon={Calendar}
          title="Sin citas"
          action={
            <button
              onClick={() => {
                setRescheduleTarget(null);
                setFormOpen(true);
              }}
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-amber-500 text-black text-xs font-semibold rounded-lg hover:bg-amber-400 transition-colors"
            >
              <Plus size={14} /> Nueva cita
            </button>
          }
        >
          {statusFilter
            ? "No hay citas con este filtro."
            : "El agente las creará por WhatsApp, o puedes añadirlas a mano."}
        </EmptyPanel>
      )}

      {!appointmentsQuery.isLoading && !appointmentsQuery.isError && items.length > 0 && view === "list" && (
        <div className="space-y-4">
          {grouped.map(([day, dayItems]) => (
            <div key={day}>
              <h3 className="text-[10px] font-semibold text-zinc-500 uppercase tracking-widest mb-1.5 capitalize">
                {dayHeading(dayItems[0].starts_at)}
              </h3>
              <div className="space-y-1.5">
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

      {!appointmentsQuery.isLoading && !appointmentsQuery.isError && view === "week" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-2">
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
                className={`bg-zinc-900 border rounded-xl p-2.5 min-h-[100px] ${
                  isToday ? "border-amber-500/40" : "border-zinc-800"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`text-[11px] font-semibold ${isToday ? "text-amber-400" : "text-zinc-400"}`}>
                    {DAY_LABELS[i]} {day.getDate()}
                  </span>
                </div>
                <div className="space-y-1">
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
                      className="w-full text-left bg-zinc-950 border border-zinc-800 rounded-md px-1.5 py-1 hover:border-amber-500/40 transition-colors"
                    >
                      <div className="flex items-center gap-1 text-[10px] text-white font-medium">
                        <Clock size={9} className="text-amber-400/70" />
                        {timeLabel(appt.starts_at)}
                      </div>
                      <p className="text-[10px] text-zinc-400 truncate">
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

      <AppointmentForm
        isOpen={formOpen}
        onClose={() => {
          setFormOpen(false);
          setRescheduleTarget(null);
        }}
        appointment={rescheduleTarget ?? undefined}
        clientId={isSuperadmin ? clientId : undefined}
      />

      {cancelTarget && (
        <div className="modal-overlay">
          <div className="modal-panel">
            <div className="modal-header">
              <h3 className="text-sm font-semibold text-white">Cancelar cita</h3>
              <button
                onClick={() => setCancelTarget(null)}
                className="text-zinc-500 hover:text-white transition-colors"
                aria-label="Cerrar"
              >
                <X size={16} />
              </button>
            </div>
            <div className="modal-body">
              <p className="text-xs text-zinc-400">
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
              <div className="flex gap-2">
                <button
                  onClick={() => setCancelTarget(null)}
                  className="flex-1 px-3 py-2 bg-zinc-800 text-zinc-300 text-xs font-medium rounded-lg border border-zinc-700 hover:bg-zinc-700 hover:text-white transition-colors"
                >
                  Volver
                </button>
                <button
                  onClick={() => cancelMutation.mutate(cancelTarget.id)}
                  disabled={cancelMutation.isPending}
                  className="flex-1 px-3 py-2 bg-red-500 text-white text-xs font-semibold rounded-lg hover:bg-red-400 transition-colors disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
                >
                  {cancelMutation.isPending && <Loader2 size={13} className="animate-spin" />}
                  Cancelar cita
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </PageShell>
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
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-3 flex items-center gap-3 flex-wrap">
      <div className="flex items-center gap-1.5 text-sm text-white font-semibold min-w-[110px]">
        <Clock size={12} className="text-amber-400" />
        {timeLabel(appt.starts_at)}
        <span className="text-zinc-600">–</span>
        <span className="text-zinc-400 font-normal text-xs">{timeLabel(appt.ends_at)}</span>
      </div>

      <div className="flex-1 min-w-[140px]">
        <div className="flex items-center gap-1.5 text-sm text-white">
          <User size={12} className="text-zinc-500" />
          {appt.contact_name || "Sin nombre"}
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-zinc-500 mt-0.5">
          <Phone size={10} />
          {appt.contact_phone}
        </div>
        {appt.notes && <p className="text-[11px] text-zinc-500 mt-0.5 line-clamp-1">{appt.notes}</p>}
      </div>

      <span className={`text-[10px] px-2 py-0.5 rounded-md font-medium ${meta.className}`}>
        {meta.label}
      </span>

      {!isCancelled && (
        <div className="flex items-center gap-1.5">
          <button
            onClick={onReschedule}
            className="px-2.5 py-1 text-[11px] font-medium rounded-md bg-zinc-800 text-zinc-300 border border-zinc-700 hover:text-white hover:bg-zinc-700 transition-colors"
          >
            Reprogramar
          </button>
          <button
            onClick={onCancel}
            className="px-2.5 py-1 text-[11px] font-medium rounded-md text-zinc-400 hover:text-red-400 hover:bg-red-500/5 transition-colors"
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
