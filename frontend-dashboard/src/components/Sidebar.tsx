import { NavLink } from "react-router-dom";
import { useState, useEffect } from "react";
import { Bot, Users, MessageSquare, ChevronLeft, ChevronRight, LogOut, LayoutTemplate, User, FileText, CalendarDays } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

interface SidebarProps {
  className?: string;
  onCloseMobile?: () => void;
}

interface NavItemProps {
  to: string;
  icon: React.ElementType;
  label: string;
  onCloseMobile?: () => void;
  isCollapsed?: boolean;
}

function NavItem({ to, icon: Icon, label, onCloseMobile, isCollapsed }: NavItemProps) {
  return (
    <NavLink
      to={to}
      onClick={onCloseMobile}
      title={isCollapsed ? label : undefined}
      className={({ isActive }) =>
        `flex items-center ${isCollapsed ? "justify-center px-2" : "gap-3 px-3"} py-2.5 rounded-xl transition-all duration-200 group relative
        ${isActive
          ? "bg-amber-500/10 text-amber-400 font-semibold"
          : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"}`
      }
    >
      {({ isActive }) => (
        <>
          <div className={`relative ${isCollapsed ? "" : ""}`}>
            <Icon size={isCollapsed ? 20 : 18} className={`stroke-[1.5] transition-transform duration-200 group-hover:scale-110 ${isActive ? "" : ""}`} />
            {isActive && !isCollapsed && (
              <span className="absolute -left-3 top-1/2 -translate-y-1/2 w-1 h-5 bg-amber-500 rounded-r-full" />
            )}
          </div>
          {!isCollapsed && <span className="text-sm truncate">{label}</span>}
          {isCollapsed && (
            <div className="absolute left-full ml-3 px-2.5 py-1.5 bg-zinc-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 border border-zinc-700 shadow-xl transition-all duration-200 -translate-x-1 group-hover:translate-x-0">
              {label}
            </div>
          )}
        </>
      )}
    </NavLink>
  );
}

export default function Sidebar({ className = "", onCloseMobile }: SidebarProps) {
  const { user, logout } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem("sidebar_collapsed") === "true";
  });

  const isSuperadmin = user?.role === "superadmin";
  const initials = user?.name
    ? user.name.charAt(0).toUpperCase()
    : user?.email?.charAt(0).toUpperCase() ?? "A";

  useEffect(() => {
    localStorage.setItem("sidebar_collapsed", String(isCollapsed));
  }, [isCollapsed]);

  return (
    <div
      className={`${isCollapsed ? "w-20" : "w-64"} h-full flex flex-col transition-all duration-300 ease-in-out bg-zinc-950/80 backdrop-blur-xl border-r border-zinc-800/50 ${className}`}
    >
      {/* Logo / Brand */}
      <div className={`p-4 flex items-center ${isCollapsed ? "justify-center" : "gap-3"} h-[73px] shrink-0`}>
        <div className="icon-box-lg bg-amber-500/15 ring-1 ring-amber-500/20">
          <span className="text-lg font-black text-amber-400">A</span>
        </div>
        {!isCollapsed && (
          <div className="overflow-hidden animate-fade-in">
            <h1 className="text-sm font-bold text-white leading-tight tracking-tight">
              Agencia <span className="text-amber-400">IA</span>
            </h1>
            <span className="text-[10px] text-zinc-500 tracking-wider uppercase block">
              Panel de Control
            </span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6 scrollbar-hide">
        {/* Principal */}
        <div className="space-y-1">
          {!isCollapsed && (
            <div className="px-3 mb-2">
              <span className="text-[10px] font-semibold text-zinc-600 uppercase tracking-widest">
                Principal
              </span>
            </div>
          )}
          <NavItem to="/app" icon={Bot} label="Dashboard" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
        </div>

        {isSuperadmin ? (
          <>
            {/* Gestión */}
            <div className="space-y-1">
              {!isCollapsed && (
                <div className="px-3 mb-2">
                  <span className="text-[10px] font-semibold text-zinc-600 uppercase tracking-widest">
                    Gestión
                  </span>
                </div>
              )}
              <NavItem to="/app/clients" icon={Users} label="Clientes" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
              <NavItem to="/app/agents" icon={Bot} label="Agentes IA" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
              <NavItem to="/app/templates" icon={LayoutTemplate} label="Plantillas" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
            </div>

            {/* Monitoreo */}
            <div className="space-y-1">
              {!isCollapsed && (
                <div className="px-3 mb-2">
                  <span className="text-[10px] font-semibold text-zinc-600 uppercase tracking-widest">
                    Monitoreo
                  </span>
                </div>
              )}
              <NavItem to="/app/conversations" icon={MessageSquare} label="Conversaciones" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
            </div>
          </>
        ) : (
          <div className="space-y-1">
            {!isCollapsed && (
              <div className="px-3 mb-2">
                <span className="text-[10px] font-semibold text-zinc-600 uppercase tracking-widest">
                  Mi negocio
                </span>
              </div>
            )}
            <NavItem to="/app/conversations" icon={MessageSquare} label="Conversaciones" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
            <NavItem to="/app/appointments" icon={CalendarDays} label="Agenda" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
            <NavItem to="/app/leads" icon={FileText} label="Leads" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
            <NavItem to="/app/profile" icon={User} label="Perfil" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
          </div>
        )}

        {/* Collapse toggle */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={`w-full flex items-center justify-center p-1.5 text-zinc-500 hover:text-white hover:bg-zinc-800/50 rounded-lg transition-all duration-200`}
          title={isCollapsed ? "Expandir menú" : "Colapsar menú"}
        >
          {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* User Footer */}
      <div className={`p-3 ${isCollapsed ? "" : ""}`}>
        <div className={`flex items-center ${isCollapsed ? "flex-col gap-1" : "gap-3 mb-2"} px-2 py-2 bg-zinc-900/50 rounded-xl border border-zinc-800/50`}>
          <div className="w-9 h-9 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs font-bold ring-2 ring-zinc-800/50 shrink-0">
            {initials}
          </div>
          {!isCollapsed && (
            <div className="flex-1 min-w-0 animate-fade-in">
              <p className="text-sm font-medium text-white truncate">{user?.name || "Usuario"}</p>
              <p className="text-[10px] text-zinc-500 truncate">{user?.email || ""}</p>
            </div>
          )}
        </div>
        <button
          onClick={logout}
          title={isCollapsed ? "Cerrar Sesión" : undefined}
          className={`w-full flex items-center ${isCollapsed ? "justify-center p-2" : "gap-2 px-3 py-2"} text-xs font-medium rounded-lg transition-all duration-200 text-zinc-400 hover:text-red-400 hover:bg-red-500/5`}
        >
          <LogOut size={14} className="stroke-[1.5]" />
          {!isCollapsed && "Cerrar Sesión"}
        </button>
      </div>
    </div>
  );
}
