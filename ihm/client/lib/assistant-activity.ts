import type { ChatMessage } from "./types";

const PREPARING_RESPONSE_MESSAGE = "Preparando resposta...";

const STREAMING_FALLBACK_LABEL = "Gerando resposta...";

/** Shown while the request is in flight and no backend status line arrived yet. */
export const DEFAULT_ASSISTANT_ACTIVITY_LABEL = "AI Assistant";

const foldStatusMessage = (value: string) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

/** Backend still reports early preflight while tokens are already visible in the assistant bubble. */
export function isStalePreflightAssistantStatus(statusMessage: string) {
  const folded = foldStatusMessage(statusMessage);
  return (
    folded.includes("enviando consulta") ||
    folded === "ai assistant" ||
    folded.includes("sending query to") ||
    folded.includes("sending query")
  );
}

/** Next.js route emits this while persisting messages / summary; input stays disabled until the stream closes. */
export function isFinalizationPhaseStatus(statusMessage: string) {
  const folded = foldStatusMessage(statusMessage);
  return (
    folded.includes("salvando contexto") ||
    folded.includes("saving context") ||
    folded.includes("salvando o contexto")
  );
}

export function normalizeAssistantStatusMessage(statusMessage?: string) {
  const trimmedMessage = statusMessage?.trim();

  if (!trimmedMessage) {
    return undefined;
  }

  const foldedMessage = foldStatusMessage(trimmedMessage);

  const isTerminalStatus =
    foldedMessage.includes("concluida com sucesso") ||
    foldedMessage.includes("concluida") ||
    foldedMessage.includes("completed successfully") ||
    foldedMessage.includes("ready to process messages") ||
    foldedMessage.includes("pronto para processar mensagens");

  if (isTerminalStatus) {
    return PREPARING_RESPONSE_MESSAGE;
  }

  return trimmedMessage;
}

export function getAssistantActivityLabel(statusMessage?: string) {
  return normalizeAssistantStatusMessage(statusMessage);
}

/**
 * Maps misleading backend labels to clearer UI copy while the assistant message already shows streamed text,
 * and keeps finalization messages intact for the post-response persistence phase.
 */
export function getEffectiveAssistantStatusMessage({
  messages,
  status,
  statusMessage,
}: {
  messages: ChatMessage[];
  status: string;
  statusMessage?: string;
}): string | undefined {
  const normalized = normalizeAssistantStatusMessage(statusMessage);

  const lastMessage = messages.at(-1);
  const assistantHasRenderableText =
    lastMessage?.role === "assistant" &&
    hasRenderableAssistantContent(lastMessage);

  if (status === "ready") {
    if (normalized && isFinalizationPhaseStatus(normalized)) {
      return normalized;
    }
    return undefined;
  }

  if (status !== "submitted" && status !== "streaming") {
    return undefined;
  }

  const baseLabel = normalized ?? DEFAULT_ASSISTANT_ACTIVITY_LABEL;

  if (!assistantHasRenderableText) {
    return baseLabel;
  }

  if (isStalePreflightAssistantStatus(baseLabel)) {
    return STREAMING_FALLBACK_LABEL;
  }

  if (normalized === PREPARING_RESPONSE_MESSAGE) {
    return STREAMING_FALLBACK_LABEL;
  }

  return baseLabel;
}

export function hasRenderableAssistantContent(message?: ChatMessage) {
  if (!message || message.role !== "assistant") {
    return false;
  }

  const parts = message.parts ?? [];

  return parts.some((part) => {
    if (part.type === "text" || part.type === "reasoning") {
      return part.text?.trim().length > 0;
    }

    return part.type.startsWith("tool-");
  });
}

export function shouldShowAssistantActivity({
  messages,
  status,
  statusMessage,
}: {
  messages: ChatMessage[];
  status: string;
  statusMessage?: string;
}) {
  const effective = getEffectiveAssistantStatusMessage({
    messages,
    status,
    statusMessage,
  });

  if (!effective?.trim()) {
    return false;
  }

  if (status === "ready") {
    return isFinalizationPhaseStatus(effective);
  }

  if (status !== "submitted" && status !== "streaming") {
    return false;
  }

  const lastMessage = messages.at(-1);

  if (!lastMessage) {
    return false;
  }

  if (lastMessage.role === "user") {
    return true;
  }

  if (lastMessage.role === "assistant") {
    if (!hasRenderableAssistantContent(lastMessage)) {
      return true;
    }

    return isFinalizationPhaseStatus(effective);
  }

  return !hasRenderableAssistantContent(lastMessage);
}
