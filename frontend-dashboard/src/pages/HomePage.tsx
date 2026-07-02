import { Link } from "react-router-dom";
import { Bot, MessageSquare, Zap, ArrowRight, Check, Store, Stethoscope, Building2, ShoppingBag, GraduationCap, Wrench } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const steps = [
  {
    icon: Bot,
    title: "Regístrate",
    description: "Crea tu cuenta en minutos y configura tu negocio.",
  },
  {
    icon: MessageSquare,
    title: "Conecta WhatsApp",
    description: "Vincula tu número de WhatsApp con tu agente IA.",
  },
  {
    icon: Zap,
    title: "El agente trabaja por ti",
    description: "Automatiza respuestas, genera leads y ahorra tiempo.",
  },
];

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "/mes",
    features: ["1 agente IA", "50 conversaciones/mes", "Soporte básico"],
    featured: false,
  },
  {
    name: "Pro",
    price: "$29",
    period: "/mes",
    features: ["3 agentes IA", "Conversaciones ilimitadas", "Soporte prioritario", "Plantillas personalizadas", "Analíticas avanzadas"],
    featured: true,
  },
  {
    name: "Enterprise",
    price: "$99",
    period: "/mes",
    features: ["Agentes ilimitados", "API dedicada", "Soporte 24/7", "Onboarding personalizado", "SLA garantizado"],
    featured: false,
  },
];

const businessTypes = [
  { icon: Store, label: "Restaurantes" },
  { icon: Stethoscope, label: "Clínicas" },
  { icon: Building2, label: "Inmobiliarias" },
  { icon: ShoppingBag, label: "E-Commerce" },
  { icon: GraduationCap, label: "Educación" },
  { icon: Wrench, label: "Servicios" },
];

export default function HomePage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navbar */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-md border-b border-zinc-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-amber-500 flex items-center justify-center">
                <span className="text-lg font-black text-black">A</span>
              </div>
              <span className="font-bold text-lg">Agencia IA</span>
            </div>
            <nav className="flex items-center gap-4">
              {isAuthenticated ? (
                <Link
                  to="/app"
                  className="flex items-center gap-2 bg-amber-500 text-black px-5 py-2 rounded-lg font-semibold text-sm hover:bg-amber-400 transition-colors"
                >
                  Ir a mi panel
                  <ArrowRight size={16} />
                </Link>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="text-zinc-400 hover:text-white text-sm font-medium transition-colors"
                  >
                    Iniciar sesión
                  </Link>
                  <Link
                    to="/register"
                    className="bg-amber-500 text-black px-5 py-2 rounded-lg font-semibold text-sm hover:bg-amber-400 transition-colors"
                  >
                    Comenzar ahora
                  </Link>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative pt-32 pb-20 px-4 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-amber-500/5 rounded-full blur-[150px]" />
          <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] bg-amber-500/5 rounded-full blur-[80px]" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium mb-8">
            <Zap size={14} />
            IA para WhatsApp
          </div>
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-tight mb-6">
            Potencia tu negocio
            <br />
            con un{" "}
            <span className="bg-gradient-to-r from-amber-400 to-amber-500 bg-clip-text text-transparent">
              Agente IA
            </span>
          </h1>
          <p className="text-lg sm:text-xl text-zinc-400 max-w-2xl mx-auto mb-10">
            Automatiza la atención al cliente, genera leads calificados y haz crecer tu negocio
            con un agente de inteligencia artificial en WhatsApp.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/register"
              className="bg-amber-500 text-black px-8 py-3.5 rounded-xl font-bold text-base hover:bg-amber-400 transition-colors shadow-lg shadow-amber-500/20 inline-flex items-center gap-2"
            >
              Comenzar ahora
              <ArrowRight size={18} />
            </Link>
            <a
              href="#how-it-works"
              className="text-zinc-400 hover:text-white px-8 py-3.5 rounded-xl border border-zinc-800 font-medium text-base transition-colors"
            >
              Cómo funciona
            </a>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-20 px-4 border-t border-zinc-900">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">¿Cómo funciona?</h2>
            <p className="text-zinc-400 max-w-xl mx-auto">
              En tres simples pasos puedes tener tu agente IA operando en WhatsApp.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((step, i) => (
              <div key={step.title} className="relative p-8 rounded-2xl bg-zinc-900/50 border border-zinc-800 text-center group hover:bg-zinc-900 transition-colors">
                <div className="w-16 h-16 rounded-xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6 group-hover:bg-amber-500/20 transition-colors">
                  <step.icon className="w-8 h-8 text-amber-500" />
                </div>
                <div className="absolute top-4 right-4 w-8 h-8 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center text-sm font-bold">
                  {i + 1}
                </div>
                <h3 className="text-xl font-bold mb-3">{step.title}</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Plans */}
      <section className="py-20 px-4 border-t border-zinc-900">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Planes</h2>
            <p className="text-zinc-400 max-w-xl mx-auto">
              Elige el plan que mejor se adapte a tu negocio.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`relative p-8 rounded-2xl border ${
                  plan.featured
                    ? "bg-amber-500/5 border-amber-500/30 shadow-xl shadow-amber-500/10"
                    : "bg-zinc-900/50 border-zinc-800"
                }`}
              >
                {plan.featured && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-amber-500 text-black text-xs font-bold rounded-full">
                    Recomendado
                  </div>
                )}
                <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
                <div className="flex items-baseline gap-1 mb-6">
                  <span className="text-4xl font-black">{plan.price}</span>
                  <span className="text-zinc-500 text-sm">{plan.period}</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-3 text-sm text-zinc-300">
                      <Check size={16} className="text-amber-500 shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to="/register"
                  className={`block w-full text-center py-3 rounded-xl font-semibold text-sm transition-colors ${
                    plan.featured
                      ? "bg-amber-500 text-black hover:bg-amber-400"
                      : "bg-zinc-800 text-white hover:bg-zinc-700"
                  }`}
                >
                  Comenzar
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Business types */}
      <section className="py-20 px-4 border-t border-zinc-900">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">¿Para quién es?</h2>
            <p className="text-zinc-400 max-w-xl mx-auto">
              Nuestra plataforma se adapta a cualquier tipo de negocio.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {businessTypes.map((type) => (
              <div
                key={type.label}
                className="flex flex-col items-center gap-3 p-6 rounded-xl bg-zinc-900/50 border border-zinc-800 hover:bg-zinc-900 hover:border-zinc-700 transition-colors group"
              >
                <div className="w-12 h-12 rounded-lg bg-amber-500/10 flex items-center justify-center group-hover:bg-amber-500/20 transition-colors">
                  <type.icon className="w-6 h-6 text-amber-500" />
                </div>
                <span className="text-sm font-medium text-zinc-300">{type.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-900 py-8 px-4">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-amber-500 flex items-center justify-center">
              <span className="text-xs font-black text-black">A</span>
            </div>
            <span className="text-sm font-semibold text-zinc-400">Agencia IA</span>
          </div>
          <p className="text-xs text-zinc-600">
            &copy; {new Date().getFullYear()} Agencia IA. Todos los derechos reservados.
          </p>
        </div>
      </footer>
    </div>
  );
}
