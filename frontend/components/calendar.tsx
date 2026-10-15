"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, MapPin, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, type Meeting, type MeetingInput } from "@/lib/api";

const pad = (value: number) => String(value).padStart(2, "0");
const dateKey = (date: Date) =>
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
const asLocalInput = (date: Date) =>
  `${dateKey(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
const monthRange = (month: Date) => {
  const start = new Date(month.getFullYear(), month.getMonth(), 1);
  const end = new Date(month.getFullYear(), month.getMonth() + 1, 1);
  return [start.toISOString(), end.toISOString()] as const;
};
const initialForm = (date: Date): MeetingInput => {
  const start = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
    10,
  );
  const end = new Date(start.getTime() + 60 * 60_000);
  return {
    title: "",
    start_at: start.toISOString(),
    end_at: end.toISOString(),
    location: null,
    purpose: null,
  };
};

export function Calendar() {
  const client = useQueryClient();
  const [month, setMonth] = useState(
    () => new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  );
  const [selected, setSelected] = useState(() => dateKey(new Date()));
  const [editing, setEditing] = useState<Meeting | null>(null);
  const [form, setForm] = useState<MeetingInput>(() => initialForm(new Date()));
  const [formError, setFormError] = useState("");
  const range = monthRange(month);
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["meetings", ...range],
    queryFn: () => api.listMeetings(...range),
  });
  const meetings = data?.meetings ?? [];
  const days = useMemo(() => {
    const offset = new Date(month.getFullYear(), month.getMonth(), 1).getDay();
    const count = new Date(
      month.getFullYear(),
      month.getMonth() + 1,
      0,
    ).getDate();
    return Array.from(
      { length: Math.ceil((offset + count) / 7) * 7 },
      (_, i) => {
        const day = i - offset + 1;
        return day > 0 && day <= count
          ? new Date(month.getFullYear(), month.getMonth(), day)
          : null;
      },
    );
  }, [month]);
  const dailyMeetings = meetings.filter(
    (meeting) => dateKey(new Date(meeting.start_at)) === selected,
  );

  const save = useMutation({
    mutationFn: () =>
      editing ? api.updateMeeting(editing.id, form) : api.createMeeting(form),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["meetings"] });
      toast.success(editing ? "Meeting updated" : "Meeting created");
      setEditing(null);
      setFormError("");
    },
    onError: (err: Error) => setFormError(err.message),
  });
  const remove = useMutation({
    mutationFn: (meeting: Meeting) => api.deleteMeeting(meeting.id),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["meetings"] });
      toast.success("Meeting deleted");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function beginCreate() {
    const date = new Date(`${selected}T12:00:00`);
    setEditing(null);
    setForm(initialForm(date));
    setFormError("");
  }
  function beginEdit(meeting: Meeting) {
    setEditing(meeting);
    setForm({
      title: meeting.title,
      start_at: meeting.start_at,
      end_at: meeting.end_at,
      location: meeting.location,
      purpose: meeting.purpose,
    });
    setFormError("");
  }
  function updateLocal(field: keyof MeetingInput, value: string) {
    setForm((old) => ({
      ...old,
      [field]:
        field === "start_at" || field === "end_at"
          ? new Date(value).toISOString()
          : value || null,
    }));
  }

  return (
    <div className="grid gap-7">
      <PageHeader
        icon="🗓️"
        title="Calendar"
        description="Plan and manage your meetings."
        action={
          <Button onClick={beginCreate}>
            <Plus data-icon="inline-start" className="size-4" />
            New meeting
          </Button>
        }
      />
      <section
        className="notion-surface overflow-hidden"
        aria-label="Monthly calendar"
      >
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="text-lg font-semibold">
            {month.toLocaleDateString(undefined, {
              month: "long",
              year: "numeric",
            })}
          </h2>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Previous month"
              onClick={() =>
                setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))
              }
            >
              <ChevronLeft />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                const today = new Date();
                setMonth(new Date(today.getFullYear(), today.getMonth(), 1));
                setSelected(dateKey(today));
              }}
            >
              Today
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Next month"
              onClick={() =>
                setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))
              }
            >
              <ChevronRight />
            </Button>
          </div>
        </div>
        {isError ? (
          <Alert variant="destructive" className="m-4">
            <AlertTitle>Could not load meetings</AlertTitle>
            <AlertDescription className="flex items-center gap-3">
              {(error as Error).message}
              <Button size="sm" variant="outline" onClick={() => refetch()}>
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        ) : (
          <>
            <div className="grid grid-cols-7 border-b text-center text-xs font-medium text-muted-foreground">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                <div key={day} className="py-2">
                  {day}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7">
              {days.map((day, index) => {
                const key = day ? dateKey(day) : `blank-${index}`;
                const count = day
                  ? meetings.filter(
                      (m) => dateKey(new Date(m.start_at)) === key,
                    ).length
                  : 0;
                return (
                  <button
                    type="button"
                    key={key}
                    disabled={!day}
                    onClick={() => day && setSelected(key)}
                    aria-pressed={day ? selected === key : undefined}
                    className={`min-h-16 border-r border-b p-1.5 text-left transition sm:min-h-24 sm:p-2 ${day ? "hover:bg-accent/60" : "bg-muted/30"} ${day && selected === key ? "bg-tint-blue" : ""}`}
                  >
                    {day && (
                      <>
                        <span
                          className={`grid size-7 place-items-center rounded-full text-sm ${key === dateKey(new Date()) ? "bg-primary font-semibold text-primary-foreground" : ""}`}
                        >
                          {day.getDate()}
                        </span>
                        {count > 0 && (
                          <span className="mt-1 block truncate rounded bg-tint-peach px-1.5 py-0.5 text-[10px] text-tint-peach-foreground sm:text-xs">
                            {count} meeting{count === 1 ? "" : "s"}
                          </span>
                        )}
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          </>
        )}
      </section>
      <section className="grid gap-3" aria-live="polite">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">
              {new Date(`${selected}T12:00:00`).toLocaleDateString(undefined, {
                weekday: "long",
                month: "long",
                day: "numeric",
              })}
            </h2>
            <p className="text-sm text-muted-foreground">
              {dailyMeetings.length} meeting
              {dailyMeetings.length === 1 ? "" : "s"}
            </p>
          </div>
          <Button variant="outline" onClick={beginCreate}>
            <Plus data-icon="inline-start" className="size-4" />
            Add meeting
          </Button>
        </div>
        {isPending ? (
          <div className="rounded-lg border p-6 text-sm text-muted-foreground">
            Loading meetings…
          </div>
        ) : dailyMeetings.length === 0 ? (
          <div className="rounded-xl border border-dashed p-8 text-center">
            <p className="font-medium">No meetings scheduled</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Create a meeting for this day to see it here.
            </p>
            <Button className="mt-4" variant="outline" onClick={beginCreate}>
              Create meeting
            </Button>
          </div>
        ) : (
          dailyMeetings.map((meeting) => (
            <article
              key={meeting.id}
              className="notion-surface flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between"
            >
              <button
                type="button"
                className="text-left"
                onClick={() => beginEdit(meeting)}
              >
                <h3 className="font-semibold hover:text-primary">
                  {meeting.title}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {new Date(meeting.start_at).toLocaleTimeString([], {
                    hour: "numeric",
                    minute: "2-digit",
                  })}{" "}
                  –{" "}
                  {new Date(meeting.end_at).toLocaleTimeString([], {
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                </p>
                {meeting.location && (
                  <p className="mt-2 flex items-center gap-1 text-sm text-muted-foreground">
                    <MapPin className="size-3.5" />
                    {/^https?:\/\//i.test(meeting.location) ? (
                      <a
                        href={meeting.location}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {meeting.location}
                      </a>
                    ) : (
                      meeting.location
                    )}
                  </p>
                )}
                {meeting.purpose && (
                  <p className="mt-2 text-sm">{meeting.purpose}</p>
                )}
              </button>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => beginEdit(meeting)}
                >
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Delete ${meeting.title}`}
                  onClick={() =>
                    window.confirm(`Delete “${meeting.title}”?`) &&
                    remove.mutate(meeting)
                  }
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
            </article>
          ))
        )}
      </section>
      {form && (
        <section
          className="notion-surface grid gap-4 p-5"
          aria-label={editing ? "Edit meeting" : "Create meeting"}
        >
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              {editing ? "Edit meeting" : "New meeting"}
            </h2>
            <Button variant="ghost" size="sm" onClick={() => setEditing(null)}>
              Close
            </Button>
          </div>
          {formError && (
            <p role="alert" className="text-sm text-destructive">
              {formError}
            </p>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2 sm:col-span-2">
              <Label htmlFor="meeting-title">Title</Label>
              <Input
                id="meeting-title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="meeting-start">Starts</Label>
              <Input
                id="meeting-start"
                type="datetime-local"
                value={asLocalInput(new Date(form.start_at))}
                onChange={(e) => updateLocal("start_at", e.target.value)}
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="meeting-end">Ends</Label>
              <Input
                id="meeting-end"
                type="datetime-local"
                value={asLocalInput(new Date(form.end_at))}
                onChange={(e) => updateLocal("end_at", e.target.value)}
                required
              />
            </div>
            <div className="grid gap-2 sm:col-span-2">
              <Label htmlFor="meeting-location">Location or meeting URL</Label>
              <Input
                id="meeting-location"
                value={form.location ?? ""}
                onChange={(e) =>
                  setForm({ ...form, location: e.target.value || null })
                }
              />
            </div>
            <div className="grid gap-2 sm:col-span-2">
              <Label htmlFor="meeting-purpose">Purpose</Label>
              <Textarea
                id="meeting-purpose"
                value={form.purpose ?? ""}
                onChange={(e) =>
                  setForm({ ...form, purpose: e.target.value || null })
                }
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button
              disabled={save.isPending}
              onClick={() => {
                setFormError("");
                const parsed = awaitlessValidate(form);
                if (!parsed) {
                  setFormError(
                    "Add a title and ensure the end time is later than the start time.",
                  );
                  return;
                }
                save.mutate();
              }}
            >
              {save.isPending ? "Saving…" : "Save meeting"}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}

function awaitlessValidate(form: MeetingInput) {
  return form.title.trim() && new Date(form.end_at) > new Date(form.start_at);
}
