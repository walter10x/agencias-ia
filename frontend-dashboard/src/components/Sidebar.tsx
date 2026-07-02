import { NavLink } from "react-router-dom";
import { useState, useEffect } from "react";
import { Bot, Users, MessageSquare, ChevronLeft, ChevronRight, LogOut, LayoutTemplate, User, FileText } from "lucide-react";
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
        `flex items-center ${isCollapsed ? "justify-center px-2" : "gap-3 px-4"} py-3 rounded-xl transition-all duration-200 group relative
        ${isActive
          ? "bg-amber-500/10 text-amber-500 font-medium shadow-sm shadow-amber-500/5"
          : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"}`
      }
    >
      <Icon size={20} className={`stroke-[1.5] ${isCollapsed ? "mx-auto" : ""}`} />
      {!isCollapsed && <span className="text-sm truncate">{label}</span>}
      {isCollapsed && (
        <div className="absolute left-full ml-2 px-2 py-1 bg-zinc-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 border border-zinc-700 shadow-xl transition-opacity">
          {label}
        </div>
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
      className={`${isCollapsed ? "w-20" : "w-64"} h-full bg-zinc-950 border-r border-zinc-800 flex flex-col transition-all duration-300 ease-in-out ${className}`}
    >
      <div className={`p-4 border-b border-zinc-900 flex items-center ${isCollapsed ? "justify-center" : "gap-3"} h-[73px]`}>
        <span className="text-2xl bg-amber-500 rounded-lg w-8 h-8 flex items-center justify-center text-black font-bold shrink-0">
          A
        </span>
        {!isCollapsed && (
          <div className="overflow-hidden">
            <h1 className="text-sm font-bold text-white leading-tight uppercase italic tracking-tighter">
              Agencia IA
            </h1>
            <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-mono truncate block italic">
              Panel de Control
            </span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto py-6 px-3 space-y-8 scrollbar-hide">
        <div className="space-y-1">
          {!isCollapsed && (
            <div className="px-4 text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-2 font-mono">
              Principal
            </div>
          )}
          <NavItem to="/app" icon={Bot} label="Dashboard" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
        </div>

        {isSuperadmin ? (
          <>
            <div className="space-y-1">
              {!isCollapsed && (
                <div className="px-4 text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-2 font-mono">
                  Gestión
                </div>
              )}
              <NavItem to="/app/clients" icon={Users} label="Clientes" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
              <NavItem to="/app/agents" icon={Bot} label="Agentes IA" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
              <NavItem to="/app/templates" icon={LayoutTemplate} label="Plantillas" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
            </div>

            <div className="space-y-1">
              {!isCollapsed && (
                <div className="px-4 text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-2 font-mono">
                  Monitoreo
                </div>
              )}
              <NavItem to="/app/conversations" icon={MessageSquare} label="Conversaciones" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
            </div>
          </>
        ) : (
          <div className="space-y-1">
            {!isCollapsed && (
              <div className="px-4 text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-2 font-mono">
                Mi negocio
              </div>
            )}
            <NavItem to="/app/conversations" icon={MessageSquare} label="Conversaciones" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
            <NavItem to="/app/leads" icon={FileText} label="Leads" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
            <NavItem to="/app/profile" icon={User} label="Perfil" onCloseMobile={onCloseMobile} isCollapsed={isCollapsed} />
          </div>
        )}
      </div>

      <div className="border-t border-zinc-900 bg-zinc-900/30">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="w-full flex items-center justify-center p-2 text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors border-b border-zinc-900/50"
          title={isCollapsed ? "Expandir" : "Colapsar"}
        >
          {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>

        <div className={`p-4 ${isCollapsed ? "flex flex-col items-center gap-2" : ""}`}>
          <div className={`flex items-center ${isCollapsed ? "justify-center" : "gap-3 mb-4"} px-2`}>
            <div className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs font-bold ring-2 ring-zinc-800 shrink-0">
              {initials}
            </div>
            {!isCollapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{user?.name || "Usuario"}</p>
                <p className="text-[10px] text-zinc-500 truncate">{user?.email || ""}</p>
              </div>
            )}
          </div>
          <button
            onClick={logout}
            title={isCollapsed ? "Cerrar Sesión" : undefined}
            className={`w-full flex items-center ${isCollapsed ? "justify-center" : "justify-center gap-2"} px-4 py-2 bg-zinc-800 hover:bg-red-500/10 hover:text-red-400 text-zinc-400 text-xs font-medium rounded-lg transition-colors border border-zinc-700/50 hover:border-red-500/20 mt-2`}
          >
            <LogOut size={14} />
            {!isCollapsed && "Cerrar Sesión"}
          </button>
        </div>
      </div>
    </div>
  );
}
