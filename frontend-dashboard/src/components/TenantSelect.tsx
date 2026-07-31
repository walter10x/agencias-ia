import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchClients, type ClientData } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";

const SELECT =
  "w-full max-w-sm bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-white text-sm focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors";

interface TenantSelectProps {
  value: string;
  onChange: (clientId: string) => void;
}

/** Selector de negocio solo para superadmin. */
export default function TenantSelect({ value, onChange }: TenantSelectProps) {
  const { user } = useAuth();
  const isSuperadmin = user?.role === "superadmin";

  const clientsQuery = useQuery({
    queryKey: ["clients", "all"],
    queryFn: () => fetchClients(200, 0),
    enabled: isSuperadmin,
  });

  const clients = clientsQuery.data?.items ?? [];

  useEffect(() => {
    if (!isSuperadmin || value || clients.length === 0) return;
    const orinoco = clients.find((c: ClientData) => /orinoco/i.test(c.name));
    onChange(orinoco?.id ?? clients[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo auto-pick inicial
  }, [isSuperadmin, clients, value]);

  if (!isSuperadmin) return null;

  if (clientsQuery.isLoading) {
    return (
      <div className="h-9 w-full max-w-sm bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
    );
  }

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={SELECT}
      aria-label="Seleccionar negocio"
    >
      <option value="">Selecciona un negocio</option>
      {clients.map((c: ClientData) => (
        <option key={c.id} value={c.id}>
          {c.name} — {c.whatsapp_number}
        </option>
      ))}
    </select>
  );
}

export function useTenantClientId() {
  const { user } = useAuth();
  const isSuperadmin = user?.role === "superadmin";
  const [clientId, setClientId] = useState("");
  return {
    isSuperadmin,
    clientId,
    setClientId,
    ready: isSuperadmin ? !!clientId : true,
  };
}
