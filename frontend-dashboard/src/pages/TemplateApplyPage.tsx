import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Wrench,
  ChevronRight,
  X,
} from "lucide-react";
import { fetchTemplates, applyTemplate } from "@/api/template";
import { useToast } from "@/components/Toast";

export default function TemplateApplyPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { toast: showToast } = useToast();

  const [name, setName] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [successData, setSuccessData] = useState<{
    templateName: string;
    clientId: string;
    agentId: string;
  } | null>(null);

  // Fetch all templates to find the current one
  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  const template = templatesQuery.data?.templates.find((t) => t.slug === slug) ?? null;

  // Mutation for applying template
  const applyMutation = useMutation({
    mutationFn: (data: { name: string; whatsapp_number: string }) =>
      applyTemplate(slug!, data),
    onSuccess: (output) => {
      setShowConfirm(false);
      setSuccessData({
        templateName: template?.name ?? slug ?? "",
        clientId: output.client.id,
        agentId: output.agent.id,
      });
    },
    onError: (err: Error) => {
      setShowConfirm(false);
      showToast("error", err.message);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !whatsapp.trim()) return;
    setShowConfirm(true);
  }

  function handleConfirm() {
    applyMutation.mutate({ name: name.trim(), whatsapp_number: whatsapp });
  }

  function cleanWhatsapp(value: string) {
    return value.replace(/\D/g, "");
  }

  // Loading state
  if (templatesQuery.isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 animate-pulse space-y-4">
          <div className="h-5 w-48 bg-zinc-800 rounded" />
          <div className="h-16 w-16 bg-zinc-800 rounded-2xl" />
          <div className="h-6 w-40 bg-zinc-800 rounded" />
          <div className="h-4 w-full bg-zinc-800 rounded" />
          <div className="h-4 w-3/4 bg-zinc-800 rounded" />
        </div>
      </div>
    );
  }

  // Error / not found state
  if (!template) {
    return (
      <div className="p-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center mx-auto mb-6">
            <AlertCircle size={32} className="text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Plantilla no encontrada</h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto mb-6">
            La plantilla "{slug}" no existe o ha sido removida.
          </p>
          <button
            onClick={() => navigate("/templates")}
            className="px-4 py-2 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors inline-flex items-center gap-2"
          >
            <ArrowLeft size={16} />
            Volver a plantillas
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 relative">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Breadcrumb */}
      <div className="relative z-10 flex items-center gap-2 text-sm text-zinc-500">
        <button
          onClick={() => navigate("/templates")}
          className="hover:text-zinc-300 transition-colors"
        >
          Plantillas
        </button>
        <ChevronRight size={14} />
        <span className="text-zinc-300">{template.name}</span>
        <ChevronRight size={14} />
        <span className="text-amber-500">Aplicar</span>
      </div>

      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: Preview */}
        <div className="lg:col-span-3 space-y-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            {/* Emoji + Name */}
            <div className="flex items-center gap-4 mb-4">
              <span className="text-5xl">{template.emoji}</span>
              <div>
                <h2 className="text-xl font-bold text-white">{template.name}</h2>
                <p className="text-sm text-zinc-400">{template.description}</p>
              </div>
            </div>

            {/* Personality */}
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                Personalidad del Agente
              </h4>
              <p className="text-sm text-zinc-300 leading-relaxed bg-zinc-950 rounded-lg p-3 border border-zinc-800">
                {template.emoji} {template.description}
              </p>
            </div>

            {/* Tools */}
            <div>
              <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Wrench size={12} />
                Herramientas ({template.tools_count})
              </h4>
              <div className="space-y-2">
                {[].constructor.name === "Array" && // placeholder, tools_count is all we have from list endpoint
                  Array.from({ length: template.tools_count }).map((_, i) => (
                    <div
                      key={i}
                      className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 flex items-center gap-3"
                    >
                      <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                        <Wrench size={14} className="text-amber-400" />
                      </div>
                      <div>
                        <p className="text-sm text-zinc-300 font-medium">
                          Herramienta {i + 1}
                        </p>
                        <p className="text-xs text-zinc-500">
                          Tool del asistente para {template.name.toLowerCase()}
                        </p>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right: Form */}
        <div className="lg:col-span-2">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-1">Aplicar Plantilla</h3>
            <p className="text-sm text-zinc-500 mb-6">
              Completa los datos de tu negocio para crear el cliente y el agente IA.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Nombre del negocio
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={template.emoji + " " + template.name}
                  required
                  maxLength={200}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  WhatsApp del negocio
                </label>
                <input
                  type="text"
                  value={whatsapp}
                  onChange={(e) => setWhatsapp(cleanWhatsapp(e.target.value))}
                  placeholder="5491122334455"
                  required
                  minLength={10}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
                />
                <p className="text-[10px] text-zinc-600 mt-1">Solo dígitos, mínimo 10</p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => navigate("/templates")}
                  className="flex-1 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={!name.trim() || !whatsapp.trim() || applyMutation.isPending}
                  className="flex-1 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {applyMutation.isPending && <Loader2 size={16} className="animate-spin" />}
                  Aplicar plantilla
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Confirmar aplicación</h3>
              <button
                onClick={() => setShowConfirm(false)}
                className="p-1 hover:bg-zinc-800 rounded-lg transition-colors"
              >
                <X size={18} className="text-zinc-500" />
              </button>
            </div>

            <div className="space-y-3 mb-6">
              <div className="bg-zinc-950 rounded-lg p-3 border border-zinc-800">
                <p className="text-xs text-zinc-500">Negocio</p>
                <p className="text-white font-medium">{name.trim()}</p>
              </div>
              <div className="bg-zinc-950 rounded-lg p-3 border border-zinc-800">
                <p className="text-xs text-zinc-500">Rubro</p>
                <p className="text-white font-medium">{template.emoji} {template.name}</p>
              </div>
              <div className="bg-zinc-950 rounded-lg p-3 border border-zinc-800">
                <p className="text-xs text-zinc-500">WhatsApp</p>
                <p className="text-white font-medium">{whatsapp}</p>
              </div>
              <div className="bg-zinc-950 rounded-lg p-3 border border-zinc-800">
                <p className="text-xs text-zinc-500">Se creará</p>
                <p className="text-white font-medium">
                  Cliente + Agente con {template.tools_count} herramientas
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 px-4 py-2.5 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirm}
                disabled={applyMutation.isPending}
                className="flex-1 px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {applyMutation.isPending && <Loader2 size={16} className="animate-spin" />}
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success Modal */}
      {successData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl text-center">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 size={36} className="text-emerald-400" />
            </div>

            <h3 className="text-lg font-semibold text-white mb-2">
              Plantilla aplicada correctamente
            </h3>
            <p className="text-sm text-zinc-400 mb-6">
              Se creó el cliente y el agente IA para {successData.templateName}
            </p>

            <div className="space-y-3 mb-6 text-left">
              <div className="bg-zinc-950 rounded-lg p-3 border border-zinc-800 flex items-center justify-between">
                <div>
                  <p className="text-xs text-zinc-500">Cliente</p>
                  <p className="text-sm text-white font-medium">{name.trim()}</p>
                </div>
                <button
                  onClick={() => {
                    setSuccessData(null);
                    navigate(`/clients/${successData.clientId}`);
                  }}
                  className="text-xs text-amber-500 hover:text-amber-400 underline"
                >
                  Ver cliente
                </button>
              </div>
              <div className="bg-zinc-950 rounded-lg p-3 border border-zinc-800 flex items-center justify-between">
                <div>
                  <p className="text-xs text-zinc-500">Agente IA</p>
                  <p className="text-sm text-white font-medium">
                    Asistente {successData.templateName}
                  </p>
                </div>
                <button
                  onClick={() => {
                    setSuccessData(null);
                    navigate(`/agents/${successData.agentId}`);
                  }}
                  className="text-xs text-amber-500 hover:text-amber-400 underline"
                >
                  Ver agente
                </button>
              </div>
            </div>

            <button
              onClick={() => {
                setSuccessData(null);
                navigate("/templates");
              }}
              className="w-full px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors"
            >
              Volver a plantillas
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
