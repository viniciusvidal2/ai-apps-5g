"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { getAssistantActivityLabel } from "@/lib/assistant-activity";
import { Shimmer } from "./elements/shimmer";
import { SparklesIcon } from "./icons";

export function AssistantActivity({
  statusMessage,
}: {
  statusMessage?: string;
}) {
  const [polledStatusMessage, setPolledStatusMessage] = useState(statusMessage);

  useEffect(() => {
    setPolledStatusMessage(statusMessage);
  }, [statusMessage]);

  useEffect(() => {
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
          setPolledStatusMessage(nextStatus);
        }
      } catch (error) {
        console.warn("[AssistantActivity] status poll failed", error);
        // Keep the latest visible status if the status endpoint is unavailable.
      }
    };

    refreshAssistantStatus();
    const intervalId = window.setInterval(refreshAssistantStatus, 1000);

    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const activityLabel = getAssistantActivityLabel(polledStatusMessage);
  if (!activityLabel) {
    return null;
  }

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

        <div className="max-w-full">
          <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-border/70 bg-background/95 px-3 py-1.5 text-muted-foreground text-sm leading-tight shadow-xs backdrop-blur-sm">
            <Shimmer
              aria-hidden="true"
              className="size-2 shrink-0 rounded-full bg-primary/20 before:via-primary/70"
              data-testid="assistant-activity-shimmer"
              key={`${activityLabel}-shimmer`}
            />

            <AnimatePresence initial={false} mode="wait">
              <motion.span
                animate={{ opacity: [0.75, 1, 0.75] }}
                className="block whitespace-nowrap"
                data-testid="assistant-activity-text"
                exit={{ opacity: 0 }}
                initial={{ opacity: 0 }}
                key={activityLabel}
                transition={{
                  opacity: {
                    duration: 1.8,
                    ease: "easeInOut",
                    repeat: Number.POSITIVE_INFINITY,
                  },
                }}
              >
                {activityLabel}
              </motion.span>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
