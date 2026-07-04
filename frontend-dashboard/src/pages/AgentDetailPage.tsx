import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Bot, Building2, Edit, Trash2, Loader2, AlertTriangle,
  Wrench, Database, ShieldAlert,
} from "lucide-react";
import { fetchClient } from "@/api/client";
import { fetchAgent, deactivateAgent, deleteAgent } from "@/api/agent";
import AgentForm from "@/components/AgentForm";
import { useToast } from "@/components/Toast";

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [editOpen, setEditOpen] = useState(false);
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const agentQuery = useQuery({
    queryKey: ["agent", id],
    queryFn: () => fetchAgent(id!),
    enabled: !!id,
  });

  const agent = agentQuery.data;

  const clientQuery = useQuery({
    queryKey: ["client", agent?.client_id],
    queryFn: () => fetchClient(agent!.client_id),
    enabled: !!agent?.client_id,
  });

  const deactivateMutation = useMutation({
    mutationFn: () => deactivateAgent(id!),
    onSuccess: () => {
      toast("success", "Agente desactivado");
      queryClient.invalidateQueries({ queryKey: ["agent", id] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: (err: Error) => toast("error", err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteAgent(id!),
    onSuccess: () => {
      toast("success", "Agente eliminado permanentemente");
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      navigate(agent?.client_id ? `/app/clients/${agent.client_id}` : "/app/agents");
    },
    onError: (err: Error) => toast("error", err.message),
  });

  if (agentQuery.isLoading) {
    return (
      <div className="p-6 space-y-6 relative">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
        </div>
        <div className="relative z-10 space-y-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 animate-pulse space-y-4">
            <div className="h-6 w-48 bg-zinc-800 rounded" />
            <div className="h-4 w-64 bg-zinc-800 rounded" />
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 animate-pulse">
            <div className="h-20 bg-zinc-800 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (agentQuery.error || !agent) {
    return (
      <div className="p-6 relative">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
        </div>
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <AlertTriangle size={48} className="text-amber-500 mx-auto mb-4 stroke-[1.5]" />
          <h3 className="text-lg font-semibold text-white mb-2">Agente no encontrado</h3>
          <p className="text-sm text-zinc-500 mb-6">El agente que buscas no existe o fue eliminado.</p>
          <button
            onClick={() => navigate("/app/agents")}
            className="px-4 py-2 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
          >
            Volver a agentes
          </button>
        </div>
      </div>
    );
  }

  const client = clientQuery.data;

  return (
    <div className="p-6 space-y-6 relative">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Back + Agent Info */}
      <div className="relative z-10 space-y-4">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={16} /> Volver
        </button>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <div className="flex items-start justify-between">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                  <Bot size={22} className="text-emerald-400 stroke-[1.5]" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">{agent.name}</h2>
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm text-zinc-400">
                <Building2 size={14} className="text-zinc-500" />
                {clientQuery.isLoading ? (
                  <span className="text-zinc-600">Cargando...</span>
                ) : client ? (
                  <span>{client.name}</span>
                ) : (
                  <span className="text-zinc-600">—</span>
                )}
              </div>
              <span className={`inline-block text-xs px-2.5 py-1 rounded-md ${
                agent.is_active
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "bg-zinc-800 text-zinc-500"
              }`}>
                {agent.is_active ? "Activo" : "Inactivo"}
              </span>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setEditOpen(true)}
                className="flex items-center gap-1.5 px-3 py-2 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
              >
                <Edit size={14} /> Editar
              </button>
              {agent.is_active && (
                <button
                  onClick={() => setConfirmDeactivate(true)}
                  className="flex items-center gap-1.5 px-3 py-2 bg-red-500/10 text-red-400 text-sm font-medium rounded-lg hover:bg-red-500/20 transition-colors border border-red-500/20"
                >
                  <Trash2 size={14} /> Desactivar
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Personality */}
      <div className="relative z-10 space-y-3">
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Personalidad</h3>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <p className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">{agent.personality}</p>
        </div>
      </div>

      {/* Tools */}
      <div className="relative z-10 space-y-3">
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
          Tools {agent.tools.length > 0 && `(${agent.tools.length})`}
        </h3>
        {agent.tools.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
            <Wrench size={24} className="text-zinc-600 mx-auto mb-3 stroke-[1.5]" />
            <p className="text-sm text-zinc-500">Sin tools configuradas</p>
          </div>
        ) : (
          <div className="space-y-2">
            {agent.tools.map((tool, i) => (
              <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Wrench size={14} className="text-amber-400 stroke-[1.5]" />
                  </div>
                  <div className="space-y-1 min-w-0">
                    <p className="text-white font-medium text-sm">{tool.name}</p>
                    <p className="text-xs text-zinc-400">{tool.description}</p>
                    {tool.endpoint && (
                      <p className="text-xs text-zinc-600 font-mono truncate">{tool.endpoint}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Knowledge Base */}
      <div className="relative z-10 space-y-3">
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Knowledge Base</h3>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          {agent.knowledge_base_refs.length === 0 ? (
            <p className="text-sm text-zinc-500">Sin referencias configuradas</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {agent.knowledge_base_refs.map((ref, i) => (
                <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 rounded-lg text-xs text-zinc-300 font-mono">
                  <Database size={12} className="text-zinc-500" />
                  {ref}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Danger Zone */}
      <div className="relative z-10 space-y-3">
        <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider flex items-center gap-2">
          <ShieldAlert size={14} /> Zona peligrosa
        </h3>
        <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-5">
          <p className="text-sm text-zinc-400 mb-4">Eliminar este agente permanentemente. Esta acción no se puede deshacer.</p>
          <button
            onClick={() => setConfirmDelete(true)}
            className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-400 text-sm font-semibold rounded-lg hover:bg-red-500/20 transition-colors border border-red-500/20"
          >
            <Trash2 size={14} /> Eliminar permanentemente
          </button>
        </div>
      </div>

      {/* Agent Form Modal */}
      {editOpen && (
        <AgentForm
          isOpen={editOpen}
          onClose={() => setEditOpen(false)}
          clientId={agent.client_id}
          agent={agent}
        />
      )}

      {/* Deactivate Confirmation Modal */}
      {confirmDeactivate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-[fadeIn_0.15s_ease-out]">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-sm mx-4 shadow-2xl p-6 animate-[fadeIn_0.15s_ease-out]">
            <AlertTriangle size={32} className="text-amber-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white text-center mb-2">¿Desactivar agente?</h3>
            <p className="text-sm text-zinc-400 text-center mb-6">
              El agente dejará de responder mensajes. Puedes reactivarlo después.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDeactivate(false)}
                className="flex-1 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
              >
                Cancelar
              </button>
              <button
                onClick={() => deactivateMutation.mutate()}
                disabled={deactivateMutation.isPending}
                className="flex-1 px-4 py-2.5 bg-red-500/10 text-red-400 text-sm font-semibold rounded-lg hover:bg-red-500/20 transition-colors border border-red-500/20 flex items-center justify-center gap-2"
              >
                {deactivateMutation.isPending && <Loader2 size={16} className="animate-spin" />}
                Desactivar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-[fadeIn_0.15s_ease-out]">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-sm mx-4 shadow-2xl p-6 animate-[fadeIn_0.15s_ease-out]">
            <ShieldAlert size={32} className="text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white text-center mb-2">¿Eliminar permanentemente?</h3>
            <p className="text-sm text-zinc-400 text-center mb-6">
              Esta acción no se puede deshacer. El agente y toda su configuración se perderán para siempre.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDelete(false)}
                className="flex-1 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
              >
                Cancelar
              </button>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="flex-1 px-4 py-2.5 bg-red-500/10 text-red-400 text-sm font-semibold rounded-lg hover:bg-red-500/20 transition-colors border border-red-500/20 flex items-center justify-center gap-2"
              >
                {deleteMutation.isPending && <Loader2 size={16} className="animate-spin" />}
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
