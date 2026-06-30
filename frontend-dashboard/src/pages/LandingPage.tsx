import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Send, Loader2, CheckCircle, AlertTriangle } from "lucide-react";
import { fetchLandingPublicConfig, submitLandingForm, type LandingPublicConfig } from "@/api/landing";

export default function LandingPage() {
  const { slug } = useParams<{ slug: string }>();
  const [config, setConfig] = useState<LandingPublicConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [interest, setInterest] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [autoReply, setAutoReply] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ name?: string; whatsapp?: string }>({});

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    fetchLandingPublicConfig(slug)
      .then(setConfig)
      .catch(() => setError("No encontrada"))
      .finally(() => setLoading(false));
  }, [slug]);

  function validate(): boolean {
    const errors: { name?: string; whatsapp?: string } = {};
    if (!name.trim()) errors.name = "El nombre es obligatorio";
    const digits = whatsapp.replace(/\D/g, "");
    if (digits.length < 10) errors.whatsapp = "WhatsApp debe tener al menos 10 dígitos";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate() || !slug) return;

    setSubmitting(true);
    try {
      const result = await submitLandingForm(slug, {
        name: name.trim(),
        whatsapp: whatsapp.replace(/\D/g, ""),
        interest: interest.trim(),
      });
      setAutoReply(result.auto_reply);
      setSubmitted(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al enviar";
      setFieldErrors({ whatsapp: msg.includes("Too many") ? "Demasiados envíos. Espera un minuto." : msg });
    } finally {
      setSubmitting(false);
    }
  }

  const primaryColor = config?.landing_primary_color ?? "#f59e0b";

  // Loading skeleton
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
        </div>
        <div className="relative z-10 w-full max-w-md space-y-6 animate-pulse">
          <div className="h-6 w-48 bg-zinc-800 rounded mx-auto" />
          <div className="h-4 w-64 bg-zinc-800 rounded mx-auto" />
          <div className="space-y-3 mt-8">
            <div className="h-12 bg-zinc-800 rounded-xl" />
            <div className="h-12 bg-zinc-800 rounded-xl" />
            <div className="h-12 bg-zinc-800 rounded-xl" />
            <div className="h-12 bg-zinc-800 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  // Error or not found
  if (error || !config) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black p-4">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
        </div>
        <div className="relative z-10 text-center space-y-4">
          <AlertTriangle size={48} className="text-amber-500 mx-auto stroke-[1.5]" />
          <h2 className="text-xl font-semibold text-white">Página no encontrada</h2>
          <p className="text-sm text-zinc-500">La landing que buscas no existe o está desactivada.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-black p-4">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full blur-[100px]"
          style={{ backgroundColor: `${primaryColor}0D` }} />
      </div>

      <div className="relative z-10 w-full max-w-md space-y-8 rounded-2xl bg-zinc-900 p-8 shadow-2xl border border-zinc-800">
        {/* Header */}
        <div className="text-center space-y-3">
          <h1 className="text-2xl font-bold text-white">{config.landing_title}</h1>
          <p className="text-sm text-zinc-500">{config.landing_description}</p>
        </div>

        {submitted ? (
          /* Success state */
          <div className="text-center space-y-4 py-4">
            <CheckCircle size={48} className="text-emerald-400 mx-auto stroke-[1.5] animate-[fadeIn_0.3s_ease-out]" />
            <h3 className="text-lg font-semibold text-white">¡Gracias {name.trim()}!</h3>
            <p className="text-sm text-zinc-400">{autoReply}</p>
          </div>
        ) : (
          /* Form */
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Tu nombre completo"
                maxLength={200}
                className={`w-full px-4 py-3 bg-zinc-800 border rounded-xl text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 transition-colors ${fieldErrors.name ? "border-red-500/50 focus:ring-red-500/20" : "border-zinc-700 focus:ring-amber-500/20"}`}
                style={{ borderColor: fieldErrors.name ? undefined : undefined }}
              />
              {fieldErrors.name && (
                <p className="mt-1 text-xs text-red-400">{fieldErrors.name}</p>
              )}
            </div>

            <div>
              <input
                type="tel"
                value={whatsapp}
                onChange={(e) => setWhatsapp(e.target.value.replace(/\D/g, ""))}
                placeholder="5491122334455"
                maxLength={20}
                className={`w-full px-4 py-3 bg-zinc-800 border rounded-xl text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 transition-colors ${fieldErrors.whatsapp ? "border-red-500/50 focus:ring-red-500/20" : "border-zinc-700 focus:ring-amber-500/20"}`}
              />
              {fieldErrors.whatsapp && (
                <p className="mt-1 text-xs text-red-400">{fieldErrors.whatsapp}</p>
              )}
            </div>

            <div>
              <textarea
                value={interest}
                onChange={(e) => setInterest(e.target.value)}
                placeholder="¿En qué estás interesado?"
                maxLength={1000}
                rows={3}
                className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-colors resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-black font-semibold transition-colors disabled:opacity-50"
              style={{ backgroundColor: primaryColor }}
            >
              {submitting ? (
                <>
                  <Loader2 size={18} className="animate-spin" /> Enviando...
                </>
              ) : (
                <>
                  <Send size={18} /> Enviar
                </>
              )}
            </button>
          </form>
        )}

        {/* Footer */}
        <p className="text-center text-xs text-zinc-600">Powered by Agencia IA</p>
      </div>
    </div>
  );
}
