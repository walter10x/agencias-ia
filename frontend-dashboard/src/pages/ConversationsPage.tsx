import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Phone, MessageSquare, ArrowRight } from "lucide-react";
import { fetchClients, type ClientData } from "@/api/client";
import { fetchConversations, type ConversationData } from "@/api/conversation";
import Pagination from "@/components/Pagination";
import PageShell, { EmptyPanel, PageHeader } from "@/components/PageShell";

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
    <span className={`text-[10px] px-2 py-0.5 rounded-md ${styles[status] ?? "bg-zinc-800 text-zinc-500"}`}>
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
    <PageShell>
      <PageHeader
        title="Conversaciones"
        description="Chats de WhatsApp con personas (no confundir con Clientes = negocios)"
      />

      <div>
        {clientsQuery.isLoading ? (
          <div className="h-9 w-full max-w-sm bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
        ) : (
          <select
            value={selectedClientId}
            onChange={(e) => { setSelectedClientId(e.target.value); setPage(1); }}
            className="w-full max-w-sm bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-white text-sm focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
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

      {!selectedClientId && (
        <EmptyPanel icon={MessageSquare} title="Selecciona un cliente">
          Elige un negocio para ver sus conversaciones
        </EmptyPanel>
      )}

      {isError && selectedClientId && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2.5 text-xs text-red-400 flex items-center gap-2">
          <span>Error al cargar conversaciones</span>
          <button onClick={() => conversationsQuery.refetch()} className="underline hover:text-red-300">Reintentar</button>
        </div>
      )}

      {isLoading && selectedClientId && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-3 animate-pulse">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 bg-zinc-800 rounded-lg" />
                <div className="space-y-1.5 flex-1">
                  <div className="h-3.5 w-32 bg-zinc-800 rounded" />
                  <div className="h-2.5 w-44 bg-zinc-800 rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && !isError && selectedClientId && conversations.length === 0 && (
        <EmptyPanel icon={MessageSquare} title="No hay conversaciones">
          No hay conversaciones para este cliente
        </EmptyPanel>
      )}

      {!isLoading && !isError && selectedClientId && conversations.length > 0 && (
        <div className="space-y-1.5">
          {conversations.map((conv: ConversationData) => (
            <div
              key={conv.id}
              onClick={() => navigate(`/app/conversations/${conv.id}`)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-3 hover:border-zinc-700 transition-colors cursor-pointer group"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                    <Phone size={14} className="text-amber-400 stroke-[1.5]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm text-white font-medium truncate">{conv.wa_phone_number}</p>
                    <p className="text-[11px] text-zinc-500 mt-0.5 truncate max-w-md">
                      {truncate(conv.last_message, 80)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[11px] text-zinc-500">{getRelativeTime(conv.updated_at)}</span>
                  <StatusBadge status={conv.status} />
                  <ArrowRight size={14} className="text-zinc-600 group-hover:text-zinc-400 transition-colors" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && selectedClientId && conversations.length > 0 && (
        <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
      )}
    </PageShell>
  );
}
