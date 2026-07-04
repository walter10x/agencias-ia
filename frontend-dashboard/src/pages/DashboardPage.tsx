import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bot, MessageSquare, Users, Loader2, TrendingUp, Sparkles, ArrowRight } from "lucide-react";
import { fetchClients } from "@/api/client";

export default function DashboardPage() {
  const navigate = useNavigate();

  const clientsQuery = useQuery({
    queryKey: ["clients", "dashboard"],
    queryFn: () => fetchClients(200, 0),
  });

  const totalClients = clientsQuery.data?.items?.length ?? 0;
  const totalAgents = clientsQuery.data?.items
    ? clientsQuery.data.items.reduce(
        (sum, c) => sum + ((c as unknown as { agent_count?: number }).agent_count ?? 0), 0)
    : 0;

  const isLoading = clientsQuery.isLoading;
  const isError = clientsQuery.error;

  const stats = [
    { title: "Clientes activos", value: isLoading ? "—" : String(totalClients), icon: Users, bg: "bg-amber-500/10", text: "text-amber-400" },
    { title: "Agentes IA", value: isLoading ? "—" : String(totalAgents), icon: Bot, bg: "bg-emerald-500/10", text: "text-emerald-400" },
    { title: "Conversaciones", value: "—", icon: MessageSquare, bg: "bg-blue-500/10", text: "text-blue-400" },
    { title: "Tasa respuesta", value: "—", icon: TrendingUp, bg: "bg-purple-500/10", text: "text-purple-400" },
  ];

  const btnPrimary = "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-xl transition-all duration-200 ease-out hover:bg-amber-400 hover:shadow-lg hover:shadow-amber-500/20 active:scale-[0.98]";
  const btnSecondary = "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-xl border border-zinc-700 transition-all duration-200 ease-out hover:bg-zinc-700 hover:text-white";

  return (
    <div className="p-6 lg:p-8 space-y-8">
      <div className="relative z-10">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div className="space-y-1 animate-fade-in">
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-amber-400" />
              <h2 className="text-lg font-semibold text-white tracking-tight">Bienvenido, Walter</h2>
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight">
              Panel de <span className="text-amber-400">Control</span>
            </h1>
            <p className="text-sm text-zinc-500 max-w-md">Gestiona tus clientes, agentes IA y monitorea todas las conversaciones desde un solo lugar.</p>
          </div>
          <button onClick={() => navigate("/app/clients")} className={btnPrimary + " self-start sm:self-auto animate-slide-right"}>
            <Users size={16} /> Nuevo Cliente
          </button>
        </div>
      </div>

      {isError && (
        <div className="relative z-10 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400 flex items-center gap-3 animate-fade-in">
          <span>Error al cargar estadísticas</span>
          <button onClick={() => clientsQuery.refetch()} className="underline hover:text-red-300 transition-colors">Reintentar</button>
        </div>
      )}

      <div className="relative z-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <div key={stat.title}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 transition-all duration-300 ease-out hover:border-zinc-700 hover:shadow-lg hover:shadow-black/20 hover:-translate-y-0.5 group"
            style={{ animationDelay: `${i * 0.08}s` }}
          >
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${stat.bg} ${stat.text} mb-4 group-hover:scale-110 transition-transform duration-300`}>
              {isLoading ? <Loader2 size={18} className="animate-spin" /> : <stat.icon size={18} />}
            </div>
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">{stat.title}</p>
            <p className="text-2xl lg:text-3xl font-bold text-white tracking-tight">{stat.value}</p>
          </div>
        ))}
      </div>

      {!isLoading && !isError && totalClients === 0 && (
        <div className="relative z-10 flex flex-col items-center justify-center text-center bg-zinc-900 border border-zinc-800 rounded-xl p-16 animate-scale-in">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mb-6 empty-state-icon">
            <Bot size={28} className="text-amber-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Comienza a construir tu agencia</h3>
          <p className="text-sm text-zinc-500 max-w-md mb-6">Crea tu primer cliente, configura un agente IA con personalidad propia.</p>
          <div className="flex items-center justify-center gap-3">
            <button onClick={() => navigate("/app/clients")} className={btnPrimary}><Users size={16} /> Crear Cliente</button>
            <button className={btnSecondary}>Ver documentación</button>
          </div>
        </div>
      )}

      {!isLoading && !isError && totalClients > 0 && (
        <div className="relative z-10 space-y-4 animate-fade-in">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white">Actividad Reciente</h3>
            <button onClick={() => navigate("/app/conversations")} className="inline-flex items-center gap-1.5 px-3 py-2 text-zinc-400 text-xs font-medium rounded-lg transition-all duration-200 hover:bg-zinc-800/50 hover:text-white">
              Ver todo <ArrowRight size={12} />
            </button>
          </div>
          <div className="flex flex-col items-center justify-center text-center bg-zinc-900 border border-zinc-800 rounded-xl p-12">
            <div className="w-16 h-16 rounded-2xl bg-zinc-800 flex items-center justify-center mb-4">
              <MessageSquare size={24} className="text-zinc-500" />
            </div>
            <p className="text-sm text-zinc-500">El panel de actividad estará disponible próximamente.</p>
          </div>
        </div>
      )}
    </div>
  );
}
