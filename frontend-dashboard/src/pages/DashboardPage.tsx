import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bot, MessageSquare, Users, Loader2, TrendingUp, Sparkles, ArrowRight } from "lucide-react";
import { fetchClients } from "@/api/client";
import PageShell, { EmptyPanel, PageHeader } from "@/components/PageShell";

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

  const btnPrimary = "inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-amber-500 text-black text-xs font-semibold rounded-lg transition-all duration-200 hover:bg-amber-400 active:scale-[0.98]";
  const btnSecondary = "inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-zinc-800 text-zinc-300 text-xs font-medium rounded-lg border border-zinc-700 transition-all duration-200 hover:bg-zinc-700 hover:text-white";

  return (
    <PageShell>
      <PageHeader
        title="Panel de control"
        description="Clientes, agentes y conversaciones en un solo lugar."
        actions={
          <button onClick={() => navigate("/app/clients")} className={btnPrimary}>
            <Users size={14} /> Nuevo cliente
          </button>
        }
      />

      <div className="flex items-center gap-1.5 text-xs text-zinc-500 animate-fade-in">
        <Sparkles size={12} className="text-amber-400" />
        Bienvenido de nuevo
      </div>

      {isError && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2.5 text-xs text-red-400 flex items-center gap-2">
          <span>Error al cargar estadísticas</span>
          <button onClick={() => clientsQuery.refetch()} className="underline hover:text-red-300">Reintentar</button>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
        {stats.map((stat) => (
          <div
            key={stat.title}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-3.5 transition-all duration-200 hover:border-zinc-700"
          >
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${stat.bg} ${stat.text} mb-2.5`}>
              {isLoading ? <Loader2 size={14} className="animate-spin" /> : <stat.icon size={14} />}
            </div>
            <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-0.5">{stat.title}</p>
            <p className="text-xl font-bold text-white tracking-tight">{stat.value}</p>
          </div>
        ))}
      </div>

      {!isLoading && !isError && totalClients === 0 && (
        <EmptyPanel
          icon={Bot}
          title="Comienza a construir tu agencia"
          action={
            <div className="flex items-center justify-center gap-2">
              <button onClick={() => navigate("/app/clients")} className={btnPrimary}><Users size={14} /> Crear cliente</button>
              <button className={btnSecondary}>Documentación</button>
            </div>
          }
        >
          Crea tu primer cliente y configura un agente IA.
        </EmptyPanel>
      )}

      {!isLoading && !isError && totalClients > 0 && (
        <div className="space-y-2.5 animate-fade-in">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Actividad reciente</h3>
            <button onClick={() => navigate("/app/conversations")} className="inline-flex items-center gap-1 px-2 py-1 text-zinc-400 text-xs rounded-md hover:bg-zinc-800/50 hover:text-white">
              Ver todo <ArrowRight size={11} />
            </button>
          </div>
          <EmptyPanel icon={MessageSquare}>
            El panel de actividad estará disponible próximamente.
          </EmptyPanel>
        </div>
      )}
    </PageShell>
  );
}
