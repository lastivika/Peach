import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider } from "next-themes";
import { describe, expect, it } from "vitest";

import { ThemeToggle } from "@/components/theme-toggle";

function renderToggle(defaultTheme: "light" | "dark" = "light") {
  return render(
    <ThemeProvider
      attribute="class"
      defaultTheme={defaultTheme}
      enableSystem={false}
      storageKey="theme"
    >
      <ThemeToggle />
    </ThemeProvider>,
  );
}

describe("ThemeToggle", () => {
  it("switches from light to dark and stores the choice", async () => {
    renderToggle("light");

    await userEvent.click(
      screen.getByRole("button", { name: "Toggle color theme" }),
    );

    await waitFor(() => {
      expect(document.documentElement.classList.contains("dark")).toBe(true);
      expect(localStorage.getItem("theme")).toBe("dark");
    });
  });

  it("switches from dark to light and stores the choice", async () => {
    localStorage.setItem("theme", "dark");
    document.documentElement.classList.add("dark");
    renderToggle("dark");

    await userEvent.click(
      screen.getByRole("button", { name: "Toggle color theme" }),
    );

    await waitFor(() => {
      expect(document.documentElement.classList.contains("dark")).toBe(false);
      expect(localStorage.getItem("theme")).toBe("light");
    });
  });
});
