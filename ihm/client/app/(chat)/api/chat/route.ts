import { auth, type UserType } from "@/app/(auth)/auth";
import type { VisibilityType } from "@/components/visibility-selector";
import { entitlementsByUserType } from "@/lib/ai/entitlements";
import { chatModels } from "@/lib/ai/models";
import {
  deleteChatById,
  getChatById,
  getMessageCountByUserId,
  saveChat,
  saveMessages,
  updateChatConversationSummaryById,
} from "@/lib/db/queries";
import { ChatSDKError } from "@/lib/errors";
import type { ChatMessage } from "@/lib/types";
import { generateUUID } from "@/lib/utils";
import { generateTitleFromUserMessage } from "../../actions";
import { type PostRequestBody, postRequestBodySchema } from "./schema";

export const maxDuration = 600;

export async function POST(request: Request) {
  let requestBody: PostRequestBody;

  try {
    const json = await request.json();
    requestBody = postRequestBodySchema.parse(json);
  } catch {
    return new ChatSDKError("bad_request:api").toResponse();
  }

  try {
    const {
      id,
      message,
      selectedVisibilityType,
      sessionId,
    }: {
      id: string;
      message: ChatMessage;
      selectedVisibilityType: VisibilityType;
      sessionId?: string;
    } = requestBody;

    const session = await auth();
    if (!session?.user) {
      return new ChatSDKError("unauthorized:chat").toResponse();
    }

    const userId = session.user.id;
    const userType: UserType = session.user.type;

    const messageCount = await getMessageCountByUserId({
      id: userId,
      differenceInHours: 24,
    });

    if (messageCount > entitlementsByUserType[userType].maxMessagesPerDay) {
      return new ChatSDKError("rate_limit:chat").toResponse();
    }

    const existingChat = await getChatById({ id });

    if (existingChat) {
      if (existingChat.userId !== userId) {
        return new ChatSDKError("forbidden:chat").toResponse();
      }
    } else {
      const title = await generateTitleFromUserMessage({ message });
      await saveChat({
        id,
        userId,
        title,
        visibility: selectedVisibilityType,
      });
    }

    await saveMessages({
      messages: [
        {
          chatId: id,
          id: message.id,
          role: "user",
          parts: message.parts,
          attachments: [],
          createdAt: new Date(),
        },
      ],
    });

    const textPart = message.parts.find((part) => part.type === "text");
    const query = textPart && "text" in textPart ? textPart.text : "";

    const ragParams = requestBody.ragParams || {};
    const fallbackModel = chatModels.find(
      (model) => model.id === requestBody.selectedChatModel
    );
    const n_chunks = ragParams.n_chunks ?? fallbackModel?.n_chunks ?? 10;
    const inference_model_name = ragParams.inference_model_name;
    const collection_name = ragParams.collection_name ?? "none";
    const conversationSummary = existingChat?.conversationSummary ?? "";

    const backendUrl = process.env.BACKEND_URL || "http://localhost:8003";
    const backendResponse = await fetch(`${backendUrl}/inference`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        user_id: userId,
        session_id: sessionId || `fallback-session-${userId}`,
        conversation_summary: conversationSummary,
        n_chunks,
        collection_name,
        ...(inference_model_name ? { inference_model_name } : {}),
      }),
    });

    if (!backendResponse.ok) {
      throw new Error(`Backend error (${backendResponse.status}): ${backendResponse.statusText}`);
    }

    const stream = backendResponse.body;
    if (!stream) {
      throw new Error("No response body from backend");
    }

    const reader = stream.getReader();
    const decoder = new TextDecoder();
    const encoder = new TextEncoder();

    let assistantResponse = "";
    let latestConversationSummary = conversationSummary;
    let hasSummaryUpdate = false;
    let sseBuffer = "";

    const interceptedStream = new ReadableStream({
      async start(controller) {
        let isClosed = false;

        const processSseLine = (line: string) => {
          if (!line.startsWith("data: ")) {
            return;
          }

          const rawPayload = line.slice(6).trim();
          if (!rawPayload || rawPayload === "[DONE]") {
            return;
          }

          try {
            const data = JSON.parse(rawPayload);

            if (data.type === "text-delta" && typeof data.delta === "string") {
              assistantResponse += data.delta;
            }

            if (
              data.type === "data-conversationSummary" &&
              typeof data.data === "string"
            ) {
              latestConversationSummary = data.data;
              hasSummaryUpdate = true;
            }
          } catch {
            // Ignore non-JSON data lines.
          }
        };

        try {
          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              if (sseBuffer) {
                for (const line of sseBuffer.split("\n")) {
                  processSseLine(line);
                }
              }

              if (!isClosed) {
                controller.enqueue(
                  encoder.encode(
                    `data: ${JSON.stringify({
                      type: "data-statusMessage",
                      data: "Salvando hist\u00f3rico da conversa...",
                    })}\n\n`
                  )
                );
              }

              if (assistantResponse.trim()) {
                try {
                  await saveMessages({
                    messages: [
                      {
                        chatId: id,
                        id: generateUUID(),
                        role: "assistant",
                        parts: [{ type: "text", text: assistantResponse }],
                        attachments: [],
                        createdAt: new Date(),
                      },
                    ],
                  });
                } catch (dbError) {
                  console.error("[API Route] Error saving assistant message:", dbError);
                }
              }

              if (hasSummaryUpdate) {
                try {
                  await updateChatConversationSummaryById({
                    chatId: id,
                    conversationSummary: latestConversationSummary,
                  });
                } catch (dbError) {
                  console.error("[API Route] Error saving conversation summary:", dbError);
                }
              }

              if (!isClosed) {
                controller.close();
                isClosed = true;
              }
              break;
            }

            const chunk = decoder.decode(value, { stream: true });
            sseBuffer += chunk;

            const lines = sseBuffer.split("\n");
            sseBuffer = lines.pop() ?? "";

            for (const line of lines) {
              processSseLine(line);
            }

            if (!isClosed) {
              controller.enqueue(value);
            }
          }
        } catch (error) {
          console.error("[API Route] Error processing backend stream:", error);
          if (!isClosed) {
            controller.error(error);
            isClosed = true;
          }
        }
      },
    });

    return new Response(interceptedStream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    const vercelId = request.headers.get("x-vercel-id");

    if (error instanceof ChatSDKError) {
      return error.toResponse();
    }

    console.error("Unhandled error in chat API:", error, { vercelId });
    return new ChatSDKError("offline:chat").toResponse();
  }
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return new ChatSDKError("bad_request:api").toResponse();
  }

  const session = await auth();

  if (!session?.user) {
    return new ChatSDKError("unauthorized:chat").toResponse();
  }

  const chat = await getChatById({ id });

  if (chat?.userId !== session.user.id) {
    return new ChatSDKError("forbidden:chat").toResponse();
  }

  const deletedChat = await deleteChatById({ id });

  return Response.json(deletedChat, { status: 200 });
}
