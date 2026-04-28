type AssistantActivityMessage = {
  role: string;
  parts?: Array<{
    type: string;
    text?: string;
  }>;
};

export const INITIAL_ASSISTANT_STATUS_LABEL =
  "Iniciando o AI Assistant e verificando serviços.";
const FINALIZATION_RESPONSE_LABEL = "Salvando hist\u00f3rico da conversa...";

/** Shown while the request is in flight and no backend status line arrived yet. */
export const DEFAULT_ASSISTANT_ACTIVITY_LABEL = INITIAL_ASSISTANT_STATUS_LABEL;

const FINALIZATION_STATUS_PATTERNS = [
  "salvando contexto",
  "saving context",
  "salvando o contexto",
  "salvando historico",
  "salvando histórico",
  "saving history",
  "gravando a mensagem",
  "updating the summary",
  "atualizando o resumo",
];

const foldStatusMessage = (value: string) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

function hasMatchingPattern(statusMessage: string, patterns: string[]) {
  const folded = foldStatusMessage(statusMessage);
  return patterns.some((pattern) => folded.includes(pattern));
}

/** Next.js route emits this while persisting messages / summary; input stays disabled until the stream closes. */
export function isFinalizationPhaseStatus(statusMessage: string) {
  return hasMatchingPattern(statusMessage, FINALIZATION_STATUS_PATTERNS);
}

export function normalizeAssistantStatusMessage(statusMessage?: string) {
  return statusMessage?.trim() || undefined;
}

export function getAssistantActivityLabel(statusMessage?: string) {
  return normalizeAssistantStatusMessage(statusMessage);
}

function getPhaseLabel({
  normalizedStatusMessage,
}: {
  normalizedStatusMessage?: string;
}) {
  if (!normalizedStatusMessage) {
    return INITIAL_ASSISTANT_STATUS_LABEL;
  }

  if (isFinalizationPhaseStatus(normalizedStatusMessage)) {
    return FINALIZATION_RESPONSE_LABEL;
  }

  return normalizedStatusMessage;
}

/**
 * Keeps backend activity labels visible while the request is active, and keeps
 * finalization messages intact for the post-response persistence phase.
 */
export function getEffectiveAssistantStatusMessage({
  messages,
  status,
  statusMessage,
}: {
  messages: AssistantActivityMessage[];
  status: string;
  statusMessage?: string;
}): string | undefined {
  const normalizedStatusMessage = normalizeAssistantStatusMessage(statusMessage);

  if (status === "ready") {
    if (
      normalizedStatusMessage &&
      isFinalizationPhaseStatus(normalizedStatusMessage)
    ) {
      return FINALIZATION_RESPONSE_LABEL;
    }
    return undefined;
  }

  if (status !== "submitted" && status !== "streaming") {
    return undefined;
  }

  return getPhaseLabel({
    normalizedStatusMessage,
  });
}

export function hasRenderableAssistantContent(message?: AssistantActivityMessage) {
  if (!message || message.role !== "assistant") {
    return false;
  }

  const parts = message.parts ?? [];

  return parts.some((part) => {
    if (part.type === "text" || part.type === "reasoning") {
      return (part.text?.trim().length ?? 0) > 0;
    }

    return part.type.startsWith("tool-");
  });
}

export function shouldShowAssistantActivity({
  messages,
  status,
  statusMessage,
}: {
  messages: AssistantActivityMessage[];
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
    return effective === FINALIZATION_RESPONSE_LABEL;
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
