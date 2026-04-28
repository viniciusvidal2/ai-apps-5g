import { expect, test } from "@playwright/test";
import {
  DEFAULT_ASSISTANT_ACTIVITY_LABEL,
  getAssistantActivityLabel,
  getEffectiveAssistantStatusMessage,
  hasRenderableAssistantContent,
  shouldShowAssistantActivity,
} from "@/lib/assistant-activity";
import type { ChatMessage } from "@/lib/types";

const createMessage = (
  message: {
    id: string;
    role: ChatMessage["role"];
    parts: unknown[];
  }
) => message as ChatMessage;

test.describe("assistant activity helpers", () => {
  test("keeps backend status labels visible", () => {
    expect(
      getAssistantActivityLabel(
        "Inferência concluída com sucesso. Assistente está pronto para processar mensagens."
      )
    ).toBe(
      "Inferência concluída com sucesso. Assistente está pronto para processar mensagens."
    );
  });

  test("keeps explicit finalization status messages visible", () => {
    expect(
      getAssistantActivityLabel(
        "Resposta pronta. Salvando contexto da conversa..."
      )
    ).toBe("Resposta pronta. Salvando contexto da conversa...");
  });

  test("returns undefined when backend status is empty", () => {
    expect(getAssistantActivityLabel("   ")).toBeUndefined();
    expect(getAssistantActivityLabel(undefined)).toBeUndefined();
  });

  test("detects renderable assistant content only when something visible exists", () => {
    const emptyAssistantMessage = createMessage({
      id: "assistant-empty",
      role: "assistant",
      parts: [{ type: "text", text: "" }],
    });

    const reasoningAssistantMessage = createMessage({
      id: "assistant-reasoning",
      role: "assistant",
      parts: [{ type: "reasoning", text: "Analisando a consulta" }],
    });

    const toolAssistantMessage = createMessage({
      id: "assistant-tool",
      role: "assistant",
      parts: [
        {
          type: "tool-getWeather",
          toolCallId: "tool-1",
          state: "input-available",
          input: { latitude: 0, longitude: 0 },
        },
      ],
    });

    expect(hasRenderableAssistantContent(emptyAssistantMessage)).toBeFalsy();
    expect(hasRenderableAssistantContent(reasoningAssistantMessage)).toBeTruthy();
    expect(hasRenderableAssistantContent(toolAssistantMessage)).toBeTruthy();
  });

  test("shows activity while streaming until the assistant has visible content", () => {
    const userMessage = createMessage({
      id: "user-1",
      role: "user",
      parts: [{ type: "text", text: "Oi" }],
    });

    const emptyAssistantMessage = createMessage({
      id: "assistant-empty",
      role: "assistant",
      parts: [{ type: "text", text: "" }],
    });

    const finalAssistantMessage = createMessage({
      id: "assistant-final",
      role: "assistant",
      parts: [{ type: "text", text: "Resposta final" }],
    });

    expect(
      shouldShowAssistantActivity({
        messages: [userMessage],
        status: "submitted",
        statusMessage: "Preparando a inferência",
      })
    ).toBeTruthy();

    expect(
      shouldShowAssistantActivity({
        messages: [userMessage, emptyAssistantMessage],
        status: "streaming",
        statusMessage: "Gerando resposta",
      })
    ).toBeTruthy();

    expect(
      shouldShowAssistantActivity({
        messages: [userMessage, finalAssistantMessage],
        status: "streaming",
        statusMessage: "Gerando resposta",
      })
    ).toBeFalsy();

    expect(
      shouldShowAssistantActivity({
        messages: [userMessage, finalAssistantMessage],
        status: "streaming",
        statusMessage: "Resposta pronta. Salvando contexto da conversa...",
      })
    ).toBeTruthy();

    expect(
      shouldShowAssistantActivity({
        messages: [userMessage],
        status: "submitted",
        statusMessage: undefined,
      })
    ).toBeTruthy();

    expect(
      getEffectiveAssistantStatusMessage({
        messages: [userMessage],
        status: "submitted",
        statusMessage: undefined,
      })
    ).toBe(DEFAULT_ASSISTANT_ACTIVITY_LABEL);
  });

  test("shows assistant activity briefly after stream ends while finalization status is visible", () => {
    const userMessage = createMessage({
      id: "user-1",
      role: "user",
      parts: [{ type: "text", text: "Oi" }],
    });

    const finalAssistantMessage = createMessage({
      id: "assistant-final",
      role: "assistant",
      parts: [{ type: "text", text: "Resposta final" }],
    });

    expect(
      shouldShowAssistantActivity({
        messages: [userMessage, finalAssistantMessage],
        status: "ready",
        statusMessage: "Resposta pronta. Salvando contexto da conversa...",
      })
    ).toBeTruthy();
  });

  test("keeps agent pipeline status while assistant text is already visible", () => {
    const userMessage = createMessage({
      id: "user-1",
      role: "user",
      parts: [{ type: "text", text: "Oi" }],
    });

    const finalAssistantMessage = createMessage({
      id: "assistant-final",
      role: "assistant",
      parts: [{ type: "text", text: "Resposta final" }],
    });

    expect(
      getEffectiveAssistantStatusMessage({
        messages: [userMessage, finalAssistantMessage],
        status: "streaming",
        statusMessage: "Enviando consulta para o AI Assistant...",
      })
    ).toBe("Enviando consulta para o AI Assistant...");
  });

  test("keeps short AI Assistant status while assistant text is already visible", () => {
    const userMessage = createMessage({
      id: "user-1",
      role: "user",
      parts: [{ type: "text", text: "Oi" }],
    });

    const finalAssistantMessage = createMessage({
      id: "assistant-final",
      role: "assistant",
      parts: [{ type: "text", text: "Resposta final" }],
    });

    expect(
      getEffectiveAssistantStatusMessage({
        messages: [userMessage, finalAssistantMessage],
        status: "streaming",
        statusMessage: "AI Assistant",
      })
    ).toBe("AI Assistant");
  });

  test("keeps finalization status when assistant message is complete", () => {
    const userMessage = createMessage({
      id: "user-1",
      role: "user",
      parts: [{ type: "text", text: "Oi" }],
    });

    const finalAssistantMessage = createMessage({
      id: "assistant-final",
      role: "assistant",
      parts: [{ type: "text", text: "Resposta final" }],
    });

    expect(
      getEffectiveAssistantStatusMessage({
        messages: [userMessage, finalAssistantMessage],
        status: "streaming",
        statusMessage: "Resposta pronta. Salvando contexto da conversa...",
      })
    ).toBe("Resposta pronta. Salvando contexto da conversa...");
  });
});
