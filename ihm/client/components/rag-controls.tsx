"use client";

import { memo } from "react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export interface RAGParams {
  use_history: boolean;
  search_db: boolean;
  search_urls: boolean;
  n_chunks?: number;
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
  const handleChange = (key: keyof RAGParams, value: boolean) => {
    onParamsChange({
      ...params,
      [key]: value,
    });
  };

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-3 border-t border-border px-2 py-2 text-xs",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <Switch
          id="use-history"
          checked={params.use_history}
          onCheckedChange={(checked) => handleChange("use_history", checked)}
        />
        <Label
          htmlFor="use-history"
          className="cursor-pointer text-xs font-normal text-muted-foreground"
        >
          Histórico
        </Label>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="search-db"
          checked={params.search_db}
          onCheckedChange={(checked) => handleChange("search_db", checked)}
        />
        <Label
          htmlFor="search-db"
          className="cursor-pointer text-xs font-normal text-muted-foreground"
        >
          Buscar PDFs
        </Label>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="search-urls"
          checked={params.search_urls}
          onCheckedChange={(checked) => handleChange("search_urls", checked)}
        />
        <Label
          htmlFor="search-urls"
          className="cursor-pointer text-xs font-normal text-muted-foreground"
        >
          Buscar URLs
        </Label>
      </div>
    </div>
  );
}

export const RAGControls = memo(PureRAGControls);

