import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X, Loader2, CalendarX2 } from "lucide-react";
import {
  createAppointment,
  fetchAvailability,
  rescheduleAppointment,
  type AppointmentData,
  type AvailabilitySlotData,
} from "@/api/appointment";
import { useToast } from "@/components/Toast";

const INPUT =
  "w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors";

function todayISO(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

interface AppointmentFormProps {
  isOpen: boolean;
  onClose: () => void;
  /** Si viene una cita, el formulario funciona en modo reprogramar. */
  appointment?: AppointmentData;
  onSuccess?: () => void;
}

interface FormErrors {
  contact_phone?: string;
  slot?: string;
}

export default function AppointmentForm({
  isOpen,
  onClose,
  appointment,
  onSuccess,
}: AppointmentFormProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const isReschedule = !!appointment;

  const [date, setDate] = useState(() =>
    appointment ? appointment.starts_at.slice(0, 10) : todayISO(),
  );
  const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlotData | null>(null);
  const [contactName, setContactName] = useState(appointment?.contact_name ?? "");
  const [contactPhone, setContactPhone] = useState(appointment?.contact_phone ?? "");
  const [notes, setNotes] = useState(appointment?.notes ?? "");
  const [errors, setErrors] = useState<FormErrors>({});
  const [apiError, setApiError] = useState("");

  const availabilityQuery = useQuery({
    queryKey: ["availability", date],
    queryFn: () => fetchAvailability(date),
    enabled: isOpen && !!date,
    staleTime: 0,
  });

  const mutation = useMutation({
    mutationFn: () =>
      isReschedule
        ? rescheduleAppointment(appointment!.id, {
            starts_at: selectedSlot!.starts_at,
            ends_at: selectedSlot!.ends_at,
          })
        : createAppointment({
            starts_at: selectedSlot!.starts_at,
            ends_at: selectedSlot!.ends_at,
            contact_phone: contactPhone.trim(),
            contact_name: contactName.trim(),
            notes: notes.trim(),
          }),
    onSuccess: () => {
      toast("success", isReschedule ? "Cita reprogramada" : "Cita creada");
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      queryClient.invalidateQueries({ queryKey: ["availability"] });
      onClose();
      onSuccess?.();
    },
    onError: (err: Error) => {
      setApiError(err.message || "No se pudo guardar la cita");
    },
  });

  function validate(): boolean {
    const e: FormErrors = {};
    if (!selectedSlot) e.slot = "Selecciona una hora disponible";
    if (!isReschedule && contactPhone.trim().length < 5) {
      e.contact_phone = "Mínimo 5 dígitos";
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function handleSubmit(ev: FormEvent) {
    ev.preventDefault();
    setApiError("");
    if (!validate()) return;
    mutation.mutate();
  }

  if (!isOpen) return null;

  const slots = availabilityQuery.data?.slots ?? [];
  const slotMinutes = availabilityQuery.data?.slot_duration_minutes;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-[fadeIn_0.15s_ease-out]">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md mx-4 shadow-2xl animate-[fadeIn_0.15s_ease-out] max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
          <h3 className="text-lg font-semibold text-white">
            {isReschedule ? "Reprogramar cita" : "Nueva cita"}
          </h3>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-white transition-colors"
            aria-label="Cerrar"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {apiError && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-sm text-red-400">
              {apiError}
            </div>
          )}

          {isReschedule && (
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-sm text-zinc-400">
              <p className="text-white font-medium">
                {appointment!.contact_name || appointment!.contact_phone}
              </p>
              <p className="text-xs mt-0.5">
                Cita actual:{" "}
                {new Date(appointment!.starts_at).toLocaleString("es-ES", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
          )}

          {!isReschedule && (
            <>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Nombre del contacto
                </label>
                <input
                  type="text"
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  placeholder="Nombre (opcional)"
                  maxLength={200}
                  className={INPUT}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Teléfono
                </label>
                <input
                  type="text"
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value.replace(/[^\d+]/g, ""))}
                  placeholder="Teléfono del contacto"
                  className={INPUT}
                />
                {errors.contact_phone && (
                  <p className="text-xs text-red-400 mt-1">{errors.contact_phone}</p>
                )}
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">
              Fecha
            </label>
            <input
              type="date"
              value={date}
              min={todayISO()}
              onChange={(e) => {
                setDate(e.target.value);
                setSelectedSlot(null);
              }}
              className={INPUT}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">
              Hora disponible
              {slotMinutes ? (
                <span className="text-zinc-600"> · citas de {slotMinutes} min</span>
              ) : null}
            </label>

            {availabilityQuery.isLoading && (
              <div className="grid grid-cols-4 gap-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="h-9 bg-zinc-800/60 rounded-lg animate-pulse" />
                ))}
              </div>
            )}

            {availabilityQuery.isError && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-sm text-red-400 flex items-center justify-between gap-3">
                <span>No se pudo cargar la disponibilidad</span>
                <button
                  type="button"
                  onClick={() => availabilityQuery.refetch()}
                  className="underline hover:text-red-300 shrink-0"
                >
                  Reintentar
                </button>
              </div>
            )}

            {!availabilityQuery.isLoading && !availabilityQuery.isError && slots.length === 0 && (
              <div className="bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-4 text-sm text-zinc-500 flex items-center gap-3">
                <CalendarX2 size={16} className="text-zinc-600 shrink-0" />
                No hay horas disponibles este día
              </div>
            )}

            {!availabilityQuery.isLoading && !availabilityQuery.isError && slots.length > 0 && (
              <div className="grid grid-cols-4 gap-2 max-h-44 overflow-y-auto pr-1">
                {slots.map((slot) => {
                  const isSelected = selectedSlot?.starts_at === slot.starts_at;
                  return (
                    <button
                      key={slot.starts_at}
                      type="button"
                      onClick={() => setSelectedSlot(slot)}
                      className={`px-2 py-2 rounded-lg text-sm border transition-colors ${
                        isSelected
                          ? "bg-amber-500 text-black border-amber-500 font-semibold"
                          : "bg-zinc-950 text-zinc-300 border-zinc-800 hover:border-amber-500/50"
                      }`}
                    >
                      {slot.label}
                    </button>
                  );
                })}
              </div>
            )}
            {errors.slot && <p className="text-xs text-red-400 mt-1">{errors.slot}</p>}
          </div>

          {!isReschedule && (
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                Notas
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Notas de la cita (opcional)"
                maxLength={2000}
                rows={3}
                className={`${INPUT} resize-none`}
              />
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg border border-zinc-700 hover:bg-zinc-700 hover:text-white transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex-1 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
            >
              {mutation.isPending && <Loader2 size={14} className="animate-spin" />}
              {isReschedule ? "Reprogramar" : "Crear cita"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
