import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Calendar } from "@/components/calendar";
import { api } from "@/lib/api";
import { renderWithQuery } from "./utils";

describe("Calendar form dismissal", () => {
  it.each(["Close", "Cancel"])(
    "%s hides the form and New meeting reopens it",
    async (label) => {
      vi.spyOn(api, "listMeetings").mockResolvedValue({
        meetings: [],
        total: 0,
      });
      renderWithQuery(<Calendar />);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      await userEvent.click(
        screen.getByRole("button", { name: "New meeting" }),
      );
      expect(
        screen.getByRole("dialog", { name: "New meeting" }),
      ).toBeInTheDocument();
      await userEvent.type(screen.getByLabelText("Title"), "Discarded draft");
      await userEvent.click(screen.getByRole("button", { name: label }));
      expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
      await userEvent.click(
        screen.getByRole("button", { name: "New meeting" }),
      );
      expect(screen.getByLabelText("Title")).toHaveValue("");
    },
  );
  it("closes and reopens the selected meeting", async () => {
    const now = new Date().toISOString();
    vi.spyOn(api, "listMeetings").mockResolvedValue({
      meetings: [
        {
          id: "meeting-1",
          title: "Team meeting",
          start_at: now,
          end_at: new Date(Date.now() + 3600000).toISOString(),
          location: null,
          purpose: null,
          created_at: now,
          updated_at: now,
        },
      ],
      total: 1,
    });
    renderWithQuery(<Calendar />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(
      screen.getByRole("dialog", { name: "Edit meeting" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveValue("Team meeting");
  });
});
