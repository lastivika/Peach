import { z } from "zod";
import { getIdToken } from "@/lib/auth";

export const agendaSchema = z.object({
  title: z.string().min(1).max(200).nullable(),
  starts_at: z.iso.datetime({ offset: true }).nullable(),
  duration_minutes: z.number().int().min(1).max(600).nullable(),
  items: z
    .array(
      z.object({
        topic: z.string().trim().min(1).max(1000),
        owner: z.string().max(320).nullable(),
        minutes: z.number().int().min(1).max(480).nullable(),
      }),
    )
    .max(50),
  action_items: z
    .array(
      z.object({
        task: z.string().trim().min(1).max(2000),
        owner: z.string().max(320).nullable(),
        due: z.iso.date().nullable(),
      }),
    )
    .max(50),
  language: z.string().regex(/^[a-z]{2,3}(-[A-Za-z]+)?$/),
});
export const suggestionSchema = z.object({
  agenda: agendaSchema,
  model: z.string(),
  prompt_version: z.string(),
});
export type Agenda = z.infer<typeof agendaSchema>;
export type Suggestion = z.infer<typeof suggestionSchema>;
export const emptyAgenda = (): Agenda => ({
  title: null,
  starts_at: null,
  duration_minutes: null,
  items: [],
  action_items: [],
  language: "en",
});

export async function parseAgenda(
  text: string,
  signal: AbortSignal,
): Promise<Suggestion> {
  if (text.length > 10000)
    throw new Error("Text is too long. Maximum: 10,000 characters.");
  const url = process.env.NEXT_PUBLIC_AGENDA_PARSER_URL;
  if (!url)
    throw new Error(
      "AI parsing is unavailable. You can enter the agenda manually.",
    );
  const token = await getIdToken();
  if (!token) throw new Error("Sign in again to parse an agenda.");
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      signal,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        text,
        today,
        tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
      }),
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error(
      "Network error. Check your connection or enter the agenda manually.",
    );
  }
  if (!response.ok) {
    const errors: Record<number, string> = {
      401: "Sign in again to parse an agenda.",
      413: "Text is too long. Maximum: 10,000 characters.",
      422: "No valid agenda found. Try clearer text or enter it manually.",
      429: "The AI service is busy. Try again shortly or enter it manually.",
    };
    throw new Error(
      errors[response.status] ??
        "AI parsing is unavailable. You can enter the agenda manually.",
    );
  }
  return suggestionSchema.parse(await response.json());
}
