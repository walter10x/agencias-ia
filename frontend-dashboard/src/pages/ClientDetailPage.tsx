import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Building2, Phone, Edit, Trash2, Plus, Bot, Loader2, AlertTriangle, Globe, Mail, Send } from "lucide-react";
import { fetchClient, deactivateClient } from "@/api/client";
import { fetchAgentsByClient } from "@/api/agent";
import { fetchLandingConfig, updateLandingConfig, type LandingConfig } from "@/api/landing";
import { fetchEmails, fetchEmailStats, sendEmail, type EmailLogData } from "@/api/email";
import ClientForm from "@/components/ClientForm";
import AgentForm from "@/components/AgentForm";
import { useToast } from "@/components/Toast";

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [editOpen, setEditOpen] = useState(false);
  const [agentFormOpen, setAgentFormOpen] = useState(false);
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);
  const [activeTab, setActiveTab] = useState<"info" | "landing" | "email">("info");

  // Landing state
  const [landingSlug, setLandingSlug] = useState("");
  const [landingTitle, setLandingTitle] = useState("");
  const [landingDescription, setLandingDescription] = useState("");
  const [landingActive, setLandingActive] = useState(false);
  const [landingColor, setLandingColor] = useState("#f59e0b");
  const [landingAutoReply, setLandingAutoReply] = useState("");
  const [landingDirty, setLandingDirty] = useState(false);

  // Email state
  const [emailTo, setEmailTo] = useState("");
  const [emailRubro, setEmailRubro] = useState("restaurante");
  const [emailSequence, setEmailSequence] = useState(1);
  const [emailContactName, setEmailContactName] = useState("");
  const [emailSending, setEmailSending] = useState(false);

  const clientQuery = useQuery({
    queryKey: ["client", id],
    queryFn: () => fetchClient(id!),
    enabled: !!id,
  });

  const agentsQuery = useQuery({
    queryKey: ["agents", "client", id],
    queryFn: () => fetchAgentsByClient(id!),
    enabled: !!id,
  });

  const landingQuery = useQuery({
    queryKey: ["landing", id],
    queryFn: () => fetchLandingConfig(id!),
    enabled: !!id,
  });

  const emailQuery = useQuery({
    queryKey: ["emails", id],
    queryFn: () => fetchEmails(id!),
    enabled: !!id && activeTab === "email",
  });

  const emailStatsQuery = useQuery({
    queryKey: ["email-stats", id],
    queryFn: () => fetchEmailStats(id!),
    enabled: !!id && activeTab === "email",
  });

  const landingMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => updateLandingConfig(id!, data),
    onSuccess: (data: LandingConfig) => {
      toast("success", "Landing actualizada");
      setLandingDirty(false);
      setLandingSlug(data.landing_slug ?? "");
      setLandingTitle(data.landing_title);
      setLandingDescription(data.landing_description);
      setLandingActive(data.landing_active);
      setLandingColor(data.landing_primary_color);
      setLandingAutoReply(data.landing_auto_reply);
      queryClient.invalidateQueries({ queryKey: ["landing", id] });
    },
    onError: (err: Error) => {
      toast("error", err.message);
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: () => deactivateClient(id!),
    onSuccess: () => {
      toast("success", "Cliente desactivado");
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.invalidateQueries({ queryKey: ["client", id] });
      navigate("/clients");
    },
    onError: (err: Error) => {
      toast("error", err.message);
    },
  });

  const client = clientQuery.data;
  const agents = agentsQuery.data?.items ?? [];
  const landing = landingQuery.data;

  const emails = emailQuery.data?.items ?? [];
  const emailStats = emailStatsQuery.data;

  // Sync landing state when data loads
  useEffect(() => {
    if (landing) {
      setLandingSlug(landing.landing_slug ?? "");
      setLandingTitle(landing.landing_title);
      setLandingDescription(landing.landing_description);
      setLandingActive(landing.landing_active);
      setLandingColor(landing.landing_primary_color);
      setLandingAutoReply(landing.landing_auto_reply);
    }
  }, [landing]);

  const isClientLoading = clientQuery.isLoading;
  const isClientError = clientQuery.error;
  const isAgentsLoading = agentsQuery.isLoading;

  if (isClientLoading) {
    return (
      <div className="p-6 space-y-6 relative">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
        </div>
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-8 animate-pulse space-y-4">
          <div className="h-6 w-48 bg-zinc-800 rounded" />
          <div className="h-4 w-64 bg-zinc-800 rounded" />
          <div className="h-4 w-36 bg-zinc-800 rounded" />
        </div>
      </div>
    );
  }

  if (isClientError || !client) {
    return (
      <div className="p-6 relative">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
        </div>
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <AlertTriangle size={48} className="text-amber-500 mx-auto mb-4 stroke-[1.5]" />
          <h3 className="text-lg font-semibold text-white mb-2">Cliente no encontrado</h3>
          <p className="text-sm text-zinc-500 mb-6">El cliente que buscas no existe o fue eliminado.</p>
          <button
            onClick={() => navigate("/clients")}
            className="px-4 py-2 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
          >
            Volver a clientes
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 relative">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Back + Client Info */}
      <div className="relative z-10 space-y-4">
        <button
          onClick={() => navigate("/clients")}
          className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={16} /> Volver
        </button>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <div className="flex items-start justify-between">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center">
                  <Building2 size={22} className="text-amber-400 stroke-[1.5]" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">{client.name}</h2>
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm text-zinc-400">
                <span className="flex items-center gap-1.5">
                  <Phone size={14} /> {client.whatsapp_number}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs px-2.5 py-1 rounded-md bg-zinc-800 text-zinc-400">
                  {client.business_type}
                </span>
                <span className={`text-xs px-2.5 py-1 rounded-md ${
                  client.is_active
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-zinc-800 text-zinc-500"
                }`}>
                  {client.is_active ? "Activo" : "Inactivo"}
                </span>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setEditOpen(true)}
                className="flex items-center gap-1.5 px-3 py-2 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
              >
                <Edit size={14} /> Editar
              </button>
              {client.is_active && (
                <button
                  onClick={() => setConfirmDeactivate(true)}
                  className="flex items-center gap-1.5 px-3 py-2 bg-red-500/10 text-red-400 text-sm font-medium rounded-lg hover:bg-red-500/20 transition-colors border border-red-500/20"
                >
                  <Trash2 size={14} /> Desactivar
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="relative z-10">
        <div className="flex gap-1 bg-zinc-900 border border-zinc-800 rounded-xl p-1">
          <button
            onClick={() => setActiveTab("info")}
            className={`flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === "info" ? "bg-amber-500 text-black" : "text-zinc-400 hover:text-white"
            }`}
          >
            <Bot size={14} className="inline mr-1.5" />
            Agentes
          </button>
          <button
            onClick={() => setActiveTab("landing")}
            className={`flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === "landing" ? "bg-amber-500 text-black" : "text-zinc-400 hover:text-white"
            }`}
          >
            <Globe size={14} className="inline mr-1.5" />
            Landing
          </button>
          <button
            onClick={() => setActiveTab("email")}
            className={`flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === "email" ? "bg-amber-500 text-black" : "text-zinc-400 hover:text-white"
            }`}
          >
            <Mail size={14} className="inline mr-1.5" />
            Email
          </button>
        </div>
      </div>

      {activeTab === "email" ? (
      /* Email Marketing Section */
      <div className="relative z-10 space-y-4">
        {/* Stats */}
        {emailStatsQuery.isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 animate-pulse">
                <div className="h-5 w-12 bg-zinc-800 rounded mb-2" />
                <div className="h-3 w-20 bg-zinc-800 rounded" />
              </div>
            ))}
          </div>
        ) : emailStats ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <p className="text-2xl font-bold text-white">{emailStats.total_sent}</p>
              <p className="text-xs text-zinc-500 mt-1">Enviados</p>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <p className="text-2xl font-bold text-emerald-400">{emailStats.total_opened}</p>
              <p className="text-xs text-zinc-500 mt-1">Abiertos ({emailStats.open_rate}%)</p>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <p className="text-2xl font-bold text-blue-400">{emailStats.total_clicked}</p>
              <p className="text-xs text-zinc-500 mt-1">Clicks ({emailStats.click_rate}%)</p>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <p className="text-2xl font-bold text-red-400">{emailStats.total_bounced}</p>
              <p className="text-xs text-zinc-500 mt-1">Rebotados</p>
            </div>
          </div>
        ) : null}

        {/* Send Email Form */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
          <h4 className="text-white font-medium flex items-center gap-2">
            <Send size={16} className="text-amber-400" />
            Enviar email de prueba
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-zinc-400 mb-1">Email destino</label>
              <input
                type="email"
                value={emailTo}
                onChange={(e) => setEmailTo(e.target.value)}
                placeholder="cliente@email.com"
                className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-xl text-white text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm text-zinc-400 mb-1">Nombre de contacto</label>
              <input
                type="text"
                value={emailContactName}
                onChange={(e) => setEmailContactName(e.target.value)}
                placeholder="María García"
                className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-xl text-white text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-colors"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-zinc-400 mb-1">Rubro</label>
              <select
                value={emailRubro}
                onChange={(e) => setEmailRubro(e.target.value)}
                className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-colors"
              >
                <option value="restaurante">Restaurante</option>
                <option value="peluqueria">Peluquería</option>
                <option value="clinica">Clínica</option>
                <option value="tienda">Tienda</option>
                <option value="inmobiliaria">Inmobiliaria</option>
                <option value="gimnasio">Gimnasio</option>
                <option value="contador">Contador</option>
                <option value="taller">Taller</option>
                <option value="hotel">Hotel</option>
                <option value="ecommerce">E-commerce</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-zinc-400 mb-1">Secuencia</label>
              <select
                value={emailSequence}
                onChange={(e) => setEmailSequence(Number(e.target.value))}
                className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-colors"
              >
                <option value={1}>1 — Bienvenida</option>
                <option value={2}>2 — Beneficios</option>
                <option value={3}>3 — Oferta</option>
              </select>
            </div>
          </div>

          <button
            onClick={async () => {
              if (!emailTo.trim()) return;
              setEmailSending(true);
              try {
                await sendEmail({
                  client_id: client.id,
                  to_email: emailTo,
                  rubro_slug: emailRubro,
                  sequence_number: emailSequence,
                  business_name: client.name,
                  contact_name: emailContactName,
                });
                toast("success", "Email enviado correctamente");
                setEmailTo("");
                setEmailContactName("");
                queryClient.invalidateQueries({ queryKey: ["emails", id] });
                queryClient.invalidateQueries({ queryKey: ["email-stats", id] });
              } catch (err: unknown) {
                const msg = err instanceof Error ? err.message : "Error al enviar email";
                toast("error", msg);
              } finally {
                setEmailSending(false);
              }
            }}
            disabled={emailSending || !emailTo.trim()}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-amber-500 text-black text-sm font-semibold rounded-xl hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {emailSending ? (
              <><Loader2 size={16} className="animate-spin" /> Enviando...</>
            ) : (
              <><Send size={14} /> Enviar email</>
            )}
          </button>
        </div>

        {/* Email History */}
        <div className="space-y-2">
          <h4 className="text-white font-medium">Historial de envios</h4>
          {emailQuery.isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 animate-pulse">
                  <div className="h-4 w-48 bg-zinc-800 rounded" />
                </div>
              ))}
            </div>
          ) : emails.length === 0 ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
              <Mail size={32} className="text-zinc-600 mx-auto mb-4 stroke-[1.5]" />
              <p className="text-sm text-zinc-500">No hay emails enviados aun</p>
            </div>
          ) : (
            <div className="space-y-2">
              {emails.map((email: EmailLogData) => (
                <div key={email.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-white text-sm font-medium truncate">{email.subject}</p>
                      <p className="text-xs text-zinc-500 mt-0.5">
                        {email.to_email} · {email.template_slug} · Seq {email.sequence_number}
                      </p>
                    </div>
                    <span
                      className={`text-xs px-2.5 py-1 rounded-md ml-3 shrink-0 ${
                        email.status === "sent"
                          ? "bg-blue-500/10 text-blue-400"
                          : email.status === "delivered"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : email.status === "opened"
                          ? "bg-amber-500/10 text-amber-400"
                          : email.status === "clicked"
                          ? "bg-violet-500/10 text-violet-400"
                          : "bg-red-500/10 text-red-400"
                      }`}
                    >
                      {email.status}
                    </span>
                  </div>
                  {email.error_message && (
                    <p className="text-xs text-red-400 mt-2 bg-red-500/5 rounded-lg p-2">{email.error_message}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      ) : activeTab === "info" ? (
      /* Agents Section */
      <div className="relative z-10 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">
            Agentes IA {agents.length > 0 && `(${agents.length})`}
          </h3>
          <button
            onClick={() => setAgentFormOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
          >
            <Plus size={14} /> Nuevo Agente
          </button>
        </div>

        {isAgentsLoading && (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 animate-pulse">
                <div className="h-5 w-36 bg-zinc-800 rounded" />
              </div>
            ))}
          </div>
        )}

        {!isAgentsLoading && agents.length === 0 && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
            <Bot size={32} className="text-zinc-600 mx-auto mb-4 stroke-[1.5]" />
            <p className="text-sm text-zinc-500 mb-4">Este cliente no tiene agentes</p>
            <button
              onClick={() => setAgentFormOpen(true)}
              className="px-4 py-2 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
            >
              Crear primer agente
            </button>
          </div>
        )}

        {!isAgentsLoading && agents.length > 0 && (
          <div className="space-y-2">
            {agents.map((agent) => (
              <div
                key={agent.id}
                onClick={() => navigate(`/agents/${agent.id}`)}
                className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors cursor-pointer group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
                      <Bot size={18} className="text-emerald-400 stroke-[1.5]" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-white font-medium truncate">{agent.name}</p>
                      <p className="text-xs text-zinc-500 truncate">{agent.personality.slice(0, 80)}</p>
                    </div>
                  </div>
                  <span className={`text-xs px-2.5 py-1 rounded-md ${
                    agent.is_active
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "bg-zinc-800 text-zinc-500"
                  }`}>
                    {agent.is_active ? "Activo" : "Inactivo"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      ) : (
      /* Landing Section */
      <div className="relative z-10 space-y-4">
        {landingQuery.isLoading ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 animate-pulse space-y-4">
            <div className="h-5 w-32 bg-zinc-800 rounded" />
            <div className="h-10 w-full bg-zinc-800 rounded-xl" />
            <div className="h-10 w-full bg-zinc-800 rounded-xl" />
            <div className="h-10 w-40 bg-zinc-800 rounded-xl" />
          </div>
        ) : landing ? (
          <>
            {/* Stats */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <p className="text-2xl font-bold text-white">{landing.leads_count}</p>
                <p className="text-xs text-zinc-500 mt-1">Leads captados</p>
              </div>
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <p className="text-2xl font-bold text-white">{landing.landing_slug ? "Activa" : "—"}</p>
                <p className="text-xs text-zinc-500 mt-1">Estado</p>
              </div>
            </div>

            {/* Config Form */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
              {/* Toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-white font-medium">Landing activa</h4>
                  <p className="text-xs text-zinc-500">Mostrar landing page pública</p>
                </div>
                <button
                  onClick={() => { setLandingActive(!landingActive); setLandingDirty(true); }}
                  className={`w-12 h-6 rounded-full transition-colors relative ${landingActive ? "bg-emerald-500" : "bg-zinc-700"}`}
                >
                  <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${landingActive ? "left-6" : "left-0.5"}`} />
                </button>
              </div>

              {/* Slug */}
              <div>
                <label className="block text-sm text-zinc-400 mb-1">URL Slug</label>
                <input
                  type="text"
                  value={landingSlug}
                  onChange={(e) => { setLandingSlug(e.target.value); setLandingDirty(true); }}
                  placeholder="mi-negocio"
                  maxLength={100}
                  className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-xl text-white text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-colors"
                />
                {landingSlug && (
                  <p className="mt-1 text-xs text-zinc-600">
                    {window.location.origin}/landing/{landingSlug || "mi-negocio"}
                  </p>
                )}
              </div>

              {/* Title */}
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Título</label>
                <input
                  type="text"
                  value={landingTitle}
                  onChange={(e) => { setLandingTitle(e.target.value); setLandingDirty(true); }}
                  maxLength={200}
                  className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-xl text-white text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-colors"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Descripción</label>
                <textarea
                  value={landingDescription}
                  onChange={(e) => { setLandingDescription(e.target.value); setLandingDirty(true); }}
                  maxLength={500}
                  rows={3}
                  className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-xl text-white text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-colors resize-none"
                />
              </div>

              {/* Color */}
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Color primario</label>
                <div className="flex items-center gap-3">
                  <input
                    type="color"
                    value={landingColor}
                    onChange={(e) => { setLandingColor(e.target.value); setLandingDirty(true); }}
                    className="w-10 h-10 rounded-lg border border-zinc-700 cursor-pointer bg-transparent"
                  />
                  <input
                    type="text"
                    value={landingColor}
                    onChange={(e) => { setLandingColor(e.target.value); setLandingDirty(true); }}
                    pattern="^#[0-9a-fA-F]{6}$"
                    maxLength={7}
                    className="flex-1 px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-xl text-white text-sm font-mono placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-colors"
                  />
                </div>
              </div>

              {/* Auto-reply */}
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Mensaje auto-reply</label>
                <textarea
                  value={landingAutoReply}
                  onChange={(e) => { setLandingAutoReply(e.target.value); setLandingDirty(true); }}
                  maxLength={1000}
                  rows={3}
                  placeholder="¡Hola {{name}}! Gracias por contactarnos."
                  className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-xl text-white text-sm placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-colors resize-none"
                />
                <p className="mt-1 text-xs text-zinc-600">Usa {"{{name}}"} para personalizar con el nombre del lead.</p>
              </div>

              {/* Save button */}
              <button
                onClick={() => {
                  const data: Record<string, unknown> = {};
                  if (landingSlug !== (landing?.landing_slug ?? "")) data.landing_slug = landingSlug || null;
                  if (landingTitle !== (landing?.landing_title ?? "")) data.landing_title = landingTitle;
                  if (landingDescription !== (landing?.landing_description ?? "")) data.landing_description = landingDescription;
                  if (landingActive !== (landing?.landing_active ?? false)) data.landing_active = landingActive;
                  if (landingColor !== (landing?.landing_primary_color ?? "#f59e0b")) data.landing_primary_color = landingColor;
                  if (landingAutoReply !== (landing?.landing_auto_reply ?? "")) data.landing_auto_reply = landingAutoReply;
                  landingMutation.mutate(data);
                }}
                disabled={landingMutation.isPending || !landingDirty}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-amber-500 text-black text-sm font-semibold rounded-xl hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {landingMutation.isPending ? (
                  <><Loader2 size={16} className="animate-spin" /> Guardando...</>
                ) : (
                  "Guardar cambios"
                )}
              </button>
            </div>
          </>
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
            <Globe size={32} className="text-zinc-600 mx-auto mb-4 stroke-[1.5]" />
            <p className="text-sm text-zinc-500">No se pudo cargar la configuración de landing</p>
          </div>
        )}
      </div>
      )}

      {/* Client Form Modal */}
      <ClientForm
        isOpen={editOpen}
        onClose={() => setEditOpen(false)}
        client={client}
      />

      {/* Agent Form Modal */}
      <AgentForm
        isOpen={agentFormOpen}
        onClose={() => setAgentFormOpen(false)}
        clientId={client.id}
      />

      {/* Deactivate Confirmation Modal */}
      {confirmDeactivate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-[fadeIn_0.15s_ease-out]">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-sm mx-4 shadow-2xl p-6 animate-[fadeIn_0.15s_ease-out]">
            <AlertTriangle size={32} className="text-amber-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white text-center mb-2">¿Desactivar cliente?</h3>
            <p className="text-sm text-zinc-400 text-center mb-6">
              Sus agentes también se desactivarán. Esta acción se puede revertir reactivando el cliente.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDeactivate(false)}
                className="flex-1 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
              >
                Cancelar
              </button>
              <button
                onClick={() => deactivateMutation.mutate()}
                disabled={deactivateMutation.isPending}
                className="flex-1 px-4 py-2.5 bg-red-500/10 text-red-400 text-sm font-semibold rounded-lg hover:bg-red-500/20 transition-colors border border-red-500/20 flex items-center justify-center gap-2"
              >
                {deactivateMutation.isPending && <Loader2 size={16} className="animate-spin" />}
                Desactivar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
