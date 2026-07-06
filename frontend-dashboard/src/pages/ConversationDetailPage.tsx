import { useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Phone, Send, Check, AlertTriangle, MinusCircle } from "lucide-react";
import { fetchConversationMessages, type MessageData } from "@/api/conversation";

/** Indicador discreto del estado de entrega de un mensaje saliente. */
function DeliveryStatus({ status }: { status: MessageData["status"] }) {
  if (status === "failed") {
    return (
      <span className="inline-flex items-center gap-0.5 text-red-400" title="No se pudo entregar">
        <AlertTriangle size={10} /> Fallido
      </span>
    );
  }
  if (status === "skipped") {
    return (
      <span className="inline-flex items-center gap-0.5 text-zinc-500" title="WhatsApp no configurado: no se envió">
        <MinusCircle size={10} /> Omitido
      </span>
    );
  }
  // "sent" (o cualquier otro) => entregado
  return (
    <span className="inline-flex items-center gap-0.5 text-amber-500/60" title="Enviado">
      <Check size={10} /> Enviado
    </span>
  );
}

function ChatBubble({ message }: { message: MessageData }) {
  const isAssistant = message.role === "assistant";
  const isSystem = message.role === "system";

  const time = new Date(message.created_at).toLocaleTimeString("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
  });

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2 text-xs text-zinc-500 italic max-w-lg text-center">
          {message.content}
          <p className="text-zinc-600 text-[10px] mt-1">{time}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isAssistant ? "justify-end" : "justify-start"} my-1`}>
      <div
        className={`max-w-[80%] lg:max-w-[60%] rounded-2xl px-4 py-2.5 ${
          isAssistant
            ? "bg-amber-500/10 text-amber-100 rounded-br-md"
            : "bg-zinc-800 text-white rounded-bl-md"
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <p className={`text-[10px] mt-1 flex items-center gap-1.5 ${isAssistant ? "text-amber-500/50 justify-end" : "text-zinc-500"}`}>
          {time}
          {isAssistant && (
            <>
              <span className="text-amber-500/30">·</span>
              <DeliveryStatus status={message.status} />
            </>
          )}
        </p>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex-1 space-y-4 p-6">
      {Array.from({ length: 6 }).map((_, i) => {
        const isRight = i % 2 === 1;
        return (
          <div key={i} className={`flex ${isRight ? "justify-end" : "justify-start"}`}>
            <div className={`animate-pulse rounded-2xl p-4 ${isRight ? "bg-amber-500/5" : "bg-zinc-800/50"} ${isRight ? "w-2/3" : "w-1/2"}`}>
              <div className="h-3 bg-zinc-700/50 rounded w-full mb-2" />
              <div className="h-3 bg-zinc-700/50 rounded w-3/4" />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function ConversationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const messagesQuery = useQuery({
    queryKey: ["conversation-messages", id],
    queryFn: () => fetchConversationMessages(id!),
    enabled: !!id,
  });

  const messages = messagesQuery.data?.messages ?? [];
  const phoneNumber = messagesQuery.data?.phone_number ?? "";
  const status = messagesQuery.data?.status ?? "";
  const isLoading = messagesQuery.isLoading;
  const isError = messagesQuery.error;

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full relative">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <div className="relative z-10 bg-zinc-950/80 backdrop-blur-sm border-b border-zinc-800 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-lg hover:bg-zinc-800 transition-colors text-zinc-400 hover:text-white"
        >
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <Phone size={14} className="text-zinc-500" />
            <span className="text-white font-medium">{phoneNumber || "Cargando..."}</span>
          </div>
          {status && (
            <span className={`text-xs px-2 py-0.5 rounded-md ${
              status === "active"
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-zinc-800 text-zinc-500"
            }`}>
              {status === "active" ? "Activo" : status === "closed" ? "Cerrado" : "Archivado"}
            </span>
          )}
        </div>
      </div>

      {/* Error */}
      {isError && (
        <div className="relative z-10 bg-red-500/10 border border-red-500/20 rounded-xl mx-6 mt-6 px-4 py-3 text-sm text-red-400 flex items-center gap-3">
          <span>Conversación no encontrada</span>
          <button onClick={() => navigate(-1)} className="underline hover:text-red-300">Volver</button>
        </div>
      )}

      {/* Loading */}
      {isLoading && <LoadingSkeleton />}

      {/* Messages Area */}
      {!isLoading && !isError && (
        <div className="relative z-10 flex-1 overflow-y-auto px-6 py-4 space-y-1">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-sm text-zinc-500">No hay mensajes en esta conversación</p>
            </div>
          ) : (
            <>
              {messages.map((msg: MessageData) => (
                <ChatBubble key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      )}

      {/* Input Footer (placeholder) */}
      <div className="relative z-10 bg-zinc-950 border-t border-zinc-800 px-6 py-4">
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Escribe un mensaje..."
            disabled
            className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-white text-sm placeholder:text-zinc-600 outline-none opacity-50 cursor-not-allowed"
          />
          <button
            disabled
            className="p-3 bg-amber-500/30 text-zinc-500 rounded-xl cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
