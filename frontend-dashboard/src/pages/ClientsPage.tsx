import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search, Plus, Building2, Phone, Tag, RefreshCw, Users } from "lucide-react";
import { fetchClients, searchClientByWhatsapp, type ClientData } from "@/api/client";
import Pagination from "@/components/Pagination";
import ClientForm from "@/components/ClientForm";
import PageShell, { EmptyPanel, PageHeader } from "@/components/PageShell";

const PAGE_SIZE = 10;

const BTN = "inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-amber-500 text-black text-xs font-semibold rounded-lg transition-all duration-200 hover:bg-amber-400 active:scale-[0.98]";
const BTN2 = "inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-zinc-800 text-zinc-300 text-xs font-medium rounded-lg border border-zinc-700 transition-all duration-200 hover:bg-zinc-700 hover:text-white";
const INPUT = "w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-white text-sm placeholder:text-zinc-600 transition-all duration-200 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/10";

export default function ClientsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [whatsappSearch, setWhatsappSearch] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<ClientData | undefined>(undefined);

  const clientsQuery = useQuery({ queryKey: ["clients", page], queryFn: () => fetchClients(PAGE_SIZE, (page - 1) * PAGE_SIZE) });
  const searchQuery = useQuery({ queryKey: ["clients", "search", whatsappSearch], queryFn: () => searchClientByWhatsapp(whatsappSearch), enabled: false });

  const totalPages = clientsQuery.data ? Math.ceil(clientsQuery.data.count / PAGE_SIZE) : 0;

  function handleSearch() { if (!whatsappSearch.trim()) return; setShowSearch(true); searchQuery.refetch(); }
  function closeForm() { setFormOpen(false); setEditingClient(undefined); }

  const isLoading = clientsQuery.isLoading;
  const isError = clientsQuery.error;
  const clients = clientsQuery.data?.items ?? [];
  const searchResult = searchQuery.data?.items?.[0];

  return (
    <PageShell>
      <PageHeader
        title="Clientes"
        description="Negocios conectados a tu agencia"
        actions={
          <button onClick={() => { setEditingClient(undefined); setFormOpen(true); }} className={BTN}>
            <Plus size={14} /> Nuevo
          </button>
        }
      />

      <div className="flex gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input type="text" value={whatsappSearch} onChange={(e) => setWhatsappSearch(e.target.value.replace(/\D/g, ""))} onKeyDown={(e) => e.key === "Enter" && handleSearch()} placeholder="Buscar por WhatsApp..." className={INPUT + " pl-8"} />
        </div>
        <button onClick={handleSearch} disabled={searchQuery.isFetching} className={BTN2}>{searchQuery.isFetching && <RefreshCw size={13} className="animate-spin" />}Buscar</button>
      </div>

      {isError && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2.5 text-xs text-red-400 flex items-center gap-2">
          <span>Error al cargar clientes</span>
          <button onClick={() => clientsQuery.refetch()} className="underline hover:text-red-300">Reintentar</button>
        </div>
      )}

      {showSearch && (
        <div>
          {searchQuery.isFetching ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4"><div className="skeleton h-8 w-40" /></div>
          ) : searchResult ? (
            <div onClick={() => navigate(`/app/clients/${searchResult.id}`)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-3.5 hover:border-zinc-700 cursor-pointer transition-colors">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0"><Building2 size={15} /></div>
                  <div className="min-w-0"><p className="text-sm text-white font-medium truncate">{searchResult.name}</p><p className="text-xs text-zinc-500">{searchResult.whatsapp_number}</p></div>
                </div>
                {searchResult.is_active ? <span className="text-[10px] px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Activo</span> : <span className="text-[10px] px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-400 border border-zinc-700">Inactivo</span>}
              </div>
            </div>
          ) : searchQuery.isFetched ? (
            <EmptyPanel icon={Search}>No se encontró ningún cliente con ese WhatsApp</EmptyPanel>
          ) : null}
        </div>
      )}

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-3">
              <div className="flex items-center gap-3">
                <div className="skeleton w-8 h-8 rounded-lg" /><div className="space-y-1.5 flex-1"><div className="skeleton h-3.5 w-32" /><div className="skeleton h-2.5 w-20" /></div><div className="skeleton h-5 w-14 rounded-md" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && !isError && clients.length > 0 && !showSearch && (
        <div className="space-y-1.5">
          {clients.map((client) => (
            <div key={client.id} onClick={() => navigate(`/app/clients/${client.id}`)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-3 hover:border-zinc-700 cursor-pointer transition-colors stagger-item">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0">
                    <Building2 size={15} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm text-white font-medium truncate">{client.name}</p>
                    <div className="flex items-center gap-2.5 text-[11px] text-zinc-500 mt-0.5">
                      <span className="flex items-center gap-1"><Phone size={9} /> {client.whatsapp_number}</span>
                      <span className="flex items-center gap-1"><Tag size={9} /> {client.business_type}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {client.status === "pending" && (
                    <span className="text-[10px] px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20">Pendiente</span>
                  )}
                  {client.whatsapp_connected && (
                    <span className="text-[10px] px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">WA</span>
                  )}
                  {client.is_active ? (
                    <span className="text-[10px] px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Activo</span>
                  ) : (
                    <span className="text-[10px] px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-400 border border-zinc-700">Inactivo</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && !isError && clients.length === 0 && !showSearch && (
        <EmptyPanel
          icon={Users}
          action={<button onClick={() => { setEditingClient(undefined); setFormOpen(true); }} className={BTN}><Plus size={14} /> Crear primer cliente</button>}
        >
          Crea tu primer cliente para empezar a configurar agentes IA.
        </EmptyPanel>
      )}

      {!isLoading && clients.length > 0 && !showSearch && (
        <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
      )}

      <ClientForm isOpen={formOpen} onClose={closeForm} client={editingClient} onSuccess={() => setShowSearch(false)} />
    </PageShell>
  );
}
