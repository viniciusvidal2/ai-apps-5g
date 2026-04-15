import type { Page } from "@playwright/test";
import { expect, test } from "../fixtures";
import { ChatPage } from "../pages/chat";

const MOCK_CHAT_STREAM = [
  'data: {"type":"data-statusMessage","data":"Consulta enviada com fallback de collection."}',
  'data: {"type":"start-step"}',
  'data: {"type":"text-start","id":"rag-controls-test"}',
  'data: {"type":"text-delta","id":"rag-controls-test","delta":"Resposta "}',
  'data: {"type":"text-delta","id":"rag-controls-test","delta":"final"}',
  'data: {"type":"text-end","id":"rag-controls-test"}',
  'data: {"type":"finish-step"}',
  'data: {"type":"finish"}',
  "data: [DONE]",
].join("\n\n");

async function accelerateCollectionPolling(page: Page) {
  await page.addInitScript(() => {
    const originalSetTimeout = window.setTimeout.bind(window);

    window.setTimeout = ((handler: TimerHandler, timeout?: number, ...args: unknown[]) => {
      const nextTimeout = timeout === 1000 ? 10 : timeout;
      return originalSetTimeout(handler, nextTimeout, ...(args as []));
    }) as typeof window.setTimeout;
  });
}

async function mockServiceLifecycleRoutes(page: Page) {
  await page.route("**/turn_on_services", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        message: "services ready",
        active_sessions_count: 1,
      }),
    });
  });

  await page.route("**/turn_off_services", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        message: "services stopped",
        active_sessions_count: 0,
      }),
    });
  });
}

test.describe("rag controls", () => {
  test("keeps polling collections until they become ready in the same tab", async ({
    page,
  }) => {
    const chatPage = new ChatPage(page);
    let collectionsRequestCount = 0;

    await accelerateCollectionPolling(page);
    await mockServiceLifecycleRoutes(page);

    await page.route("**/ai_assistant/available_models", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          available_models: ["gemma4:latest", "gemma3:12b"],
        }),
      });
    });

    await page.route("**/ai_assistant/collections", async (route) => {
      collectionsRequestCount += 1;

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ready: collectionsRequestCount >= 2,
          collection_names: collectionsRequestCount >= 2 ? ["rag-docs"] : [],
        }),
      });
    });

    await chatPage.createNewChat();

    const modelTrigger = page.getByTestId("rag-model-trigger");
    const collectionTrigger = page.getByTestId("rag-collection-trigger");

    await expect(modelTrigger).not.toBeDisabled();
    await expect(collectionTrigger).toBeDisabled();
    await expect(collectionTrigger).toContainText("Carregando...");
    await expect.poll(() => collectionsRequestCount).toBeGreaterThan(1);

    await expect(collectionTrigger).not.toBeDisabled();
    await collectionTrigger.click();
    await expect(page.getByRole("option", { name: "rag-docs" })).toBeVisible();
  });

  test("marks collections unavailable after timeout and sends none in chat payload", async ({
    page,
  }) => {
    const chatPage = new ChatPage(page);
    let collectionsRequestCount = 0;
    let lastChatRequestBody: Record<string, any> | undefined;

    await accelerateCollectionPolling(page);
    await mockServiceLifecycleRoutes(page);

    await page.route("**/ai_assistant/available_models", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          available_models: ["gemma4:latest"],
        }),
      });
    });

    await page.route("**/ai_assistant/collections", async (route) => {
      collectionsRequestCount += 1;

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ready: false,
          collection_names: [],
        }),
      });
    });

    await page.route("**/api/chat", async (route) => {
      lastChatRequestBody = route.request().postDataJSON();

      await route.fulfill({
        status: 200,
        body: MOCK_CHAT_STREAM,
        headers: {
          "Content-Type": "text/event-stream; charset=utf-8",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    });

    await chatPage.createNewChat();

    const collectionTrigger = page.getByTestId("rag-collection-trigger");

    await expect.poll(() => collectionsRequestCount).toBe(30);
    await expect(collectionTrigger).toBeDisabled();
    await expect(collectionTrigger).toContainText("Indisponivel");

    await chatPage.sendUserMessage("Use fallback sem collection.");
    await chatPage.isGenerationComplete();

    expect(lastChatRequestBody?.ragParams?.collection_name).toBe("none");

    const assistantMessage = await chatPage.getRecentAssistantMessage();
    expect(assistantMessage?.content).toContain("Resposta final");
  });
});
