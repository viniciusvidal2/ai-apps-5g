export const dynamic = "force-dynamic";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8003";

  try {
    const response = await fetch(`${backendUrl}/ai_assistant/status`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return Response.json({ status: "" }, { status: response.status });
    }

    const data = await response.json();
    const status = typeof data.status === "string" ? data.status.trim() : "";

    return Response.json(
      { status },
      {
        headers: {
          "Cache-Control": "no-store",
        },
      }
    );
  } catch (error) {
    console.error("[API Route] Error loading AI Assistant status:", error);
    return Response.json({ status: "" }, { status: 503 });
  }
}
