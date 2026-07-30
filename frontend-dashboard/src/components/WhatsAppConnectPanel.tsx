import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link2, Link2Off, Loader2, MessageCircle } from "lucide-react";
import {
  connectClientWhatsapp,
  disconnectClientWhatsapp,
  type ClientData,
} from "@/api/client";
import { useToast } from "@/components/Toast";

const CARD =
  "bg-zinc-900 border border-zinc-800 rounded-xl transition-all duration-300 ease-out";
const INPUT =
  "w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-white text-sm placeholder:text-zinc-600 transition-all duration-200 focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/10";
const BTN =
  "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-xl transition-all duration-200 ease-out hover:bg-amber-400 active:scale-[0.98] disabled:opacity-50";
const BTN2 =
  "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-xl border border-zinc-700 transition-all duration-200 ease-out hover:bg-zinc-700 hover:text-white disabled:opacity-50";
const BTND =
  "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-red-500/10 text-red-400 text-sm font-semibold rounded-xl border border-red-500/20 transition-all duration-200 ease-out hover:bg-red-500/20 disabled:opacity-50";
const BADGE_OK =
  "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
const BADGE_MUT =
  "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700";

interface WhatsAppConnectPanelProps {
  client: ClientData;
  canManage: boolean;
}

export default function WhatsAppConnectPanel({ client, canManage }: WhatsAppConnectPanelProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [phoneNumberId, setPhoneNumberId] = useState(client.phone_number_id || client.whatsapp_number || "");
  const [accessToken, setAccessToken] = useState("");
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const connected = Boolean(client.whatsapp_connected);

  const connectMutation = useMutation({
    mutationFn: () =>
      connectClientWhatsapp(client.id, {
        phone_number_id: phoneNumberId.trim(),
        access_token: accessToken.trim(),
      }),
    onSuccess: (data) => {
      toast("success", "WhatsApp conectado");
      setAccessToken("");
      queryClient.setQueryData(["client", client.id], (prev: ClientData | undefined) =>
        prev
          ? {
              ...prev,
              whatsapp_connected: data.whatsapp_connected,
              phone_number_id: phoneNumberId.trim(),
              status: data.status,
            }
          : prev,
      );
      queryClient.invalidateQueries({ queryKey: ["client", client.id] });
      queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
    onError: (err: Error) => toast("error", err.message),
  });

  const disconnectMutation = useMutation({
    mutationFn: () => disconnectClientWhatsapp(client.id),
    onSuccess: () => {
      toast("success", "WhatsApp desconectado");
      setConfirmDisconnect(false);
      queryClient.invalidateQueries({ queryKey: ["client", client.id] });
      queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
    onError: (err: Error) => toast("error", err.message),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!phoneNumberId.trim() || !accessToken.trim()) {
      toast("error", "Completa phone_number_id y token");
      return;
    }
    connectMutation.mutate();
  }

  const canConnect =
    canManage &&
    client.status !== "pending" &&
    client.status !== "inactive" &&
    client.status !== "rejected";

  return (
    <div className={CARD + " p-6 space-y-4"}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <MessageCircle size={16} className="text-amber-400" />
          <h3 className="text-lg font-bold text-white tracking-tight">WhatsApp</h3>
        </div>
        {connected ? (
          <span className={BADGE_OK}>Conectado</span>
        ) : (
          <span className={BADGE_MUT}>Sin conectar</span>
        )}
      </div>

      <p className="text-xs text-zinc-500">
        YCloud Coexistence: número en E.164 (ej. +34600111222) + API Key de YCloud.
        No uses el número de Orinoco en otro tenant.
      </p>

      {connected && client.phone_number_id && (
        <p className="text-sm text-zinc-300 font-mono break-all">{client.phone_number_id}</p>
      )}

      {!canManage ? (
        <p className="text-xs text-zinc-600">Solo superadmin puede conectar o desconectar WhatsApp.</p>
      ) : client.status === "pending" ? (
        <p className="text-xs text-amber-400/90">Aprueba el cliente antes de conectar WhatsApp.</p>
      ) : canConnect ? (
        <form onSubmit={onSubmit} className="space-y-3">
          <label className="space-y-1.5 block">
            <span className="text-xs text-zinc-400">phone_number_id / número E.164</span>
            <input
              className={INPUT}
              value={phoneNumberId}
              onChange={(e) => setPhoneNumberId(e.target.value)}
              placeholder="+34600111222"
              autoComplete="off"
            />
          </label>
          <label className="space-y-1.5 block">
            <span className="text-xs text-zinc-400">API Key / access token</span>
            <input
              type="password"
              className={INPUT}
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              placeholder="Se cifra al guardar"
              autoComplete="off"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={connectMutation.isPending} className={BTN}>
              {connectMutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Link2 size={14} />
              )}
              {connected ? "Actualizar conexión" : "Conectar WhatsApp"}
            </button>
            {connected && !confirmDisconnect && (
              <button
                type="button"
                onClick={() => setConfirmDisconnect(true)}
                className={BTND}
              >
                <Link2Off size={14} /> Desconectar
              </button>
            )}
          </div>
          {confirmDisconnect && (
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="text-xs text-zinc-400">¿Desconectar este número?</span>
              <button
                type="button"
                onClick={() => disconnectMutation.mutate()}
                disabled={disconnectMutation.isPending}
                className={BTND}
              >
                {disconnectMutation.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : null}
                Confirmar
              </button>
              <button type="button" onClick={() => setConfirmDisconnect(false)} className={BTN2}>
                Cancelar
              </button>
            </div>
          )}
        </form>
      ) : (
        <p className="text-xs text-zinc-600">El cliente debe estar aprobado/activo para conectar WhatsApp.</p>
      )}
    </div>
  );
}
