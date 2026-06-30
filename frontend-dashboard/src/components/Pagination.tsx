interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({
  currentPage,
  totalPages,
  onPageChange,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-4 py-4">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        className="px-4 py-2 bg-zinc-900 text-zinc-400 rounded-lg border border-zinc-800 text-sm font-medium
                   hover:bg-zinc-800 hover:text-zinc-300 transition-colors
                   disabled:opacity-40 disabled:cursor-not-allowed"
      >
        ← Anterior
      </button>

      <span className="text-sm text-zinc-500">
        Página{" "}
        <span className="text-white font-semibold">{currentPage}</span> de{" "}
        <span className="text-white font-semibold">{totalPages}</span>
      </span>

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className="px-4 py-2 bg-zinc-900 text-zinc-400 rounded-lg border border-zinc-800 text-sm font-medium
                   hover:bg-zinc-800 hover:text-zinc-300 transition-colors
                   disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Siguiente →
      </button>
    </div>
  );
}
