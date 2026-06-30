import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Loader2 } from "lucide-react";
import { createClient, updateClient, type ClientData, type ClientCreateInput, type ClientUpdateInput } from "@/api/client";
import { useToast } from "@/components/Toast";

const BUSINESS_TYPES = [
  "peluqueria", "bar", "restaurante", "contador", "fonatero",
  "tienda", "gimnasio", "clinica", "otro",
];

interface ClientFormProps {
  isOpen: boolean;
  onClose: () => void;
  client?: ClientData;
  onSuccess?: () => void;
}

interface FormErrors {
  name?: string;
  business_type?: string;
  whatsapp_number?: string;
}

export default function ClientForm({ isOpen, onClose, client, onSuccess }: ClientFormProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const isEdit = !!client;

  const [name, setName] = useState(client?.name ?? "");
  const [businessType, setBusinessType] = useState(client?.business_type ?? "");
  const [whatsapp, setWhatsapp] = useState(client?.whatsapp_number ?? "");
  const [errors, setErrors] = useState<FormErrors>({});
  const [apiError, setApiError] = useState("");

  const mutation = useMutation({
    mutationFn: isEdit
      ? () => updateClient(client!.id, { name: name.trim(), whatsapp_number: whatsapp.trim() } satisfies ClientUpdateInput)
      : () => createClient({ name: name.trim(), business_type: businessType, whatsapp_number: whatsapp.trim() } satisfies ClientCreateInput),
    onSuccess: () => {
      toast("success", isEdit ? "Cliente actualizado" : "Cliente creado");
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      if (client) queryClient.invalidateQueries({ queryKey: ["client", client.id] });
      onClose();
      onSuccess?.();
    },
    onError: (err: Error) => {
      setApiError(err.message);
    },
  });

  function validate(): boolean {
    const e: FormErrors = {};
    if (!name.trim()) e.name = "El nombre es obligatorio";
    if (!businessType) e.business_type = "Selecciona un tipo";
    if (!/^\d{10,}$/.test(whatsapp.trim())) e.whatsapp_number = "Mínimo 10 dígitos, solo números";
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-[fadeIn_0.15s_ease-out]">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md mx-4 shadow-2xl animate-[fadeIn_0.15s_ease-out]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
          <h3 className="text-lg font-semibold text-white">
            {isEdit ? "Editar cliente" : "Nuevo cliente"}
          </h3>
          <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {apiError && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-sm text-red-400">
              {apiError}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">Nombre</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nombre del negocio"
              maxLength={200}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
            />
            {errors.name && <p className="text-xs text-red-400 mt-1">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">Tipo de negocio</label>
            <select
              value={businessType}
              onChange={(e) => setBusinessType(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
            >
              <option value="" className="bg-zinc-900">Seleccionar tipo...</option>
              {BUSINESS_TYPES.map((bt) => (
                <option key={bt} value={bt} className="bg-zinc-900">{bt}</option>
              ))}
            </select>
            {errors.business_type && <p className="text-xs text-red-400 mt-1">{errors.business_type}</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">WhatsApp</label>
            <input
              type="text"
              value={whatsapp}
              onChange={(e) => setWhatsapp(e.target.value.replace(/\D/g, ""))}
              placeholder="573001234567"
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
            />
            {errors.whatsapp_number && <p className="text-xs text-red-400 mt-1">{errors.whatsapp_number}</p>}
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex-1 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {mutation.isPending && <Loader2 size={16} className="animate-spin" />}
              {isEdit ? "Guardar cambios" : "Crear cliente"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
