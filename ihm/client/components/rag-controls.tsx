"use client";

import { memo } from "react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface RAGOption {
  id: string;
  name: string;
}

export const NONE_COLLECTION_OPTION: RAGOption = {
  id: "none",
  name: "Nenhum",
};

export interface RAGParams {
  n_chunks?: number;
  inference_model_name?: string;
  collection_name: string;
}

export type RAGOptionLoadStatus = "loading" | "ready" | "unavailable";

interface RAGControlsProps {
  params: RAGParams;
  inferenceModels: RAGOption[];
  collections: RAGOption[];
  inferenceModelsStatus: RAGOptionLoadStatus;
  collectionsStatus: RAGOptionLoadStatus;
  onParamsChange: (params: RAGParams) => void;
  className?: string;
}

function PureRAGControls({
  params,
  inferenceModels,
  collections,
  inferenceModelsStatus,
  collectionsStatus,
  onParamsChange,
  className,
}: RAGControlsProps) {
  const handleModelChange = (value: string) => {
    onParamsChange({
      ...params,
      inference_model_name: value,
    });
  };

  const handleCollectionChange = (value: string) => {
    onParamsChange({
      ...params,
      collection_name: value,
    });
  };

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-4 border-t border-border px-2 py-2 text-xs",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <Label
          htmlFor="inference-model"
          className="text-xs font-normal text-muted-foreground whitespace-nowrap"
        >
          Modelo:
        </Label>
        <Select
          disabled={
            inferenceModelsStatus !== "ready" || inferenceModels.length === 0
          }
          value={
            inferenceModelsStatus === "ready"
              ? params.inference_model_name
              : undefined
          }
          onValueChange={handleModelChange}
        >
          <SelectTrigger
            id="inference-model"
            className="h-7 w-[140px] text-xs"
            data-testid="rag-model-trigger"
          >
            <SelectValue
              placeholder={
                inferenceModelsStatus === "loading"
                  ? "Carregando..."
                  : inferenceModels.length === 0
                    ? "Indisponivel"
                    : "Selecione"
              }
            />
          </SelectTrigger>
          <SelectContent>
            {inferenceModels.map((model) => (
              <SelectItem key={model.id} value={model.id} className="text-xs">
                {model.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-2">
        <Label
          htmlFor="collection-name"
          className="text-xs font-normal text-muted-foreground whitespace-nowrap"
        >
          Collection:
        </Label>
        <Select
          disabled={collectionsStatus !== "ready"}
          value={
            collectionsStatus === "ready" ? params.collection_name : undefined
          }
          onValueChange={handleCollectionChange}
        >
          <SelectTrigger
            id="collection-name"
            className="h-7 w-[120px] text-xs"
            data-testid="rag-collection-trigger"
          >
            <SelectValue
              placeholder={
                collectionsStatus === "loading"
                  ? "Carregando..."
                  : collectionsStatus === "unavailable"
                    ? "Indisponivel"
                    : "Selecione"
              }
            />
          </SelectTrigger>
          <SelectContent>
            {collections.map((option) => (
              <SelectItem key={option.id} value={option.id} className="text-xs">
                {option.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}

export const RAGControls = memo(PureRAGControls);
