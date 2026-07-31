import type { ReactNode } from "react";

interface PageShellProps {
  children: ReactNode;
  /** Narrower content (forms / detail). Default is list width. */
  narrow?: boolean;
  className?: string;
}

/** Contenedor centrado y compacto para pantallas del panel. */
export default function PageShell({ children, narrow = false, className = "" }: PageShellProps) {
  return (
    <div
      className={`mx-auto w-full px-4 py-4 sm:px-5 sm:py-5 space-y-4 ${
        narrow ? "max-w-2xl" : "max-w-5xl"
      } ${className}`}
    >
      {children}
    </div>
  );
}

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3 animate-fade-in">
      <div className="min-w-0 space-y-0.5">
        <h2 className="text-lg font-semibold text-white tracking-tight">{title}</h2>
        {description ? (
          <p className="text-xs text-zinc-500 leading-relaxed">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}

interface EmptyPanelProps {
  icon?: React.ElementType;
  title?: string;
  children: ReactNode;
  action?: ReactNode;
}

export function EmptyPanel({ icon: Icon, title, children, action }: EmptyPanelProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center bg-zinc-900 border border-zinc-800 rounded-xl px-5 py-8 animate-scale-in">
      {Icon ? (
        <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10">
          <Icon size={20} className="text-amber-400 stroke-[1.5]" />
        </div>
      ) : null}
      {title ? <h3 className="mb-1 text-sm font-semibold text-white">{title}</h3> : null}
      <div className="max-w-sm text-xs text-zinc-500 leading-relaxed">{children}</div>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
