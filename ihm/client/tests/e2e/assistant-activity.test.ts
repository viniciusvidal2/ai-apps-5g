import { expect, test } from "../fixtures";
import { ChatPage } from "../pages/chat";

const MOCK_CHAT_STREAM = [
  'data: {"type":"data-statusMessage","data":"Recuperando documentos relevantes da base de dados."}',
  'data: {"type":"start-step"}',
  'data: {"type":"text-start","id":"assistant-activity-test"}',
  'data: {"type":"text-delta","id":"assistant-activity-test","delta":"Resposta "}',
  'data: {"type":"text-delta","id":"assistant-activity-test","delta":"final "}',
  'data: {"type":"text-end","id":"assistant-activity-test"}',
  'data: {"type":"finish-step"}',
  'data: {"type":"finish"}',
  "data: [DONE]",
].join("\n\n");

test.describe("assistant activity", () => {
  let chatPage: ChatPage;

  test.beforeEach(async ({ page }) => {
    chatPage = new ChatPage(page);
    await chatPage.createNewChat();
  });

  test("shows a temporary assistant activity indicator while the response is pending", async ({
    page,
  }) => {
    await page.route("**/api/chat", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 700));

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

    await chatPage.sendUserMessage("Quero ver o status da inferência");

    await expect(page.getByTestId("message-assistant-loading")).toBeVisible();
    await expect(page.getByTestId("assistant-activity-text")).toContainText(
      "Pensando..."
    );

    await chatPage.isGenerationComplete();

    await expect(
      page.getByTestId("message-assistant-loading")
    ).not.toBeVisible();

    const assistantMessage = await chatPage.getRecentAssistantMessage();
    expect(assistantMessage?.content).toContain("Resposta final");
  });
});
