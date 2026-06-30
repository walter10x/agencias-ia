import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Send,
  Star,
  RefreshCw,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  updateLead,
  sendProactiveMessage,
  type LeadUpdateInput,
} from "@/api/lead";
import { fetchFeedbackList, type FeedbackData } from "@/api/feedback";

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [messageText, setMessageText] = useState("");

  const feedbacksQuery = useQuery({
    queryKey: ["feedback", id],
    queryFn: () =>
      fetchFeedbackList(id!, 50, 0),
    enabled: !!id,
  });

  const updateMutation = useMutation({
    mutationFn: (data: LeadUpdateInput) => updateLead(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead"] });
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: (text: string) => sendProactiveMessage(id!, text),
    onSuccess: () => {
      setMessageText("");
    },
  });

  const feedbacks: FeedbackData[] = feedbacksQuery.data?.items ?? [];

  function handleStatusChange(status: string) {
    updateMutation.mutate({ status });
  }

  function handleSendMessage() {
    if (!messageText.trim()) return;
    sendMessageMutation.mutate(messageText.trim());
  }

  return (
    <div className="p-6 space-y-6 relative">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Back button */}
      <div className="relative z-10">
        <button
          onClick={() => navigate("/leads")}
          className="flex items-center gap-2 text-sm text-zinc-500 hover:text-white transition-colors"
        >
          <ArrowLeft size={16} />
          Volver a Leads
        </button>
      </div>

      {/* Lead ID */}
      <div className="relative z-10">
        <h2 className="text-2xl font-bold text-white">Lead: {id}</h2>
        <p className="text-sm text-zinc-500 mt-1">
          Detalle y acciones sobre el lead
        </p>
      </div>

      {/* Actions */}
      <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-3">
        <h3 className="text-sm font-semibold text-white">Cambiar Estado</h3>
        <div className="flex flex-wrap gap-2">
          {["new", "contacted", "interested", "not_interested", "converted", "archived"].map(
            (status) => (
              <button
                key={status}
                onClick={() => handleStatusChange(status)}
                disabled={updateMutation.isPending}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 text-zinc-300 hover:bg-zinc-700 border border-zinc-700 transition-colors disabled:opacity-50 capitalize"
              >
                {status.replace("_", " ")}
              </button>
            ),
          )}
        </div>
      </div>

      {/* Send Message */}
      <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-3">
        <h3 className="text-sm font-semibold text-white">Enviar Mensaje Proactivo</h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
            placeholder="Escribe el mensaje..."
            className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-zinc-600 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 outline-none transition-colors"
          />
          <button
            onClick={handleSendMessage}
            disabled={sendMessageMutation.isPending || !messageText.trim()}
            className="px-4 py-2.5 bg-amber-500 text-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {sendMessageMutation.isPending ? (
              <RefreshCw size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
            Enviar
          </button>
        </div>
      </div>

      {/* Feedback History */}
      <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-white mb-3">
          Feedback Recibido
        </h3>
        {feedbacks.length === 0 ? (
          <p className="text-sm text-zinc-500">Sin feedback aún</p>
        ) : (
          <div className="space-y-2">
            {feedbacks.map((fb) => (
              <div
                key={fb.id}
                className="flex items-start gap-3 p-3 bg-zinc-950 rounded-lg"
              >
                <div className="flex items-center gap-1">
                  {Array.from({ length: fb.rating }).map((_, i) => (
                    <Star
                      key={i}
                      size={12}
                      className="text-amber-400 fill-amber-400"
                    />
                  ))}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white">{fb.comment || "Sin comentario"}</p>
                  <p className="text-xs text-zinc-600 mt-1">{fb.created_at}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
