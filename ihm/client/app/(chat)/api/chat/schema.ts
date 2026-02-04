import { z } from "zod";

const textPartSchema = z.object({
  type: z.enum(["text"]),
  text: z.string().min(1).max(2000),
});

const filePartSchema = z.object({
  type: z.enum(["file"]),
  mediaType: z.enum(["image/jpeg", "image/png"]),
  name: z.string().min(1).max(100),
  url: z.string().url(),
});

const partSchema = z.union([textPartSchema, filePartSchema]);

const ragParamsSchema = z.object({
  n_chunks: z.number().optional(),
  inference_model_name: z.string().optional(),
  vectorstore_name: z.enum(["documents", "none"]).optional(),
}).optional();

export const postRequestBodySchema = z.object({
  id: z.string().uuid(),
  message: z.object({
    id: z.string().uuid(),
    role: z.enum(["user"]),
    parts: z.array(partSchema),
  }),
  selectedChatModel: z.enum(["search-mode-default", "search-mode-wide"]),
  selectedVisibilityType: z.enum(["public", "private"]),
  ragParams: ragParamsSchema,
  sessionId: z.string().optional(),
});

export type PostRequestBody = z.infer<typeof postRequestBodySchema>;
