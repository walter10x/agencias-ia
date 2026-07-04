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

const CARD = "bg-zinc-900 border border-zinc-800 rounded-xl transition-all duration-300 ease-out hover:border-zinc-700 hover:shadow-lg hover:shadow-black/20";
const BTN = "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-xl transition-all duration-200 ease-out hover:bg-amber-400 hover:shadow-lg hover:shadow-amber-500/20 active:scale-[0.98]";
const BTN2 = "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-xl border border-zinc-700 transition-all duration-200 ease-out hover:bg-zinc-700 hover:text-white";
const BTND = "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-red-500/10 text-red-400 text-sm font-semibold rounded-xl border border-red-500/20 transition-all duration-200 ease-out hover:bg-red-500/20";
const INPUT = "w-full px-4 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-white text-sm placeholder:text-zinc-600 transition-all duration-200 focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/10";
const BADGE_OK = "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
const BADGE_MUT = "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700";

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [editOpen, setEditOpen] = useState(false);
  const [agentFormOpen, setAgentFormOpen] = useState(false);
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);
  const [activeTab, setActiveTab] = useState<"info" | "landing" | "email">("info");

  const [landingSlug, setLandingSlug] = useState("");
  const [landingTitle, setLandingTitle] = useState("");
  const [landingActive, setLandingActive] = useState(false);
  const [landingColor, setLandingColor] = useState("#f59e0b");
  const [landingDirty, setLandingDirty] = useState(false);

  const [emailTo, setEmailTo] = useState("");
  const [emailRubro, setEmailRubro] = useState("restaurante");
  const [emailSequence, setEmailSequence] = useState(1);
  const [emailContactName, setEmailContactName] = useState("");
  const [emailSending, setEmailSending] = useState(false);

  const clientQuery = useQuery({ queryKey: ["client", id], queryFn: () => fetchClient(id!), enabled: !!id });
  const agentsQuery = useQuery({ queryKey: ["agents", "client", id], queryFn: () => fetchAgentsByClient(id!), enabled: !!id });
  const landingQuery = useQuery({ queryKey: ["landing", id], queryFn: () => fetchLandingConfig(id!), enabled: !!id });
  const emailQuery = useQuery({ queryKey: ["emails", id], queryFn: () => fetchEmails(id!), enabled: !!id && activeTab === "email" });
  const emailStatsQuery = useQuery({ queryKey: ["email-stats", id], queryFn: () => fetchEmailStats(id!), enabled: !!id && activeTab === "email" });

  const landingMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => updateLandingConfig(id!, data),
    onSuccess: (data: LandingConfig) => { toast("success", "Landing actualizada"); setLandingDirty(false); setLandingSlug(data.landing_slug ?? ""); setLandingTitle(data.landing_title); setLandingActive(data.landing_active); setLandingColor(data.landing_primary_color); queryClient.invalidateQueries({ queryKey: ["landing", id] }); },
    onError: (err: Error) => toast("error", err.message),
  });

  const deactivateMutation = useMutation({
    mutationFn: () => deactivateClient(id!),
    onSuccess: () => { toast("success", "Cliente desactivado"); queryClient.invalidateQueries({ queryKey: ["clients"] }); queryClient.invalidateQueries({ queryKey: ["client", id] }); navigate("/app/clients"); },
    onError: (err: Error) => toast("error", err.message),
  });

  const client = clientQuery.data;
  const agents = agentsQuery.data?.items ?? [];
  const landing = landingQuery.data;
  const emails = emailQuery.data?.items ?? [];
  const emailStats = emailStatsQuery.data;

  useEffect(() => { if (landing) { setLandingSlug(landing.landing_slug ?? ""); setLandingTitle(landing.landing_title); setLandingActive(landing.landing_active); setLandingColor(landing.landing_primary_color); } }, [landing]);

  if (clientQuery.isLoading) return <div className="p-6 lg:p-8 space-y-6"><div className={CARD + " p-8 space-y-4"}><div className="skeleton h-10 w-48" /><div className="skeleton h-5 w-64" /><div className="skeleton h-5 w-36" /></div></div>;
  if (clientQuery.error || !client) return (
    <div className="p-6 lg:p-8">
      <div className="flex flex-col items-center justify-center text-center bg-zinc-900 border border-zinc-800 rounded-xl py-16 animate-scale-in">
        <AlertTriangle size={48} className="text-amber-400 mb-4 empty-state-icon" /><h3 className="text-lg font-semibold text-white mb-2">Cliente no encontrado</h3><p className="text-sm text-zinc-500 mb-6">El cliente que buscas no existe o fue eliminado.</p><button onClick={() => navigate("/app/clients")} className={BTN}>Volver a Clientes</button>
      </div>
    </div>
  );

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="space-y-4 animate-fade-in">
        <button onClick={() => navigate("/app/clients")} className="inline-flex items-center gap-1.5 px-3 py-2 text-zinc-400 text-sm font-medium rounded-lg transition-all duration-200 hover:bg-zinc-800/50 hover:text-white"><ArrowLeft size={14} /> Volver</button>
        <div className={CARD + " !p-6"}>
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0"><Building2 size={22} /></div>
              <div className="space-y-1.5">
                <h2 className="text-xl font-bold text-white">{client.name}</h2>
                <div className="flex items-center gap-3 text-sm text-zinc-400"><span className="flex items-center gap-1.5"><Phone size={13} /> {client.whatsapp_number}</span></div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={BADGE_MUT}>{client.business_type}</span>
                  {client.is_active ? <span className={BADGE_OK}>Activo</span> : <span className={BADGE_MUT}>Inactivo</span>}
                </div>
              </div>
            </div>
            <div className="flex gap-2 self-start"><button onClick={() => setEditOpen(true)} className={BTN2}><Edit size={14} /> Editar</button>{client.is_active && <button onClick={() => setConfirmDeactivate(true)} className={BTND}><Trash2 size={14} /> Desactivar</button>}</div>
          </div>
        </div>
      </div>

      <div className="flex gap-1 bg-zinc-900 border border-zinc-800 rounded-xl p-1 animate-fade-in" style={{ animationDelay: "0.1s" }}>
        {(["info","landing","email"] as const).map(tab => {
          const labels = {info: <><Bot size={14} /> Agencia</>, landing: <><Globe size={14} /> Landing</>, email: <><Mail size={14} /> Email</>};
          return <button key={tab} onClick={() => setActiveTab(tab)} className={`flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${activeTab===tab?"bg-amber-500 text-black font-semibold shadow-sm shadow-amber-500/20":"text-zinc-400 hover:text-white hover:bg-zinc-800/50"}`}>{labels[tab]}</button>;
        })}
      </div>

      <div className="animate-fade-in">
        {activeTab === "email" ? (
          <div className="space-y-4">
            {emailStatsQuery.isLoading ? <div className="grid grid-cols-2 md:grid-cols-4 gap-3">{Array.from({length:4}).map((_,i)=><div key={i} className={CARD+" p-4"}><div className="skeleton h-8 w-16 mb-2"/><div className="skeleton h-3 w-20"/></div>)}</div>
            : emailStats ? <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className={CARD+" p-4"}><p className="text-2xl font-bold text-white">{emailStats.total_sent}</p><p className="text-xs text-zinc-500 mt-1">Enviados</p></div>
              <div className={CARD+" p-4"}><p className="text-2xl font-bold text-emerald-400">{emailStats.total_opened}</p><p className="text-xs text-zinc-500 mt-1">Abiertos ({emailStats.open_rate}%)</p></div>
              <div className={CARD+" p-4"}><p className="text-2xl font-bold text-blue-400">{emailStats.total_clicked}</p><p className="text-xs text-zinc-500 mt-1">Clicks ({emailStats.click_rate}%)</p></div>
              <div className={CARD+" p-4"}><p className="text-2xl font-bold text-red-400">{emailStats.total_bounced}</p><p className="text-xs text-zinc-500 mt-1">Rebotados</p></div>
            </div> : null}
            <div className={CARD+" p-6 space-y-4"}>
              <h4 className="text-white font-semibold flex items-center gap-2"><Send size={16} className="text-amber-400"/>Enviar email</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div><label className="block text-sm text-zinc-400 mb-1">Email destino</label><input type="email" value={emailTo} onChange={e=>setEmailTo(e.target.value)} placeholder="cliente@email.com" className={INPUT}/></div>
                <div><label className="block text-sm text-zinc-400 mb-1">Nombre</label><input type="text" value={emailContactName} onChange={e=>setEmailContactName(e.target.value)} placeholder="María García" className={INPUT}/></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div><label className="block text-sm text-zinc-400 mb-1">Rubro</label><select value={emailRubro} onChange={e=>setEmailRubro(e.target.value)} className={INPUT}><option value="restaurante">Restaurante</option><option value="peluqueria">Peluquería</option><option value="clinica">Clínica</option><option value="tienda">Tienda</option></select></div>
                <div><label className="block text-sm text-zinc-400 mb-1">Secuencia</label><select value={emailSequence} onChange={e=>setEmailSequence(Number(e.target.value))} className={INPUT}><option value={1}>1 — Bienvenida</option><option value={2}>2 — Beneficios</option><option value={3}>3 — Oferta</option></select></div>
              </div>
              <button onClick={async()=>{if(!emailTo.trim())return;setEmailSending(true);try{await sendEmail({client_id:client.id,to_email:emailTo,rubro_slug:emailRubro,sequence_number:emailSequence,business_name:client.name,contact_name:emailContactName});toast("success","Email enviado");setEmailTo("");setEmailContactName("");queryClient.invalidateQueries({queryKey:["emails",id]});queryClient.invalidateQueries({queryKey:["email-stats",id]})}catch(err:unknown){toast("error",err instanceof Error?err.message:"Error al enviar email")}finally{setEmailSending(false)}}} disabled={emailSending||!emailTo.trim()} className={BTN+" w-full"}>{emailSending?<><Loader2 size={16} className="animate-spin"/>Enviando...</>:<><Send size={14}/>Enviar email</>}</button>
            </div>
            <div className="space-y-2"><h4 className="text-white font-semibold">Historial</h4>
              {emailQuery.isLoading?<div className="space-y-2">{Array.from({length:3}).map((_,i)=><div key={i} className={CARD+" p-4"}><div className="skeleton h-4 w-48"/></div>)}</div>
              :emails.length===0?<div className={CARD+" flex flex-col items-center justify-center py-8"}><Mail size={24} className="text-zinc-600 mb-2 empty-state-icon"/><p className="text-sm text-zinc-500">No hay emails enviados</p></div>
              :<div className="space-y-2">{emails.map((email:EmailLogData)=><div key={email.id} className={CARD+" p-4"}><div className="flex items-center justify-between"><div className="min-w-0 flex-1"><p className="text-white text-sm font-medium truncate">{email.subject}</p><p className="text-xs text-zinc-500 mt-0.5">{email.to_email} · {email.template_slug}</p></div><span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium ml-3 shrink-0 ${email.status==="sent"?"bg-blue-500/10 text-blue-400 border border-blue-500/20":email.status==="delivered"?BADGE_OK:email.status==="opened"?"bg-amber-500/10 text-amber-400 border border-amber-500/20":"bg-red-500/10 text-red-400 border border-red-500/20"}`}>{email.status}</span></div></div>)}</div>}
            </div>
          </div>
        ) : activeTab === "info" ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between"><h3 className="text-lg font-bold text-white tracking-tight">Agentes IA {agents.length>0&&`(${agents.length})`}</h3><button onClick={()=>setAgentFormOpen(true)} className={BTN}><Plus size={14}/>Nuevo Agente</button></div>
            {agentsQuery.isLoading?<div className="space-y-3">{Array.from({length:3}).map((_,i)=><div key={i} className={CARD+" p-4"}><div className="skeleton h-5 w-36"/></div>)}</div>
            :agents.length===0?<div className={CARD+" flex flex-col items-center justify-center py-12"}><Bot size={32} className="text-zinc-600 mb-4 empty-state-icon"/><p className="text-sm text-zinc-500 mb-4">Este cliente no tiene agentes</p><button onClick={()=>setAgentFormOpen(true)} className={BTN2}>Crear primer agente</button></div>
            :<div className="space-y-2">{agents.map(agent=><div key={agent.id} onClick={()=>navigate(`/app/agents/${agent.id}`)} className={CARD+" p-4 cursor-pointer"}><div className="flex items-center justify-between"><div className="flex items-center gap-3 min-w-0"><div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0"><Bot size={18}/></div><div className="min-w-0"><p className="text-white font-medium truncate">{agent.name}</p><p className="text-xs text-zinc-500 truncate">{agent.personality.slice(0,80)}</p></div></div>{agent.is_active?<span className={BADGE_OK}>Activo</span>:<span className={BADGE_MUT}>Inactivo</span>}</div></div>)}</div>}
          </div>
        ) : (
          <div className="space-y-4">
            {landingQuery.isLoading?<div className={CARD+" p-6 space-y-4"}><div className="skeleton h-5 w-32"/><div className="skeleton h-10 w-full"/></div>
            :landing?<>
              <div className="grid grid-cols-2 gap-3"><div className={CARD+" p-4"}><p className="text-2xl font-bold text-white">{landing.leads_count}</p><p className="text-xs text-zinc-500 mt-1">Leads captados</p></div><div className={CARD+" p-4"}><p className="text-2xl font-bold text-white">{landing.landing_slug?"Activa":"—"}</p><p className="text-xs text-zinc-500 mt-1">Estado</p></div></div>
              <div className={CARD+" p-6 space-y-4"}>
                <div className="flex items-center justify-between"><div><h4 className="text-white font-semibold">Landing activa</h4><p className="text-xs text-zinc-500">Mostrar landing page pública</p></div><button onClick={()=>{setLandingActive(!landingActive);setLandingDirty(true)}} className={`w-12 h-6 rounded-full transition-colors relative ${landingActive?"bg-emerald-500":"bg-zinc-700"}`}><span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${landingActive?"translate-x-6":"translate-x-0.5"}`}/></button></div>
                <div><label className="block text-sm text-zinc-400 mb-1">URL Slug</label><input type="text" value={landingSlug} onChange={e=>{setLandingSlug(e.target.value);setLandingDirty(true)}} placeholder="mi-negocio" maxLength={100} className={INPUT}/>{landingSlug&&<p className="mt-1 text-xs text-zinc-600">landing/{landingSlug}</p>}</div>
                <div><label className="block text-sm text-zinc-400 mb-1">Título</label><input type="text" value={landingTitle} onChange={e=>{setLandingTitle(e.target.value);setLandingDirty(true)}} maxLength={200} className={INPUT}/></div>
                <div><label className="block text-sm text-zinc-400 mb-1">Color primario</label><div className="flex items-center gap-3"><input type="color" value={landingColor} onChange={e=>{setLandingColor(e.target.value);setLandingDirty(true)}} className="w-10 h-10 rounded-lg border border-zinc-700 cursor-pointer bg-transparent"/><input type="text" value={landingColor} onChange={e=>{setLandingColor(e.target.value);setLandingDirty(true)}} maxLength={7} className={INPUT+" flex-1 font-mono"}/></div></div>
                <button onClick={()=>landingMutation.mutate({})} disabled={landingMutation.isPending||!landingDirty} className={BTN+" w-full"}>{landingMutation.isPending?<><Loader2 size={16} className="animate-spin"/>Guardando...</>:"Guardar cambios"}</button>
              </div>
            </>:<div className={CARD+" flex flex-col items-center justify-center py-12"}><Globe size={32} className="text-zinc-600 mb-4 empty-state-icon"/><p className="text-sm text-zinc-500">No se pudo cargar la landing</p></div>}
          </div>
        )}
      </div>

      <ClientForm isOpen={editOpen} onClose={()=>setEditOpen(false)} client={client}/>
      <AgentForm isOpen={agentFormOpen} onClose={()=>setAgentFormOpen(false)} clientId={client.id}/>

      {confirmDeactivate&&<div className="fixed inset-0 z-50 flex items-center justify-center animate-scale-in"><div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={()=>setConfirmDeactivate(false)}/><div className="bg-zinc-900/95 backdrop-blur-md border border-zinc-800/50 rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6"><AlertTriangle size={32} className="text-amber-400 mx-auto mb-4"/><h3 className="text-lg font-semibold text-white text-center mb-2">¿Desactivar cliente?</h3><p className="text-sm text-zinc-400 text-center mb-6">Sus agentes también se desactivarán.</p><div className="flex gap-3"><button onClick={()=>setConfirmDeactivate(false)} className={BTN2+" flex-1"}>Cancelar</button><button onClick={()=>deactivateMutation.mutate()} disabled={deactivateMutation.isPending} className={BTND+" flex-1"}>{deactivateMutation.isPending&&<Loader2 size={16} className="animate-spin"/>}Desactivar</button></div></div></div>}
    </div>
  );
}
