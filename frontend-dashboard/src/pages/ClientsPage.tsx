import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search, Plus, Building2, Phone, Tag, RefreshCw } from "lucide-react";
import { fetchClients, searchClientByWhatsapp, type ClientData } from "@/api/client";
import Pagination from "@/components/Pagination";
import ClientForm from "@/components/ClientForm";

const PAGE_SIZE = 10;

export default function ClientsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [whatsappSearch, setWhatsappSearch] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<ClientData | undefined>(undefined);

  const clientsQuery = useQuery({
    queryKey: ["clients", page],
    queryFn: () => fetchClients(PAGE_SIZE, (page - 1) * PAGE_SIZE),
  });

  const searchQuery = useQuery({
    queryKey: ["clients", "search", whatsappSearch],
    queryFn: () => searchClientByWhatsapp(whatsappSearch),
    enabled: false,
  });

  const totalPages = clientsQuery.data
    ? Math.ceil(clientsQuery.data.count / PAGE_SIZE)
    : 0;

  function handleSearch() {
    if (!whatsappSearch.trim()) return;
    setShowSearch(true);
    searchQuery.refetch();
  }

  function closeForm() {
    setFormOpen(false);
    setEditingClient(undefined);
  }

  const isLoading = clientsQuery.isLoading;
  const isError = clientsQuery.error;
  const clients = clientsQuery.data?.items ?? [];
  const searchResult = searchQuery.data?.items?.[0];

  return (
    <div className="p-6 space-y-6 relative">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Clientes</h2>
          <p className="text-sm text-zinc-500 mt-1">Gestiona los negocios conectados</p>
        </div>
        <button
          onClick={() => { setEditingClient(undefined); setFormOpen(true); }}
          className="flex items-center gap-2 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
        >
          <Plus size={16} /> Nuevo Cliente
        </button>
      </div>

      {/* Search */}
      <div className="relative z-10 flex gap-2">
        <div className="relative flex-1 max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            value={whatsappSearch}
            onChange={(e) => setWhatsappSearch(e.target.value.replace(/\D/g, ""))}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Buscar por WhatsApp..."
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-10 pr-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
          />
        </div>
        <button
          onClick={handleSearch}
          disabled={searchQuery.isFetching}
          className="px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700 flex items-center gap-2"
        >
          {searchQuery.isFetching && <RefreshCw size={14} className="animate-spin" />}
          Buscar
        </button>
      </div>

      {/* Error */}
      {isError && (
        <div className="relative z-10 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400 flex items-center gap-3">
          <span>Error al cargar clientes</span>
          <button onClick={() => clientsQuery.refetch()} className="underline hover:text-red-300">Reintentar</button>
        </div>
      )}

      {/* Search Result */}
      {showSearch && (
        <div className="relative z-10">
          {searchQuery.isFetching ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
              <div className="h-6 w-48 bg-zinc-800 animate-pulse rounded" />
            </div>
          ) : searchResult ? (
            <div
              onClick={() => navigate(`/clients/${searchResult.id}`)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white font-medium">{searchResult.name}</p>
                  <p className="text-sm text-zinc-500">{searchResult.whatsapp_number}</p>
                </div>
                <span className={`text-xs px-2 py-1 rounded-md ${
                  searchResult.is_active
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-zinc-800 text-zinc-500"
                }`}>
                  {searchResult.is_active ? "Activo" : "Inactivo"}
                </span>
              </div>
            </div>
          ) : searchQuery.isFetched ? (
            <p className="text-sm text-zinc-500">No se encontró ningún cliente con ese WhatsApp</p>
          ) : null}
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="relative z-10 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 animate-pulse">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 bg-zinc-800 rounded-lg" />
                <div className="space-y-2 flex-1">
                  <div className="h-4 w-36 bg-zinc-800 rounded" />
                  <div className="h-3 w-24 bg-zinc-800 rounded" />
                </div>
                <div className="h-6 w-16 bg-zinc-800 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && clients.length > 0 && !showSearch && (
        <div className="relative z-10 space-y-2">
          {clients.map((client) => (
            <div
              key={client.id}
              onClick={() => navigate(`/clients/${client.id}`)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                    <Building2 size={18} className="text-amber-400 stroke-[1.5]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white font-medium truncate">{client.name}</p>
                    <div className="flex items-center gap-3 text-xs text-zinc-500 mt-0.5">
                      <span className="flex items-center gap-1">
                        <Phone size={11} /> {client.whatsapp_number}
                      </span>
                      <span className="flex items-center gap-1">
                        <Tag size={11} /> {client.business_type}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2.5 py-1 rounded-md ${
                    client.is_active
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "bg-zinc-800 text-zinc-500"
                  }`}>
                    {client.is_active ? "Activo" : "Inactivo"}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && clients.length === 0 && !showSearch && (
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6">
            <Building2 size={32} className="text-amber-500 stroke-[1.5]" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">No hay clientes aún</h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto mb-6">
            Crea tu primer cliente para empezar a configurar agentes IA y automatizar conversaciones.
          </p>
          <button
            onClick={() => { setEditingClient(undefined); setFormOpen(true); }}
            className="px-4 py-2 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
          >
            Crear primer cliente
          </button>
        </div>
      )}

      {/* Pagination */}
      {!isLoading && clients.length > 0 && !showSearch && (
        <div className="relative z-10">
          <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
      )}

      {/* Client Form Modal */}
      <ClientForm
        isOpen={formOpen}
        onClose={closeForm}
        client={editingClient}
        onSuccess={() => { setShowSearch(false); }}
      />
    </div>
  );
}
