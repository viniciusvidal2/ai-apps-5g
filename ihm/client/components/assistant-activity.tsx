"use client";

import { AnimatePresence, motion } from "framer-motion";
import { getAssistantActivityLabel } from "@/lib/assistant-activity";
import { SparklesIcon } from "./icons";

export function AssistantActivity({
  statusMessage,
}: {
  statusMessage?: string;
}) {
  const activityLabel = getAssistantActivityLabel(statusMessage);

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
          <div className="flex w-fit items-center gap-2 rounded-full border border-border/60 bg-muted/35 px-3 py-2 text-muted-foreground text-sm">
            <span className="relative flex size-2.5 shrink-0">
              <motion.span
                animate={{ opacity: [0.15, 0.45, 0.15], scale: [0.85, 1.7, 0.85] }}
                aria-hidden="true"
                className="absolute inset-0 rounded-full bg-current"
                transition={{
                  duration: 1.4,
                  ease: "easeInOut",
                  repeat: Number.POSITIVE_INFINITY,
                }}
              />
              <motion.span
                animate={{ opacity: [0.55, 1, 0.55] }}
                aria-hidden="true"
                className="relative size-2.5 rounded-full bg-current"
                transition={{
                  duration: 1.4,
                  ease: "easeInOut",
                  repeat: Number.POSITIVE_INFINITY,
                }}
              />
            </span>

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
        </div>
      </div>
    </motion.div>
  );
}
