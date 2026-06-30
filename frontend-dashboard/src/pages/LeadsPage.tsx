import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Users,
  TrendingUp,
  MessageSquare,
  Target,
  Star,
} from "lucide-react";
import { fetchLeadStats, type LeadStatsData } from "@/api/lead";

export default function LeadsPage() {
  const [selectedClientId, setSelectedClientId] = useState("");

  const statsQuery = useQuery({
    queryKey: ["lead-stats", selectedClientId],
    queryFn: () => fetchLeadStats(selectedClientId),
    enabled: !!selectedClientId.trim(),
  });

  const stats: LeadStatsData | null = statsQuery.data ?? null;

  return (
    <div className="p-6 space-y-6 relative">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Leads</h2>
          <p className="text-sm text-zinc-500 mt-1">
            Pipeline de prospección automática
          </p>
        </div>
      </div>

      {/* Client ID Input */}
      <div className="relative z-10 flex gap-2">
        <div className="relative flex-1 max-w-md">
          <Target
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
          />
          <input
            type="text"
            value={selectedClientId}
            onChange={(e) => setSelectedClientId(e.target.value)}
            placeholder="Ingresa Client ID para ver estadísticas..."
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-10 pr-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
          />
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                <Users size={18} className="text-amber-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats.total}</p>
                <p className="text-xs text-zinc-500">Total Leads</p>
              </div>
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <TrendingUp size={18} className="text-emerald-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {stats.conversion_rate.toFixed(1)}%
                </p>
                <p className="text-xs text-zinc-500">Conversión</p>
              </div>
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <MessageSquare size={18} className="text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {stats.new_today}
                </p>
                <p className="text-xs text-zinc-500">Nuevos Hoy</p>
              </div>
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Star size={18} className="text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {stats.avg_score.toFixed(1)}
                </p>
                <p className="text-xs text-zinc-500">Score Promedio</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Status Breakdown */}
      {stats && (
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-white mb-3">
            Leads por Estado
          </h3>
          <div className="space-y-2">
            {Object.entries(stats.by_status).map(([status, count]) => (
              <div
                key={status}
                className="flex items-center justify-between text-sm"
              >
                <span className="text-zinc-400 capitalize">
                  {status.replace("_", " ")}
                </span>
                <span className="text-white font-medium">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty */}
      {!stats && statsQuery.isFetched && (
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6">
            <Users size={32} className="text-amber-500 stroke-[1.5]" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">
            Sin datos de leads
          </h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto">
            Ingresa un Client ID válido para ver las estadísticas del pipeline
            de prospección.
          </p>
        </div>
      )}

      {/* Loading */}
      {statsQuery.isLoading && (
        <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 animate-pulse"
            >
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 bg-zinc-800 rounded-lg" />
                <div className="space-y-2">
                  <div className="h-6 w-16 bg-zinc-800 rounded" />
                  <div className="h-3 w-20 bg-zinc-800 rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
