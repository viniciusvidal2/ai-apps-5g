import type { NextRequest } from "next/server";
import { auth } from "@/app/(auth)/auth";
import { getChatsByUserId } from "@/lib/db/queries";
import { ChatSDKError } from "@/lib/errors";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;

  const limit = Number.parseInt(searchParams.get("limit") || "10", 10);
  const startingAfter = searchParams.get("starting_after");
  const endingBefore = searchParams.get("ending_before");

  if (startingAfter && endingBefore) {
    return new ChatSDKError(
      "bad_request:api",
      "Only one of starting_after or ending_before can be provided."
    ).toResponse();
  }

  const session = await auth();

  // TEMPORARY FIX: Always use fixed guest user
  const fixedGuestUser = {
    id: "00000000-0000-0000-0000-000000000001",
    email: "guest-fixed@temp.com",
    type: "guest"
  };

  if (!session?.user) {
    console.log("[History API] No session found, using fixed guest user");
  } else {
    console.log(`[History API] Session found: ${session.user.id}, but using fixed guest user`);
  }

  const chats = await getChatsByUserId({
    id: fixedGuestUser.id,
    limit,
    startingAfter,
    endingBefore,
  });

  return Response.json(chats);
}
