import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock, Loader2, Save } from "lucide-react";
import {
  fetchClientSchedule,
  updateClientSchedule,
  type BusinessHoursData,
} from "@/api/client";
import { useToast } from "@/components/Toast";

const DAYS: { key: string; label: string }[] = [
  { key: "monday", label: "Lunes" },
  { key: "tuesday", label: "Martes" },
  { key: "wednesday", label: "Miércoles" },
  { key: "thursday", label: "Jueves" },
  { key: "friday", label: "Viernes" },
  { key: "saturday", label: "Sábado" },
  { key: "sunday", label: "Domingo" },
];

const CARD =
  "bg-zinc-900 border border-zinc-800 rounded-xl transition-all duration-300 ease-out";
const INPUT =
  "px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-white text-sm placeholder:text-zinc-600 transition-all duration-200 focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/10";
const BTN =
  "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-xl transition-all duration-200 ease-out hover:bg-amber-400 active:scale-[0.98] disabled:opacity-50";

type DayState = { open: boolean; start: string; end: string };

function scheduleToDayState(data: BusinessHoursData): Record<string, DayState> {
  const out: Record<string, DayState> = {};
  for (const { key } of DAYS) {
    const ranges = data.weekly[key] ?? [];
    if (ranges.length > 0) {
      out[key] = { open: true, start: ranges[0][0] ?? "09:00", end: ranges[0][1] ?? "18:00" };
    } else {
      out[key] = { open: false, start: "09:00", end: "18:00" };
    }
  }
  return out;
}

function dayStateToWeekly(days: Record<string, DayState>): Record<string, string[][]> {
  const weekly: Record<string, string[][]> = {};
  for (const { key } of DAYS) {
    const d = days[key];
    weekly[key] = d?.open ? [[d.start, d.end]] : [];
  }
  return weekly;
}

interface BusinessHoursEditorProps {
  clientId: string;
}

export default function BusinessHoursEditor({ clientId }: BusinessHoursEditorProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const scheduleQuery = useQuery({
    queryKey: ["client-schedule", clientId],
    queryFn: () => fetchClientSchedule(clientId),
  });

  const [timezone, setTimezone] = useState("Europe/Madrid");
  const [duration, setDuration] = useState(30);
  const [days, setDays] = useState<Record<string, DayState>>({});
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (scheduleQuery.data && !hydrated) {
      setTimezone(scheduleQuery.data.timezone || "Europe/Madrid");
      setDuration(scheduleQuery.data.appointment_duration_minutes || 30);
      setDays(scheduleToDayState(scheduleQuery.data));
      setHydrated(true);
    }
  }, [scheduleQuery.data, hydrated]);

  const mutation = useMutation({
    mutationFn: () =>
      updateClientSchedule(clientId, {
        timezone: timezone.trim() || "UTC",
        appointment_duration_minutes: duration,
        reminder_offset_minutes: scheduleQuery.data?.reminder_offset_minutes ?? 1440,
        weekly: dayStateToWeekly(days),
      }),
    onSuccess: (data) => {
      toast("success", "Horario guardado");
      queryClient.setQueryData(["client-schedule", clientId], data);
      setDays(scheduleToDayState(data));
    },
    onError: (err: Error) => toast("error", err.message),
  });

  function updateDay(key: string, patch: Partial<DayState>) {
    setDays((prev) => ({ ...prev, [key]: { ...prev[key], ...patch } }));
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    mutation.mutate();
  }

  if (scheduleQuery.isLoading || !hydrated) {
    return (
      <div className={CARD + " p-6 space-y-3"}>
        <div className="skeleton h-6 w-40" />
        <div className="skeleton h-10 w-full" />
        <div className="skeleton h-10 w-full" />
      </div>
    );
  }

  if (scheduleQuery.error) {
    return (
      <div className={CARD + " p-6 text-sm text-red-400"}>
        No se pudo cargar el horario.{" "}
        <button className="underline" onClick={() => scheduleQuery.refetch()}>
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className={CARD + " p-6 space-y-5"}>
      <div className="flex items-center gap-2">
        <Clock size={16} className="text-amber-400" />
        <h3 className="text-lg font-bold text-white tracking-tight">Horario de negocio</h3>
      </div>
      <p className="text-xs text-zinc-500">
        Define días abiertos y duración de cita. Se usa para disponibilidad y demos del agente.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label className="space-y-1.5 block">
          <span className="text-xs text-zinc-400">Zona horaria (IANA)</span>
          <input
            className={INPUT + " w-full"}
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            placeholder="Europe/Madrid"
          />
        </label>
        <label className="space-y-1.5 block">
          <span className="text-xs text-zinc-400">Duración cita (min)</span>
          <input
            type="number"
            min={5}
            max={480}
            className={INPUT + " w-full"}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value) || 30)}
          />
        </label>
      </div>

      <div className="space-y-2">
        {DAYS.map(({ key, label }) => {
          const d = days[key] ?? { open: false, start: "09:00", end: "18:00" };
          return (
            <div
              key={key}
              className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 py-2 border-b border-zinc-800/80 last:border-0"
            >
              <label className="flex items-center gap-2 w-36 shrink-0 text-sm text-zinc-300">
                <input
                  type="checkbox"
                  checked={d.open}
                  onChange={(e) => updateDay(key, { open: e.target.checked })}
                  className="rounded border-zinc-600"
                />
                {label}
              </label>
              {d.open ? (
                <div className="flex items-center gap-2">
                  <input
                    type="time"
                    className={INPUT}
                    value={d.start}
                    onChange={(e) => updateDay(key, { start: e.target.value })}
                  />
                  <span className="text-zinc-500 text-sm">a</span>
                  <input
                    type="time"
                    className={INPUT}
                    value={d.end}
                    onChange={(e) => updateDay(key, { end: e.target.value })}
                  />
                </div>
              ) : (
                <span className="text-xs text-zinc-600">Cerrado</span>
              )}
            </div>
          );
        })}
      </div>

      <button type="submit" disabled={mutation.isPending} className={BTN}>
        {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
        Guardar horario
      </button>
    </form>
  );
}
