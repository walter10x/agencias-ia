import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bot, Building2, ChevronDown, Plus, Wrench } from "lucide-react";
import { fetchClients } from "@/api/client";
import { fetchAgentsByClient } from "@/api/agent";
import AgentForm from "@/components/AgentForm";

export default function AgentsPage() {
  const navigate = useNavigate();
  const [selectedClientId, setSelectedClientId] = useState<string>("");
  const [formOpen, setFormOpen] = useState(false);

  const clientsQuery = useQuery({
    queryKey: ["clients", "all"],
    queryFn: () => fetchClients(200, 0),
  });

  const agentsQuery = useQuery({
    queryKey: ["agents", "client", selectedClientId],
    queryFn: () => fetchAgentsByClient(selectedClientId),
    enabled: !!selectedClientId,
  });

  const clients = clientsQuery.data?.items ?? [];
  const agents = agentsQuery.data?.items ?? [];
  const selectedClient = clients.find((c) => c.id === selectedClientId);

  return (
    <div className="p-6 space-y-6 relative">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <div className="relative z-10">
        <h2 className="text-2xl font-bold text-white">Agentes IA</h2>
        <p className="text-sm text-zinc-500 mt-1">Selecciona un cliente para ver sus agentes</p>
      </div>

      {/* Client Selector */}
      <div className="relative z-10">
        {clientsQuery.isLoading ? (
          <div className="h-12 bg-zinc-900 border border-zinc-800 rounded-xl animate-pulse" />
        ) : clients.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
            <Building2 size={32} className="text-zinc-600 mx-auto mb-4 stroke-[1.5]" />
            <p className="text-sm text-zinc-400 mb-4">Crea un cliente primero para poder crear agentes</p>
            <button
              onClick={() => navigate("/app/clients")}
              className="px-4 py-2 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
            >
              Ir a Clientes
            </button>
          </div>
        ) : (
          <div className="relative">
            <select
              value={selectedClientId}
              onChange={(e) => setSelectedClientId(e.target.value)}
              className="w-full max-w-md appearance-none bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-white text-sm focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
            >
              <option value="" className="bg-zinc-900">Seleccionar cliente...</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id} className="bg-zinc-900">
                  {c.name} ({c.business_type})
                </option>
              ))}
            </select>
            <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
          </div>
        )}
      </div>

      {/* Agents */}
      {selectedClientId && (
        <div className="relative z-10 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">
              {selectedClient?.name}
              {agents.length > 0 && (
                <span className="text-sm font-normal text-zinc-500 ml-2">({agents.length})</span>
              )}
            </h3>
            <button
              onClick={() => setFormOpen(true)}
              className="flex items-center gap-1.5 px-3 py-2 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
            >
              <Plus size={14} /> Nuevo Agente
            </button>
          </div>

          {agentsQuery.isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 animate-pulse">
                  <div className="h-5 w-36 bg-zinc-800 rounded" />
                </div>
              ))}
            </div>
          )}

          {agentsQuery.isError && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400">
              Error al cargar agentes
            </div>
          )}

          {!agentsQuery.isLoading && !agentsQuery.isError && agents.length === 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
              <Bot size={32} className="text-zinc-600 mx-auto mb-4 stroke-[1.5]" />
              <p className="text-sm text-zinc-500 mb-4">Este cliente no tiene agentes</p>
              <button
                onClick={() => setFormOpen(true)}
                className="px-4 py-2 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
              >
                Crear agente
              </button>
            </div>
          )}

          {!agentsQuery.isLoading && !agentsQuery.isError && agents.length > 0 && (
            <div className="space-y-2">
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  onClick={() => navigate(`/app/agents/${agent.id}`)}
                  className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
                        <Bot size={18} className="text-emerald-400 stroke-[1.5]" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-white font-medium truncate">{agent.name}</p>
                        <p className="text-xs text-zinc-500 truncate">{agent.personality.slice(0, 80)}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="flex items-center gap-1 text-xs text-zinc-500">
                        <Wrench size={12} /> {agent.tools.length}
                      </span>
                      <span className={`text-xs px-2.5 py-1 rounded-md ${
                        agent.is_active
                          ? "bg-emerald-500/10 text-emerald-400"
                          : "bg-zinc-800 text-zinc-500"
                      }`}>
                        {agent.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <AgentForm
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        clientId={selectedClientId}
      />
    </div>
  );
}
