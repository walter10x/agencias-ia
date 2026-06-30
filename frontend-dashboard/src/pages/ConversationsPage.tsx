import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Phone, MessageSquare, ArrowRight } from "lucide-react";
import { fetchClients, type ClientData } from "@/api/client";
import { fetchConversations, type ConversationData } from "@/api/conversation";
import Pagination from "@/components/Pagination";

const PAGE_SIZE = 20;

function getRelativeTime(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "ahora";
  if (diffMins < 60) return `hace ${diffMins}m`;
  if (diffHours < 24) return `hace ${diffHours}h`;
  if (diffDays < 7) return `hace ${diffDays}d`;
  return dateStr.slice(0, 10);
}

function truncate(text: string | null, max: number): string {
  if (!text) return "";
  return text.length > max ? text.slice(0, max) + "..." : text;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: "bg-emerald-500/10 text-emerald-400",
    closed: "bg-zinc-800 text-zinc-500",
    archived: "bg-zinc-800 text-zinc-500",
  };
  return (
    <span className={`text-xs px-2.5 py-1 rounded-md ${styles[status] ?? "bg-zinc-800 text-zinc-500"}`}>
      {status === "active" ? "Activo" : status === "closed" ? "Cerrado" : "Archivado"}
    </span>
  );
}

export default function ConversationsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [selectedClientId, setSelectedClientId] = useState<string>("");

  const clientsQuery = useQuery({
    queryKey: ["clients", "all"],
    queryFn: () => fetchClients(200, 0),
  });

  const conversationsQuery = useQuery({
    queryKey: ["conversations", selectedClientId, page],
    queryFn: () => fetchConversations(selectedClientId, PAGE_SIZE, (page - 1) * PAGE_SIZE),
    enabled: !!selectedClientId,
  });

  const clients = clientsQuery.data?.items ?? [];
  const isLoading = conversationsQuery.isLoading;
  const isError = conversationsQuery.error;
  const conversations = conversationsQuery.data?.items ?? [];
  const totalCount = conversationsQuery.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  return (
    <div className="p-6 space-y-6 relative">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <div className="relative z-10">
        <h2 className="text-2xl font-bold text-white">Conversaciones</h2>
        <p className="text-sm text-zinc-500 mt-1">Historial de conversaciones con clientes</p>
      </div>

      {/* Client Selector */}
      <div className="relative z-10">
        {clientsQuery.isLoading ? (
          <div className="h-10 w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
        ) : (
          <select
            value={selectedClientId}
            onChange={(e) => { setSelectedClientId(e.target.value); setPage(1); }}
            className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
          >
            <option value="">Selecciona un cliente</option>
            {clients.map((c: ClientData) => (
              <option key={c.id} value={c.id}>
                {c.name} — {c.whatsapp_number}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* No client selected */}
      {!selectedClientId && (
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6">
            <MessageSquare size={32} className="text-amber-500 stroke-[1.5]" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Selecciona un cliente</h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto">
            Elige un cliente para ver sus conversaciones
          </p>
        </div>
      )}

      {/* Error */}
      {isError && selectedClientId && (
        <div className="relative z-10 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400 flex items-center gap-3">
          <span>Error al cargar conversaciones</span>
          <button onClick={() => conversationsQuery.refetch()} className="underline hover:text-red-300">Reintentar</button>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && selectedClientId && (
        <div className="relative z-10 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 animate-pulse">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 bg-zinc-800 rounded-lg" />
                <div className="space-y-2 flex-1">
                  <div className="h-4 w-36 bg-zinc-800 rounded" />
                  <div className="h-3 w-48 bg-zinc-800 rounded" />
                </div>
                <div className="h-6 w-16 bg-zinc-800 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && selectedClientId && conversations.length === 0 && (
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6">
            <MessageSquare size={32} className="text-amber-500 stroke-[1.5]" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">No hay conversaciones</h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto">
            No hay conversaciones para este cliente
          </p>
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && selectedClientId && conversations.length > 0 && (
        <div className="relative z-10 space-y-2">
          {conversations.map((conv: ConversationData) => (
            <div
              key={conv.id}
              onClick={() => navigate(`/conversations/${conv.id}`)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                    <Phone size={18} className="text-amber-400 stroke-[1.5]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white font-medium truncate">{conv.wa_phone_number}</p>
                    <p className="text-xs text-zinc-500 mt-0.5 truncate max-w-md">
                      {truncate(conv.last_message, 80)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-zinc-500">{getRelativeTime(conv.updated_at)}</span>
                  <StatusBadge status={conv.status} />
                  <ArrowRight size={16} className="text-zinc-600 group-hover:text-zinc-400 transition-colors" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && selectedClientId && conversations.length > 0 && (
        <div className="relative z-10">
          <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}
