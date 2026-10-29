import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AgendaDialog } from "@/components/agenda-dialog";
import { api, type Meeting } from "@/lib/api";
import * as agendaApi from "@/lib/agenda";
import { renderWithQuery } from "./utils";

const meeting: Meeting = {
  id: "meeting-1",
  title: "Pricing sync",
  start_at: "2026-10-19T10:00:00+03:00",
  end_at: "2026-10-19T10:45:00+03:00",
  location: null,
  purpose: null,
  created_at: "",
  updated_at: "",
};
const suggestion: agendaApi.Suggestion = {
  agenda: {
    ...agendaApi.emptyAgenda(),
    title: "Pricing",
    language: "uk",
    items: [{ topic: "Pro plan", owner: "Олена", minutes: 15 }],
  },
  model: "test-model",
  prompt_version: "agenda-v1",
};

describe("Paste, review, save", () => {
  it("marks suggestions, clears a touched badge, and saves the original suggestion separately", async () => {
    vi.spyOn(agendaApi, "parseAgenda").mockResolvedValue(suggestion);
    const save = vi.spyOn(api, "saveAgenda").mockResolvedValue(meeting);
    const close = vi.fn();
    renderWithQuery(<AgendaDialog meeting={meeting} onClose={close} />);
    await userEvent.type(
      screen.getByLabelText("Paste an agenda"),
      "Pricing sync with Олена",
    );
    await userEvent.click(screen.getByRole("button", { name: "Parse" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Agenda title")).toHaveValue("Pricing"),
    );
    const title = screen.getByLabelText("Agenda title");
    expect(title.closest("label")).toHaveTextContent("suggested");
    await userEvent.clear(title);
    await userEvent.type(title, "Reviewed pricing");
    expect(title.closest("label")).not.toHaveTextContent("suggested");
    expect(save).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Save agenda" }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        meeting.id,
        { ...suggestion.agenda, title: "Reviewed pricing" },
        suggestion,
      ),
    );
    expect(close).toHaveBeenCalled();
  });
  it("aborts a pending parse and ignores its late result", async () => {
    let resolve!: (value: agendaApi.Suggestion) => void;
    const parse = vi.spyOn(agendaApi, "parseAgenda").mockImplementation(
      () =>
        new Promise((r) => {
          resolve = r;
        }),
    );
    renderWithQuery(<AgendaDialog meeting={meeting} onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText("Paste an agenda"), "Pricing");
    await userEvent.click(screen.getByRole("button", { name: "Parse" }));
    expect(screen.getByRole("status")).toHaveTextContent("Reading");
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(parse.mock.calls[0][1].aborted).toBe(true);
    resolve(suggestion);
    await waitFor(() =>
      expect(screen.getByLabelText("Agenda title")).toHaveValue(""),
    );
  });
  it("keeps manual entry usable when parsing fails", async () => {
    vi.spyOn(agendaApi, "parseAgenda").mockRejectedValue(
      new Error("The AI service is busy."),
    );
    renderWithQuery(<AgendaDialog meeting={meeting} onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText("Paste an agenda"), "Pricing");
    await userEvent.click(screen.getByRole("button", { name: "Parse" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("busy");
    await userEvent.click(screen.getByRole("button", { name: "Add topic" }));
    await userEvent.type(
      screen.getByLabelText("Topic 1", { exact: true }),
      "Manual topic",
    );
    expect(screen.getByLabelText("Topic 1", { exact: true })).toHaveValue(
      "Manual topic",
    );
  });
});
