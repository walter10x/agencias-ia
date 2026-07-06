import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search, Plus, Building2, Phone, Tag, RefreshCw, Users } from "lucide-react";
import { fetchClients, searchClientByWhatsapp, type ClientData } from "@/api/client";
import Pagination from "@/components/Pagination";
import ClientForm from "@/components/ClientForm";

const PAGE_SIZE = 10;

function EmptyState({ icon: Icon, msg, action }: { icon: React.ElementType; msg: string; action?: React.ReactNode }) {
  return (
    <div className="relative z-10 flex flex-col items-center justify-center text-center bg-zinc-900 border border-zinc-800 rounded-xl p-16 animate-scale-in">
      <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mb-6 empty-state-icon">
        <Icon size={28} className="text-amber-400" />
      </div>
      <p className="text-sm text-zinc-500 mb-4">{msg}</p>
      {action}
    </div>
  );
}

const BTN = "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-xl transition-all duration-200 ease-out hover:bg-amber-400 hover:shadow-lg hover:shadow-amber-500/20 active:scale-[0.98]";
const BTN2 = "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-xl border border-zinc-700 transition-all duration-200 ease-out hover:bg-zinc-700 hover:text-white";
const INPUT = "w-full px-4 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-white text-sm placeholder:text-zinc-600 transition-all duration-200 focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/10";

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
    <div className="p-6 lg:p-8 space-y-6">
      <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 animate-fade-in">
        <div className="space-y-1">
          <h2 className="text-2xl font-bold text-white tracking-tight">Clientes</h2>
          <p className="text-sm text-zinc-500">Gestiona los negocios conectados a tu agencia</p>
        </div>
        <button onClick={() => { setEditingClient(undefined); setFormOpen(true); }} className={BTN}><Plus size={16} /> Nuevo Cliente</button>
      </div>

      <div className="relative z-10 flex gap-2 animate-fade-in" style={{ animationDelay: "0.1s" }}>
        <div className="relative flex-1 max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input type="text" value={whatsappSearch} onChange={(e) => setWhatsappSearch(e.target.value.replace(/\D/g, ""))} onKeyDown={(e) => e.key === "Enter" && handleSearch()} placeholder="Buscar por WhatsApp..." className={INPUT + " pl-10"} />
        </div>
        <button onClick={handleSearch} disabled={searchQuery.isFetching} className={BTN2}>{searchQuery.isFetching && <RefreshCw size={14} className="animate-spin" />}Buscar</button>
      </div>

      {isError && (
        <div className="relative z-10 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400 flex items-center gap-3 animate-fade-in">
          <span>Error al cargar clientes</span>
          <button onClick={() => clientsQuery.refetch()} className="underline hover:text-red-300 transition-colors">Reintentar</button>
        </div>
      )}

      {showSearch && (
        <div className="relative z-10 animate-fade-in">
          {searchQuery.isFetching ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6"><div className="skeleton h-10 w-48" /></div>
          ) : searchResult ? (
            <div onClick={() => navigate(`/app/clients/${searchResult.id}`)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 transition-all duration-300 ease-out hover:border-zinc-700 hover:shadow-lg hover:shadow-black/20 cursor-pointer">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center"><Building2 size={18} /></div>
                  <div><p className="text-white font-semibold">{searchResult.name}</p><p className="text-sm text-zinc-500">{searchResult.whatsapp_number}</p></div>
                </div>
                {searchResult.is_active ? <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Activo</span> : <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">Inactivo</span>}
              </div>
            </div>
          ) : searchQuery.isFetched ? (
            <div className="flex flex-col items-center justify-center text-center bg-zinc-900 border border-zinc-800 rounded-xl p-8">
              <Search size={24} className="text-zinc-600 mb-2 empty-state-icon" />
              <p className="text-sm text-zinc-500">No se encontró ningún cliente con ese WhatsApp</p>
            </div>
          ) : null}
        </div>
      )}

      {isLoading && (
        <div className="relative z-10 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4" style={{ animationDelay: `${i * 0.06}s` }}>
              <div className="flex items-center gap-4">
                <div className="skeleton w-10 h-10 rounded-lg" /><div className="space-y-2 flex-1"><div className="skeleton h-4 w-36" /><div className="skeleton h-3 w-24" /></div><div className="skeleton h-6 w-16 rounded-md" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && !isError && clients.length > 0 && !showSearch && (
        <div className="relative z-10 space-y-2">
          {clients.map((client) => (
            <div key={client.id} onClick={() => navigate(`/app/clients/${client.id}`)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 transition-all duration-300 ease-out hover:border-zinc-700 hover:shadow-lg hover:shadow-black/20 cursor-pointer stagger-item">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-110">
                    <Building2 size={18} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white font-semibold truncate">{client.name}</p>
                    <div className="flex items-center gap-3 text-xs text-zinc-500 mt-0.5">
                      <span className="flex items-center gap-1"><Phone size={10} /> {client.whatsapp_number}</span>
                      <span className="flex items-center gap-1"><Tag size={10} /> {client.business_type}</span>
                    </div>
                  </div>
                </div>
                {client.is_active ? <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Activo</span> : <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">Inactivo</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && !isError && clients.length === 0 && !showSearch && (
        <EmptyState icon={Users} msg="Crea tu primer cliente para empezar a configurar agentes IA." action={
          <button onClick={() => { setEditingClient(undefined); setFormOpen(true); }} className={BTN}><Plus size={16} /> Crear primer cliente</button>
        } />
      )}

      {!isLoading && clients.length > 0 && !showSearch && (
        <div className="relative z-10 animate-fade-in"><Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} /></div>
      )}

      <ClientForm isOpen={formOpen} onClose={closeForm} client={editingClient} onSuccess={() => setShowSearch(false)} />
    </div>
  );
}
