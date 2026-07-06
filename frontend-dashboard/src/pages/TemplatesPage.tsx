import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { LayoutTemplate, Wrench, RefreshCw } from "lucide-react";
import { fetchTemplates } from "@/api/template";

export default function TemplatesPage() {
  const navigate = useNavigate();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  const templates = data?.templates ?? [];

  return (
    <div className="p-6 space-y-6 relative">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <div className="relative z-10">
        <h2 className="text-2xl font-bold text-white">Plantillas de Servicio</h2>
        <p className="text-sm text-zinc-500 mt-1">
          Selecciona una plantilla y crea un Cliente + Agente IA preconfigurado en 1 click
        </p>
      </div>

      {/* Error */}
      {isError && (
        <div className="relative z-10 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400 flex items-center gap-3">
          <span>Error al cargar plantillas</span>
          <button onClick={() => refetch()} className="underline hover:text-red-300">Reintentar</button>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 animate-pulse space-y-4">
              <div className="h-12 w-12 bg-zinc-800 rounded-xl mx-auto" />
              <div className="h-5 w-32 bg-zinc-800 rounded mx-auto" />
              <div className="h-4 w-full bg-zinc-800 rounded" />
              <div className="h-4 w-3/4 bg-zinc-800 rounded mx-auto" />
              <div className="h-6 w-24 bg-zinc-800 rounded mx-auto" />
              <div className="h-10 w-full bg-zinc-800 rounded-lg" />
            </div>
          ))}
        </div>
      )}

      {/* Grid */}
      {!isLoading && !isError && (
        <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {templates.map((t) => (
            <div
              key={t.slug}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 hover:border-zinc-700 transition-colors flex flex-col"
            >
              {/* Emoji */}
              <div className="text-5xl text-center mb-4">{t.emoji}</div>

              {/* Name */}
              <h3 className="text-lg font-semibold text-white text-center mb-2">{t.name}</h3>

              {/* Description */}
              <p className="text-sm text-zinc-400 text-center mb-4 flex-1 line-clamp-2">
                {t.description}
              </p>

              {/* Tools badge */}
              <div className="flex items-center justify-center gap-1.5 mb-5">
                <Wrench size={14} className="text-zinc-500" />
                <span className="text-xs text-zinc-500 font-medium">
                  {t.tools_count} {t.tools_count === 1 ? "herramienta" : "herramientas"}
                </span>
              </div>

              {/* Apply button */}
              <button
                onClick={() => navigate(`/app/templates/${t.slug}/apply`)}
                className="w-full py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors flex items-center justify-center gap-2"
              >
                <LayoutTemplate size={16} />
                Aplicar plantilla
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Empty (shouldn't happen, but handle gracefully) */}
      {!isLoading && !isError && templates.length === 0 && (
        <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6">
            <LayoutTemplate size={32} className="text-amber-500 stroke-[1.5]" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">No hay plantillas disponibles</h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto">
            Intenta recargar la página más tarde.
          </p>
          <button
            onClick={() => refetch()}
            className="mt-6 px-4 py-2 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors inline-flex items-center gap-2"
          >
            <RefreshCw size={16} />
            Recargar
          </button>
        </div>
      )}
    </div>
  );
}
