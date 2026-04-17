"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChevronDownIcon, InfoIcon } from "lucide-react";
import {
  getAssistantActivityLabel,
  isFinalizationPhaseStatus,
} from "@/lib/assistant-activity";
import { Shimmer } from "./elements/shimmer";
import {
  Task,
  TaskContent,
  TaskItem,
  TaskTrigger,
} from "./elements/task";
import { SparklesIcon } from "./icons";

export function AssistantActivity({
  statusMessage,
}: {
  statusMessage?: string;
}) {
  const activityLabel = getAssistantActivityLabel(statusMessage);
  if (!activityLabel) {
    return null;
  }

  const showPersistenceHint = isFinalizationPhaseStatus(activityLabel);

  return (
    <motion.div
      animate={{ opacity: 1 }}
      className="group/message w-full"
      data-role="assistant"
      data-testid="message-assistant-loading"
      initial={{ opacity: 0 }}
    >
      <div className="flex items-start justify-start gap-3">
        <div className="-mt-1 flex size-8 shrink-0 items-center justify-center rounded-full bg-background ring-1 ring-border">
          <SparklesIcon size={14} />
        </div>

        <div className="flex w-full flex-col gap-2 md:gap-4">
          <div className="flex w-fit max-w-full flex-col gap-2">
            <div className="flex w-fit items-center gap-2 rounded-full border border-border/60 bg-muted/35 px-3 py-2 text-muted-foreground text-sm">
              <Shimmer
                aria-hidden="true"
                className="size-2.5 shrink-0 rounded-full"
                data-testid="assistant-activity-shimmer"
                key={`${activityLabel}-shimmer`}
              />

              <div className="min-h-[20px] min-w-0">
                <AnimatePresence initial={false} mode="wait">
                  <motion.span
                    animate={{ opacity: [0.65, 1, 0.65], y: 0 }}
                    className="block whitespace-pre-wrap"
                    data-testid="assistant-activity-text"
                    exit={{ opacity: 0, y: -4 }}
                    initial={{ opacity: 0, y: 4 }}
                    key={activityLabel}
                    transition={{
                      opacity: {
                        duration: 1.8,
                        ease: "easeInOut",
                        repeat: Number.POSITIVE_INFINITY,
                      },
                      y: { duration: 0.18, ease: "easeOut" },
                    }}
                  >
                    {activityLabel}
                  </motion.span>
                </AnimatePresence>
              </div>
            </div>

            {showPersistenceHint && (
              <Task
                className="max-w-lg rounded-lg border border-border/50 bg-muted/20 px-3 py-2"
                data-testid="assistant-activity-persistence-hint"
                defaultOpen
              >
                <TaskTrigger title="">
                  <div className="flex cursor-pointer items-center gap-2 text-muted-foreground text-xs transition-colors hover:text-foreground [&[data-state=open]>svg:last-child]:rotate-180">
                    <InfoIcon aria-hidden className="size-3.5 shrink-0" />
                    <p className="text-left font-medium">
                      Por que o chat ainda está bloqueado?
                    </p>
                    <ChevronDownIcon className="size-3.5 shrink-0 transition-transform" />
                  </div>
                </TaskTrigger>
                <TaskContent>
                  <TaskItem>
                    A resposta já foi gerada; o servidor está gravando a mensagem
                    e atualizando o resumo da conversa no banco de dados.
                  </TaskItem>
                  <TaskItem>
                    O envio fica desativado até terminar essa etapa para evitar
                    mensagens fora de ordem ou resumo inconsistente.
                  </TaskItem>
                </TaskContent>
              </Task>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
