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

// Available inference models
export const INFERENCE_MODELS = [
  { id: "gemma3:4b", name: "Gemma3 4B" },
  { id: "gemma3:12b", name: "Gemma3 12B" },
  { id: "gemma3:27b", name: "Gemma3 27B" },
  { id: "qwen3-embedding:0.6b", name: "Qwen3 Embedding 0.6B" },
] as const;

// Available collection options
export const COLLECTION_OPTIONS = [
  { id: "documents", name: "Documentos" },
  { id: "none", name: "Nenhum" },
] as const;

export interface RAGParams {
  n_chunks?: number;
  inference_model_name: string;
  collection_name: string;
}

interface RAGControlsProps {
  params: RAGParams;
  onParamsChange: (params: RAGParams) => void;
  className?: string;
}

function PureRAGControls({
  params,
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
          value={params.inference_model_name}
          onValueChange={handleModelChange}
        >
          <SelectTrigger id="inference-model" className="h-7 w-[140px] text-xs">
            <SelectValue placeholder="Selecione" />
          </SelectTrigger>
          <SelectContent>
            {INFERENCE_MODELS.map((model) => (
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
          value={params.collection_name}
          onValueChange={handleCollectionChange}
        >
          <SelectTrigger id="collection-name" className="h-7 w-[120px] text-xs">
            <SelectValue placeholder="Selecione" />
          </SelectTrigger>
          <SelectContent>
            {COLLECTION_OPTIONS.map((option) => (
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
