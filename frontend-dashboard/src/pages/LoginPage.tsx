export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-black">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-amber-500/5 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-md space-y-8 rounded-2xl bg-zinc-900 p-8 shadow-2xl border border-zinc-800">
        {/* Logo */}
        <div className="text-center space-y-3">
          <div className="w-14 h-14 rounded-xl bg-amber-500 flex items-center justify-center mx-auto">
            <span className="text-2xl font-black text-black">A</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Agencia IA</h1>
          <p className="text-sm text-zinc-500">
            Panel de control para agentes de IA
          </p>
        </div>

        {/* Form */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">
              Email
            </label>
            <input
              type="email"
              placeholder="admin@agencia-ia.com"
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">
              Contraseña
            </label>
            <input
              type="password"
              placeholder="••••••••"
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
            />
          </div>

          <button className="w-full bg-amber-500 text-black font-semibold rounded-lg px-4 py-2.5 hover:bg-amber-400 transition-colors text-sm">
            Iniciar sesión
          </button>
        </div>

        <p className="text-center text-xs text-zinc-600">
          Acceso exclusivo para administradores
        </p>
      </div>
    </div>
  );
}
