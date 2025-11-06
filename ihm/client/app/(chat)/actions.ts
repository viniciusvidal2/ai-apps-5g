"use server";

import { type UIMessage } from "ai";
import { cookies } from "next/headers";
import type { VisibilityType } from "@/components/visibility-selector";
import {
  deleteMessagesByChatIdAfterTimestamp,
  getMessageById,
  updateChatVisiblityById,
} from "@/lib/db/queries";

export async function saveChatModelAsCookie(model: string) {
  const cookieStore = await cookies();
  // Only save valid models
  if (model === "search-mode-default" || model === "search-mode-wide") {
    cookieStore.set("chat-model", model);
  } else {
    // Clear invalid cookie
    cookieStore.delete("chat-model");
  }
}

export async function generateTitleFromUserMessage({
  message,
}: {
  message: UIMessage;
}) {
  // Extract text from message parts
  const textPart = message.parts.find((p) => p.type === "text");
  const text = textPart && "text" in textPart ? textPart.text : "";
  
  // Generate simple title from first 50 characters
  const title = text.length > 50 
    ? text.substring(0, 50).trim() + "..." 
    : text || "Nova conversa";
  
  return title;
}

export async function deleteTrailingMessages({ id }: { id: string }) {
  const [message] = await getMessageById({ id });

  await deleteMessagesByChatIdAfterTimestamp({
    chatId: message.chatId,
    timestamp: message.createdAt,
  });
}

export async function updateChatVisibility({
  chatId,
  visibility,
}: {
  chatId: string;
  visibility: VisibilityType;
}) {
  await updateChatVisiblityById({ chatId, visibility });
}
