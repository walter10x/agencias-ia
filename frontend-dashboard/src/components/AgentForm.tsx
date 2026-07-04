import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Loader2, Plus, Trash2 } from "lucide-react";
import { createAgent, updateAgent, type AgentData, type AgentToolData, type AgentCreateInput, type AgentUpdateInput } from "@/api/agent";
import { useToast } from "@/components/Toast";

interface AgentFormProps {
  isOpen: boolean;
  onClose: () => void;
  clientId: string;
  agent?: AgentData;
  onSuccess?: () => void;
}

interface ToolRow {
  key: string;
  name: string;
  description: string;
  endpoint: string;
}

interface FormErrors {
  name?: string;
  personality?: string;
}

function emptyTool(): ToolRow {
  return { key: crypto.randomUUID(), name: "", description: "", endpoint: "" };
}

export default function AgentForm({ isOpen, onClose, clientId, agent, onSuccess }: AgentFormProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const isEdit = !!agent;

  const [name, setName] = useState(agent?.name ?? "");
  const [personality, setPersonality] = useState(agent?.personality ?? "");
  const [tools, setTools] = useState<ToolRow[]>(
    agent?.tools.length
      ? agent.tools.map((t) => ({ ...t, key: crypto.randomUUID() }))
      : [emptyTool()],
  );
  const [kbRefs, setKbRefs] = useState(agent?.knowledge_base_refs?.join(", ") ?? "");
  const [errors, setErrors] = useState<FormErrors>({});
  const [apiError, setApiError] = useState("");

  const mutation = useMutation({
    mutationFn: isEdit
      ? () => {
          const toolsData: AgentToolData[] = tools
            .filter((t) => t.name.trim() && t.description.trim())
            .map((t) => ({ name: t.name.trim(), description: t.description.trim(), endpoint: t.endpoint.trim() }));
          return updateAgent(agent!.id, {
            name: name.trim(),
            personality: personality.trim(),
            tools: toolsData,
            knowledge_base_refs: kbRefs.split(",").map((s) => s.trim()).filter(Boolean),
          } satisfies AgentUpdateInput);
        }
      : () => {
          const toolsData: AgentToolData[] = tools
            .filter((t) => t.name.trim() && t.description.trim())
            .map((t) => ({ name: t.name.trim(), description: t.description.trim(), endpoint: t.endpoint.trim() }));
          return createAgent(clientId, {
            name: name.trim(),
            personality: personality.trim(),
            tools: toolsData,
            knowledge_base_refs: kbRefs.split(",").map((s) => s.trim()).filter(Boolean),
          } satisfies AgentCreateInput);
        },
    onSuccess: () => {
      toast("success", isEdit ? "Agente actualizado" : "Agente creado");
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      if (agent) queryClient.invalidateQueries({ queryKey: ["agent", agent.id] });
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
    if (personality.trim().length < 10) e.personality = "Mínimo 10 caracteres";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function handleSubmit(ev: FormEvent) {
    ev.preventDefault();
    setApiError("");
    if (!validate()) return;
    mutation.mutate();
  }

  function addTool() {
    setTools((prev) => [...prev, emptyTool()]);
  }

  function removeTool(key: string) {
    setTools((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((t) => t.key !== key);
    });
  }

  function updateTool(key: string, field: keyof ToolRow, value: string) {
    setTools((prev) => prev.map((t) => (t.key === key ? { ...t, [field]: value } : t)));
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-[fadeIn_0.15s_ease-out]">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto shadow-2xl animate-[fadeIn_0.15s_ease-out]">
        <div className="sticky top-0 bg-zinc-900 flex items-center justify-between px-6 py-4 border-b border-zinc-800 rounded-t-2xl">
          <h3 className="text-lg font-semibold text-white">
            {isEdit ? "Editar agente" : "Nuevo agente"}
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
              placeholder="Nombre del agente"
              maxLength={200}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
            />
            {errors.name && <p className="text-xs text-red-400 mt-1">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">Personalidad</label>
            <textarea
              value={personality}
              onChange={(e) => setPersonality(e.target.value)}
              placeholder="Eres un asistente amable que..."
              rows={4}
              maxLength={5000}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors resize-y"
            />
            {errors.personality && <p className="text-xs text-red-400 mt-1">{errors.personality}</p>}
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-zinc-400">Tools</label>
              <button
                type="button"
                onClick={addTool}
                className="flex items-center gap-1 text-xs text-amber-500 hover:text-amber-400 transition-colors"
              >
                <Plus size={14} /> Añadir tool
              </button>
            </div>
            <div className="space-y-3">
              {tools.map((tool) => (
                <div key={tool.key} className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={tool.name}
                      onChange={(e) => updateTool(tool.key, "name", e.target.value)}
                      placeholder="Nombre (ej: book_appointment)"
                      className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-2 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 outline-none transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => removeTool(tool.key)}
                      className="p-2 text-zinc-500 hover:text-red-400 transition-colors shrink-0"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <input
                    type="text"
                    value={tool.description}
                    onChange={(e) => updateTool(tool.key, "description", e.target.value)}
                    placeholder="Descripción"
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-2 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 outline-none transition-colors"
                  />
                  <input
                    type="text"
                    value={tool.endpoint}
                    onChange={(e) => updateTool(tool.key, "endpoint", e.target.value)}
                    placeholder="Endpoint (opcional) https://..."
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-2 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 outline-none transition-colors font-mono"
                  />
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">Knowledge Base Refs (opcional)</label>
            <input
              type="text"
              value={kbRefs}
              onChange={(e) => setKbRefs(e.target.value)}
              placeholder="kb-precios, kb-faq-general"
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
            />
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
              {isEdit ? "Guardar cambios" : "Crear agente"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
