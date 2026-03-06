import type { ChatMessage } from "./types";

const PREPARING_RESPONSE_MESSAGE = "Preparando resposta...";
const FALLBACK_ACTIVITY_MESSAGE = "Pensando...";

const foldStatusMessage = (value: string) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

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
  return normalizeAssistantStatusMessage(statusMessage) ?? FALLBACK_ACTIVITY_MESSAGE;
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
}: {
  messages: ChatMessage[];
  status: string;
}) {
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

  return !hasRenderableAssistantContent(lastMessage);
}
