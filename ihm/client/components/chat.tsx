"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { useSWRConfig } from "swr";
import { unstable_serialize } from "swr/infinite";
import { ChatHeader } from "@/components/chat-header";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useArtifactSelector } from "@/hooks/use-artifact";
import { useAutoResume } from "@/hooks/use-auto-resume";
import { useChatVisibility } from "@/hooks/use-chat-visibility";
import { chatModels } from "@/lib/ai/models";
import { ChatSDKError } from "@/lib/errors";
import { useSessionId } from "@/lib/session-context";
import type { Attachment, ChatMessage } from "@/lib/types";
import type { AppUsage } from "@/lib/usage";
import { fetchWithErrorHandlers, generateUUID } from "@/lib/utils";
import { Artifact } from "./artifact";
import { useDataStream } from "./data-stream-provider";
import { Messages } from "./messages";
import { MultimodalInput } from "./multimodal-input";
import {
  NONE_COLLECTION_OPTION,
  type RAGOption,
  type RAGOptionLoadStatus,
  type RAGParams,
} from "./rag-controls";
import { getChatHistoryPaginationKey } from "./sidebar-history";
import { toast } from "./toast";
import type { VisibilityType } from "./visibility-selector";

type RAGOptionState = {
  inferenceModels: RAGOption[];
  inferenceModelsStatus: RAGOptionLoadStatus;
  collections: RAGOption[];
  collectionsStatus: RAGOptionLoadStatus;
};

const COLLECTIONS_POLL_INTERVAL_MS = Number(
  process.env.NEXT_PUBLIC_RAG_COLLECTIONS_POLL_INTERVAL_MS ?? "1000"
);
const COLLECTIONS_MAX_ATTEMPTS = Number(
  process.env.NEXT_PUBLIC_RAG_COLLECTIONS_MAX_ATTEMPTS ?? "30"
);

function createInitialRAGOptionState(): RAGOptionState {
  return {
    inferenceModels: [],
    inferenceModelsStatus: "loading",
    collections: [NONE_COLLECTION_OPTION],
    collectionsStatus: "loading",
  };
}

function normalizeRAGOptions(values: unknown): RAGOption[] {
  if (!Array.isArray(values)) {
    return [];
  }

  const seen = new Set<string>();

  return values.flatMap((value) => {
    if (typeof value !== "string") {
      return [];
    }

    const normalizedValue = value.trim();
    if (!normalizedValue || seen.has(normalizedValue)) {
      return [];
    }

    seen.add(normalizedValue);
    return [{ id: normalizedValue, name: normalizedValue }];
  });
}

function getValidatedOptionId(
  currentValue: string | undefined,
  options: RAGOption[],
  fallbackValue: string | undefined
): string | undefined {
  if (currentValue && options.some((option) => option.id === currentValue)) {
    return currentValue;
  }

  return fallbackValue;
}

function getEffectiveRAGParams(
  params: RAGParams,
  optionState: RAGOptionState
): RAGParams {
  const inference_model_name =
    optionState.inferenceModelsStatus === "ready"
      ? getValidatedOptionId(
          params.inference_model_name,
          optionState.inferenceModels,
          optionState.inferenceModels[0]?.id
        )
      : undefined;

  const collection_name =
    optionState.collectionsStatus === "ready"
      ? getValidatedOptionId(
          params.collection_name,
          optionState.collections,
          NONE_COLLECTION_OPTION.id
        ) ?? NONE_COLLECTION_OPTION.id
      : NONE_COLLECTION_OPTION.id;

  return {
    ...params,
    inference_model_name,
    collection_name,
  };
}

