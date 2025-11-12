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
    description: "Respostas rápidas e diretas",
    n_chunks: 3,
  },
  {
    id: "search-mode-wide",
    name: "Busca ampla",
    description: "Análise mais detalhada e abrangente",
    n_chunks: 10,
  },
];
