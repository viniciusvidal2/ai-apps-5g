export const DEFAULT_CHAT_MODEL: string = "chat-model";

export type ChatModel = {
  id: string;
  name: string;
  description: string;
};

export const chatModels: ChatModel[] = [
  {
    id: "chat-model",
    name: "gpt-oss:120b",
    description: "Modelo multimodal avançado com capacidades de visão e texto",
  },
];