export function Chat({
  id,
  initialMessages,
  initialChatModel,
  initialVisibilityType,
  isReadonly,
  autoResume,
  initialLastContext,
}: {
  id: string;
  initialMessages: ChatMessage[];
  initialChatModel: string;
  initialVisibilityType: VisibilityType;
  isReadonly: boolean;
  autoResume: boolean;
  initialLastContext?: AppUsage;
}) {
  const { visibilityType } = useChatVisibility({
    chatId: id,
    initialVisibilityType,
  });

  const { mutate } = useSWRConfig();
  const { setDataStream } = useDataStream();
  const sessionId = useSessionId();

  const [input, setInput] = useState<string>("");
  const [usage, setUsage] = useState<AppUsage | undefined>(initialLastContext);
  const [backendStatusMessage, setBackendStatusMessage] = useState<string>("");
  const [showCreditCardAlert, setShowCreditCardAlert] = useState(false);
  const [currentModelId, setCurrentModelId] = useState(initialChatModel);

  // Helper function to get n_chunks from model
  const getNChunksFromModel = (modelId: string): number => {
    const model = chatModels.find((m) => m.id === modelId);
    return model?.n_chunks ?? 10;
  };

  // RAG parameters with localStorage persistence
  const [ragParams, setRAGParams] = useState<RAGParams>(() => {
    const defaultParams = {
      n_chunks: getNChunksFromModel(initialChatModel),
      collection_name: "none",
    };

    if (typeof window === "undefined") {
      return defaultParams;
    }

    const stored = localStorage.getItem("rag-params");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        return {
          n_chunks: getNChunksFromModel(initialChatModel),
          inference_model_name:
            typeof parsed.inference_model_name === "string"
              ? parsed.inference_model_name
              : undefined,
          collection_name:
            typeof parsed.collection_name === "string"
              ? parsed.collection_name
              : typeof parsed.vectorstore_name === "string"
                ? parsed.vectorstore_name
                : defaultParams.collection_name,
        };
      } catch {
        return defaultParams;
      }
    }
    return defaultParams;
  });

  const [ragOptionState, setRAGOptionState] = useState<RAGOptionState>(
    createInitialRAGOptionState
  );

  useEffect(() => {
    if (isReadonly) {
      setRAGOptionState({
        inferenceModels: [],
        inferenceModelsStatus: "ready",
        collections: [NONE_COLLECTION_OPTION],
        collectionsStatus: "ready",
      });
      return;
    }

    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8003";
    const abortController = new AbortController();

    setRAGOptionState(createInitialRAGOptionState());

    const loadInferenceModels = async () => {
      try {
        const response = await fetch(`${backendUrl}/ai_assistant/available_models`, {
          signal: abortController.signal,
        });

        if (!response.ok) {
          throw new Error(
            `Failed to load RAG models (${response.status})`
          );
        }

        const data = await response.json();
        const inferenceModels = normalizeRAGOptions(data.available_models);

        setRAGOptionState((current) => ({
          ...current,
          inferenceModels,
          inferenceModelsStatus: "ready",
        }));
      } catch (error) {
        if (abortController.signal.aborted) {
          return;
        }

        console.error("Error loading RAG models:", error);
        setRAGOptionState((current) => ({
          ...current,
          inferenceModels: [],
          inferenceModelsStatus: "unavailable",
        }));
      }
    };

    const loadCollections = async () => {
      let lastError: unknown;

      for (
        let attempt = 1;
        attempt <= COLLECTIONS_MAX_ATTEMPTS;
        attempt += 1
      ) {
        if (abortController.signal.aborted) {
          return;
        }

        try {
          const response = await fetch(`${backendUrl}/ai_assistant/collections`, {
            signal: abortController.signal,
          });

          if (!response.ok) {
            throw new Error(
              `Failed to load RAG collections (${response.status})`
            );
          }

          const data = await response.json();
          const isReady = data.ready !== false;

          if (isReady) {
            const collections = normalizeRAGOptions(
              data.collection_names
            ).filter((option) => option.id !== NONE_COLLECTION_OPTION.id);

            setRAGOptionState((current) => ({
              ...current,
              collections: [NONE_COLLECTION_OPTION, ...collections],
              collectionsStatus: "ready",
            }));
            return;
          }
        } catch (error) {
          if (abortController.signal.aborted) {
            return;
          }

          lastError = error;
        }

        if (attempt < COLLECTIONS_MAX_ATTEMPTS) {
          await new Promise((resolve) =>
            window.setTimeout(resolve, COLLECTIONS_POLL_INTERVAL_MS)
          );
        }
      }

      if (abortController.signal.aborted) {
        return;
      }

      console.error(
        "RAG collections remained unavailable after polling:",
        lastError
      );
      setRAGOptionState((current) => ({
        ...current,
        collections: [NONE_COLLECTION_OPTION],
        collectionsStatus: "unavailable",
      }));
    };

    void loadInferenceModels();
    void loadCollections();

    return () => {
      abortController.abort();
    };
  }, [isReadonly]);

  useEffect(() => {
    if (ragOptionState.inferenceModelsStatus !== "ready") {
      return;
    }

    const validModelIds = new Set(
      ragOptionState.inferenceModels.map((model) => model.id)
    );

    setRAGParams((current) => {
      const nextInferenceModel =
        current.inference_model_name &&
        validModelIds.has(current.inference_model_name)
          ? current.inference_model_name
          : ragOptionState.inferenceModels[0]?.id;

      if (current.inference_model_name === nextInferenceModel) {
        return current;
      }

      return {
        ...current,
        inference_model_name: nextInferenceModel,
      };
    });
  }, [ragOptionState.inferenceModels, ragOptionState.inferenceModelsStatus]);

  useEffect(() => {
    if (ragOptionState.collectionsStatus !== "ready") {
      return;
    }

    const validCollectionIds = new Set(
      ragOptionState.collections.map((collection) => collection.id)
    );

    setRAGParams((current) => {
      const nextCollection =
        current.collection_name && validCollectionIds.has(current.collection_name)
          ? current.collection_name
          : NONE_COLLECTION_OPTION.id;

      if (current.collection_name === nextCollection) {
        return current;
      }

      return {
        ...current,
        collection_name: nextCollection,
      };
    });
  }, [ragOptionState.collections, ragOptionState.collectionsStatus]);

  // Sync n_chunks when model changes
  useEffect(() => {
    const newNChunks = getNChunksFromModel(currentModelId);
    if (ragParams.n_chunks !== newNChunks) {
      setRAGParams((prev) => ({ ...prev, n_chunks: newNChunks }));
    }
  }, [currentModelId, ragParams.n_chunks]);

  useEffect(() => {
    localStorage.setItem("rag-params", JSON.stringify(ragParams));
  }, [ragParams]);

  const currentModelIdRef = useRef(currentModelId);
  const ragParamsRef = useRef(getEffectiveRAGParams(ragParams, ragOptionState));

  useEffect(() => {
    currentModelIdRef.current = currentModelId;
  }, [currentModelId]);

  useEffect(() => {
    ragParamsRef.current = getEffectiveRAGParams(ragParams, ragOptionState);
  }, [ragOptionState, ragParams]);

  const {
    messages,
    setMessages,
    sendMessage,
    status,
    stop,
    regenerate,
    resumeStream,
  } = useChat<ChatMessage>({
    id,
    messages: initialMessages,
    experimental_throttle: 50,
    generateId: generateUUID,
    transport: new DefaultChatTransport({
      api: "/api/chat",
      fetch: fetchWithErrorHandlers,
      prepareSendMessagesRequest(request) {
        return {
          body: {
            id: request.id,
            message: request.messages.at(-1),
            selectedChatModel: currentModelIdRef.current,
            selectedVisibilityType: visibilityType,
            ragParams: ragParamsRef.current,
            sessionId: sessionId,
            ...request.body,
          },
        };
      },
    }),
    onData: (dataPart) => {
      setDataStream((ds) => (ds ? [...ds, dataPart] : []));
      if (dataPart.type === "data-usage") {
        setUsage(dataPart.data);
      }
      if (dataPart.type === "data-statusMessage") {
        // flushSync forces an immediate React render so the status label
        // is visible as soon as it arrives, even when many stream events
        // are processed in the same microtask batch.
        flushSync(() => {
          setBackendStatusMessage(dataPart.data as string);
        });
      }
    },
    onFinish: () => {
      mutate(unstable_serialize(getChatHistoryPaginationKey));
    },
    onError: (error) => {
      setBackendStatusMessage("");
      if (error instanceof ChatSDKError) {
        // Check if it's a credit card error
        if (
          error.message?.includes("AI Gateway requires a valid credit card")
        ) {
          setShowCreditCardAlert(true);
        } else {
          toast({
            type: "error",
            description: error.message,
          });
        }
      }
    },
  });

  const searchParams = useSearchParams();
  const query = searchParams.get("query");

  const [hasAppendedQuery, setHasAppendedQuery] = useState(false);

  useEffect(() => {
    if (status !== "ready") {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setBackendStatusMessage("");
    }, 800);
    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [status]);

  useEffect(() => {
    if (status !== "submitted" && status !== "streaming") {
      return;
    }

    let isCancelled = false;

    const refreshAssistantStatus = async () => {
      try {
        const response = await fetch("/api/ai-assistant/status", {
          cache: "no-store",
        });
        if (!response.ok) {
          return;
        }
        const data = await response.json();
        const nextStatus =
          typeof data.status === "string" ? data.status.trim() : "";
        if (nextStatus && !isCancelled) {
          setBackendStatusMessage(nextStatus);
        }
      } catch {
        // Keep the latest streamed status when the polling endpoint is unavailable.
      }
    };

    refreshAssistantStatus();
    const intervalId = window.setInterval(refreshAssistantStatus, 1000);

    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
    };
  }, [status]);

  useEffect(() => {
    if (query && !hasAppendedQuery) {
      sendMessage({
        role: "user" as const,
        parts: [{ type: "text", text: query }],
      });

      setHasAppendedQuery(true);
      window.history.replaceState({}, "", `/chat/${id}`);
    }
  }, [query, sendMessage, hasAppendedQuery, id]);

  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const isArtifactVisible = useArtifactSelector((state) => state.isVisible);

  useAutoResume({
    autoResume,
    initialMessages,
    resumeStream,
    setMessages,
  });

  return (
    <>
      <div className="overscroll-behavior-contain flex h-dvh min-w-0 touch-pan-y flex-col bg-background">
        <ChatHeader
          chatId={id}
          isReadonly={isReadonly}
        />

        <Messages
          isArtifactVisible={isArtifactVisible}
          isReadonly={isReadonly}
          messages={messages}
          regenerate={regenerate}
          selectedModelId={initialChatModel}
          setMessages={setMessages}
          status={status}
          statusMessage={backendStatusMessage}
        />

        <div className="sticky bottom-0 z-1 mx-auto flex w-full max-w-4xl gap-2 border-t-0 bg-background px-2 pb-3 md:px-4 md:pb-4">
          {!isReadonly && (
            <MultimodalInput
              attachments={attachments}
              chatId={id}
              input={input}
              messages={messages}
              onModelChange={setCurrentModelId}
              selectedModelId={currentModelId}
              selectedVisibilityType={visibilityType}
              sendMessage={sendMessage}
              setAttachments={setAttachments}
              setInput={setInput}
              setMessages={setMessages}
              status={status}
              statusMessage={backendStatusMessage}
              stop={stop}
              usage={usage}
              ragParams={ragParams}
              ragCollections={ragOptionState.collections}
              ragCollectionsStatus={ragOptionState.collectionsStatus}
              ragInferenceModels={ragOptionState.inferenceModels}
              ragInferenceModelsStatus={ragOptionState.inferenceModelsStatus}
              onRAGParamsChange={setRAGParams}
            />
          )}
        </div>
      </div>

      <Artifact
        attachments={attachments}
        chatId={id}
        input={input}
        isReadonly={isReadonly}
        messages={messages}
        regenerate={regenerate}
        selectedModelId={currentModelId}
        selectedVisibilityType={visibilityType}
        sendMessage={sendMessage}
        setAttachments={setAttachments}
        setInput={setInput}
        setMessages={setMessages}
        status={status}
        statusMessage={backendStatusMessage}
        stop={stop}
      />

      <AlertDialog
        onOpenChange={setShowCreditCardAlert}
        open={showCreditCardAlert}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Ativar AI Gateway</AlertDialogTitle>
            <AlertDialogDescription>
              Esta aplicação requer que{" "}
              {process.env.NODE_ENV === "production" ? "o proprietário" : "você"} ative
              o Vercel AI Gateway.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                window.open(
                  "https://vercel.com/d?to=%2F%5Bteam%5D%2F%7E%2Fai%3Fmodal%3Dadd-credit-card",
                  "_blank"
                );
                window.location.href = "/";
              }}
            >
              Ativar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
