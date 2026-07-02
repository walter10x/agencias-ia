import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bot, MessageSquare, Users, Zap, Loader2 } from "lucide-react";
import { fetchClients } from "@/api/client";

interface StatCardData {
  title: string;
  value: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
}

export default function DashboardPage() {
  const navigate = useNavigate();

  const clientsQuery = useQuery({
    queryKey: ["clients", "dashboard"],
    queryFn: () => fetchClients(200, 0),
  });

  const totalClients = clientsQuery.data?.items?.length ?? 0;
  const totalAgents = clientsQuery.data?.items
    ? clientsQuery.data.items.reduce(
        (sum, c) => sum + ((c as unknown as { agent_count?: number }).agent_count ?? 0),
        0,
      )
    : 0;

  const isLoading = clientsQuery.isLoading;
  const isError = clientsQuery.error;

  const stats: StatCardData[] = [
    {
      title: "Clientes activos",
      value: isLoading ? "—" : String(totalClients),
      icon: Users,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10",
    },
    {
      title: "Agentes IA",
      value: isLoading ? "—" : String(totalAgents),
      icon: Bot,
      color: "text-emerald-400",
      bgColor: "bg-emerald-500/10",
    },
    {
      title: "Mensajes hoy",
      value: "—",
      icon: MessageSquare,
      color: "text-sky-400",
      bgColor: "bg-sky-500/10",
    },
    {
      title: "Tasa respuesta",
      value: "—",
      icon: Zap,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10",
    },
  ];

  return (
    <div className="p-6 space-y-6 relative">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <div className="relative z-10">
        <h2 className="text-2xl font-bold text-white">Dashboard</h2>
        <p className="text-sm text-zinc-500 mt-1">Resumen de tu agencia de IA</p>
      </div>

      {/* Error Banner */}
      {isError && (
        <div className="relative z-10 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400 flex items-center gap-3">
          <span>Error al cargar estadísticas</span>
          <button onClick={() => clientsQuery.refetch()} className="underline hover:text-red-300">Reintentar</button>
        </div>
      )}

      {/* Stats Grid */}
      <div className="relative z-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.title}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 hover:border-zinc-700 transition-colors group"
          >
            <div className={`w-10 h-10 rounded-lg ${stat.bgColor} flex items-center justify-center mb-3`}>
              {isLoading ? (
                <Loader2 size={20} className="text-amber-500 animate-spin stroke-[1.5]" />
              ) : (
                <stat.icon size={20} className={`${stat.color} stroke-[1.5]`} />
              )}
            </div>
            <p className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{stat.title}</p>
            <p className="mt-1 text-3xl font-bold text-white tracking-tight">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Empty/Placeholder State */}
      {!isLoading && !isError && totalClients === 0 && (
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6">
            <Bot size={32} className="text-amber-500 stroke-[1.5]" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Aún no hay agentes configurados</h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto">
            Crea tu primer cliente, configura un agente IA y conéctalo a WhatsApp para empezar a automatizar respuestas.
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <button
              onClick={() => navigate("/app/clients")}
              className="px-4 py-2 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
            >
              Crear Cliente
            </button>
            <button className="px-4 py-2 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700">
              Ver documentación
            </button>
          </div>
        </div>
      )}

      {/* Has Clients - Activity Placeholder */}
      {!isLoading && !isError && totalClients > 0 && (
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6">
            <Bot size={32} className="text-amber-500 stroke-[1.5]" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Actividad de agentes</h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto">
            El panel de actividad y métricas de conversaciones estará disponible próximamente.
          </p>
        </div>
      )}
    </div>
  );
}
