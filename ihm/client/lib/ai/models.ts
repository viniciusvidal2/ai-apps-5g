export const DEFAULT_CHAT_MODEL: string = "search-mode-default";

export type ChatModel = {
  id: string;
  name: string;
  description: string;
  n_chunks: number;
};

export const chatModels: ChatModel[] = [
  {
    id: "search-mode-default",
    name: "Padrão",
    description: "Busca padrão com 3 chunks (mais rápido)",
    n_chunks: 3,
  },
  {
    id: "search-mode-wide",
    name: "Busca ampla",
    description: "Busca ampla com 10 chunks (mais completo)",
    n_chunks: 10,
  },
];
