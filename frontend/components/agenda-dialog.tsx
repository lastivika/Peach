"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { api, type Meeting } from "@/lib/api";
import {
  agendaSchema,
  emptyAgenda,
  parseAgenda,
  type Agenda,
  type Suggestion,
} from "@/lib/agenda";

type Props = { meeting: Meeting; onClose: () => void };

export function AgendaDialog({ meeting, onClose }: Props) {
  const client = useQueryClient();
  const [agenda, setAgenda] = useState<Agenda>(
    () => meeting.agenda ?? emptyAgenda(),
  );
  const [suggestion, setSuggestion] = useState<Suggestion | null>(
    meeting.ai_suggestion ?? null,
  );
  const [suggested, setSuggested] = useState<Set<string>>(new Set());
  const [text, setText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  function touched(key: string) {
    setSuggested((old) => {
      const next = new Set(old);
      next.delete(key);
      return next;
    });
  }
  function removeSuggestedRow(group: "items" | "action_items", index: number) {
    setSuggested(
      (old) =>
        new Set(
          [...old].flatMap((key) => {
            if (!key.startsWith(`${group}.`)) return [key];
            const [, row, field] = key.split(".");
            const n = Number(row);
            return n === index
              ? []
              : [`${group}.${n > index ? n - 1 : n}.${field}`];
          }),
        ),
    );
  }
  function cancelParse() {
    controller.current?.abort();
    controller.current = null;
    setParsing(false);
  }
  async function parse() {
    cancelParse();
    const current = new AbortController();
    controller.current = current;
    setParsing(true);
    setError("");
    try {
      const result = await parseAgenda(text, current.signal);
      if (current.signal.aborted) return;
      setAgenda(structuredClone(result.agenda));
      setSuggestion(result);
      const fields = new Set<string>();
      for (const [key, value] of Object.entries(result.agenda)) {
        if (Array.isArray(value))
          value.forEach((row, i) =>
            Object.entries(row).forEach(([field, v]) => {
              if (v !== null && v !== "") fields.add(`${key}.${i}.${field}`);
            }),
          );
        else if (value !== null && value !== "") fields.add(key);
      }
      setSuggested(fields);
    } catch (err) {
      if (!current.signal.aborted)
        setError(
          err instanceof Error ? err.message : "Could not parse the agenda.",
        );
    } finally {
      if (controller.current === current) {
        controller.current = null;
        setParsing(false);
      }
    }
  }
  async function save() {
    const parsed = agendaSchema.safeParse(agenda);
    if (!parsed.success) {
      setError(
        "Check the fields: topics and tasks need text, dates need an ISO format, and minutes must be positive whole numbers.",
      );
      return;
    }
    setSaving(true);
    setError("");
    try {
      await api.saveAgenda(meeting.id, parsed.data, suggestion);
      await client.invalidateQueries({ queryKey: ["meetings"] });
      toast.success("Agenda saved");
      onClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save the agenda.",
      );
    } finally {
      setSaving(false);
    }
  }
  const badge = (key: string) =>
    suggested.has(key) ? (
      <span className="ml-2 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-normal text-primary">
        suggested
      </span>
    ) : null;
  function field(
    key: string,
    label: string,
    value: string | number | null,
    change: (value: string) => void,
    type = "text",
  ) {
    return (
      <label className="grid gap-1 text-sm" key={key}>
        <span>
          {label}
          {badge(key)}
        </span>
        <Input
          aria-label={label}
          type={type}
          value={value ?? ""}
          onChange={(e) => {
            touched(key);
            change(e.target.value);
          }}
        />
      </label>
    );
  }
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !saving) {
          cancelParse();
          onClose();
        }
      }}
    >
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Agenda · {meeting.title}</DialogTitle>
          <DialogDescription>
            Paste notes to get a suggestion, review every field, then save. You
            can also fill everything in manually.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-2 rounded-lg border bg-muted/30 p-3">
          <label htmlFor="agenda-paste" className="font-medium">
            Paste an agenda
          </label>
          <Textarea
            id="agenda-paste"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste an email, chat message, or meeting notes…"
            rows={3}
            disabled={parsing || saving}
          />
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">
              {text.length.toLocaleString()} / 10,000 characters
            </span>
            {parsing ? (
              <>
                <span role="status" className="text-sm">
                  Reading your agenda…
                </span>
                <Button variant="outline" onClick={cancelParse}>
                  Cancel
                </Button>
              </>
            ) : (
              <Button onClick={parse} disabled={!text.trim() || saving}>
                Parse
              </Button>
            )}
          </div>
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <fieldset
          disabled={parsing || saving}
          className="grid gap-4 disabled:opacity-60"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {field("title", "Agenda title", agenda.title, (v) =>
              setAgenda({ ...agenda, title: v || null }),
            )}
            {field(
              "starts_at",
              "Starts at (ISO date with offset)",
              agenda.starts_at,
              (v) => setAgenda({ ...agenda, starts_at: v || null }),
            )}
            {field(
              "duration_minutes",
              "Duration (minutes)",
              agenda.duration_minutes,
              (v) =>
                setAgenda({
                  ...agenda,
                  duration_minutes: v === "" ? null : Number(v),
                }),
              "number",
            )}
            {field("language", "Language", agenda.language, (v) =>
              setAgenda({ ...agenda, language: v }),
            )}
          </div>
          <div className="grid gap-3">
            <h3 className="font-medium">Topics</h3>
            {agenda.items.map((item, i) => (
              <div
                key={i}
                className="grid gap-2 rounded-lg border p-3 sm:grid-cols-3"
              >
                {field(`items.${i}.topic`, `Topic ${i + 1}`, item.topic, (v) =>
                  setAgenda({
                    ...agenda,
                    items: agenda.items.map((r, j) =>
                      j === i ? { ...r, topic: v } : r,
                    ),
                  }),
                )}
                {field(
                  `items.${i}.owner`,
                  `Topic ${i + 1} owner`,
                  item.owner,
                  (v) =>
                    setAgenda({
                      ...agenda,
                      items: agenda.items.map((r, j) =>
                        j === i ? { ...r, owner: v || null } : r,
                      ),
                    }),
                )}
                {field(
                  `items.${i}.minutes`,
                  `Topic ${i + 1} minutes`,
                  item.minutes,
                  (v) =>
                    setAgenda({
                      ...agenda,
                      items: agenda.items.map((r, j) =>
                        j === i
                          ? { ...r, minutes: v === "" ? null : Number(v) }
                          : r,
                      ),
                    }),
                  "number",
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setAgenda({
                      ...agenda,
                      items: agenda.items.filter((_, j) => j !== i),
                    });
                    removeSuggestedRow("items", i);
                  }}
                >
                  Remove topic {i + 1}
                </Button>
              </div>
            ))}
            <Button
              variant="outline"
              onClick={() =>
                setAgenda({
                  ...agenda,
                  items: [
                    ...agenda.items,
                    { topic: "", owner: null, minutes: null },
                  ],
                })
              }
              disabled={agenda.items.length >= 50}
            >
              Add topic
            </Button>
          </div>
          <div className="grid gap-3">
            <h3 className="font-medium">Action items</h3>
            {agenda.action_items.map((item, i) => (
              <div
                key={i}
                className="grid gap-2 rounded-lg border p-3 sm:grid-cols-3"
              >
                {field(
                  `action_items.${i}.task`,
                  `Action ${i + 1}`,
                  item.task,
                  (v) =>
                    setAgenda({
                      ...agenda,
                      action_items: agenda.action_items.map((r, j) =>
                        j === i ? { ...r, task: v } : r,
                      ),
                    }),
                )}
                {field(
                  `action_items.${i}.owner`,
                  `Action ${i + 1} owner`,
                  item.owner,
                  (v) =>
                    setAgenda({
                      ...agenda,
                      action_items: agenda.action_items.map((r, j) =>
                        j === i ? { ...r, owner: v || null } : r,
                      ),
                    }),
                )}
                {field(
                  `action_items.${i}.due`,
                  `Action ${i + 1} due`,
                  item.due,
                  (v) =>
                    setAgenda({
                      ...agenda,
                      action_items: agenda.action_items.map((r, j) =>
                        j === i ? { ...r, due: v || null } : r,
                      ),
                    }),
                  "date",
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setAgenda({
                      ...agenda,
                      action_items: agenda.action_items.filter(
                        (_, j) => j !== i,
                      ),
                    });
                    removeSuggestedRow("action_items", i);
                  }}
                >
                  Remove action {i + 1}
                </Button>
              </div>
            ))}
            <Button
              variant="outline"
              onClick={() =>
                setAgenda({
                  ...agenda,
                  action_items: [
                    ...agenda.action_items,
                    { task: "", owner: null, due: null },
                  ],
                })
              }
              disabled={agenda.action_items.length >= 50}
            >
              Add action
            </Button>
          </div>
        </fieldset>
        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            disabled={saving}
            onClick={() => {
              cancelParse();
              onClose();
            }}
          >
            Close
          </Button>
          <Button onClick={save} disabled={saving || parsing}>
            {saving ? "Saving…" : "Save agenda"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
