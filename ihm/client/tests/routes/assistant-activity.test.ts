import { expect, test } from "@playwright/test";
import {
  getAssistantActivityLabel,
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
  test("normalizes terminal backend statuses to a neutral UI label", () => {
    expect(
      getAssistantActivityLabel(
        "Inferência concluída com sucesso. Assistente está pronto para processar mensagens."
      )
    ).toBe("Preparando resposta...");
  });

  test("falls back to the default label when backend status is empty", () => {
    expect(getAssistantActivityLabel("   ")).toBe("Pensando...");
    expect(getAssistantActivityLabel(undefined)).toBe("Pensando...");
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
      })
    ).toBeTruthy();

    expect(
      shouldShowAssistantActivity({
        messages: [userMessage, emptyAssistantMessage],
        status: "streaming",
      })
    ).toBeTruthy();

    expect(
      shouldShowAssistantActivity({
        messages: [userMessage, finalAssistantMessage],
        status: "streaming",
      })
    ).toBeFalsy();
  });
});
