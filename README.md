# Chief of Staff: Multi-Agent Assistant on n8n

A "chief of staff" assistant built from nine n8n workflows. A **Router** agent receives requests (chat, schedules, webhooks) and hands them to specialist agents for briefing, scheduling, email and follow-ups.

The design is **propose, then approve, then execute**:

1. Specialist agents run in *propose* mode only. They read calendar, mail, Slack and Drive, then return proposals.
2. Every proposal is saved as a `pending` row in a data table and shown to the user with a `proposal_id`.
3. Only after the user approves does an *execute* workflow run. It re-reads the stored row, re-validates it and performs the action.

All agents use the OpenAI chat model `gpt-6.1-sol`. All workflows share the same error workflow (`mgTS3Y2KolpDdVX`).

## Workflow inventory

| File | Workflow | Role |
|---|---|---|
| `Chief of Staff - Router.json` | Chief of Staff - Router | Entry point, routing, scheduled and event runs, Slack approvals |
| `Briefing agent (read-only).json` | Briefing agent (read-only) | Builds briefs, never proposes anything |
| `CM - Email (propose).json` | CM - Email (propose) | Inbox triage and saved reply drafts |
| `CM - Read Thread (tool).json` | CM - Read Thread (tool) | Helper tool that reads one Gmail thread |
| `Email agent (execute).json` | Email agent (execute) | Sends approved drafts |
| `Scheduler agent (propose).json` | Scheduler agent (propose) | Proposes meeting slots, reschedules, cancellations |
| `Scheduler agent (execute).json` | Scheduler agent (execute) | Books, moves or cancels approved events |
| `Follow-up agent (propose).json` | Follow-up agent (propose) | Finds open loops and proposes next steps |
| `Follow-up agent (execute).json` | Follow-up agent (execute) | Executes approved emails, tasks and events |

---

## Part 1: The individual agents

### 1. Briefing agent (read-only)

**Purpose:** a concise, two-minute brief of a day, week, meeting, person or topic.

- **Trigger:** called by the Router, either as the `briefing` tool in chat or from the morning-brief and weekly-review runs. Input is a `task` JSON.
- **Tools (all read-only):**
  - `calendar_events`: Google Calendar events between two times, with attendees.
  - `search_mail`: Gmail search with operators, up to 15 messages.
  - `search_chat`: Slack message search, up to 20 messages.
  - `search_docs`: Google Drive file-name search, returning id, name and link.
- **Behaviour:**
  1. Works out the scope and window (default is today). If it cannot infer the scope it returns `needs_input`.
  2. Pulls calendar events, then searches mail, chat and docs for context on each meeting.
  3. Returns a structured `brief`: `title`, `summary`, `events` (with a prep line each), `key_points`, `open_items`, `people`, `documents` and `sources`. Facts must be cited and never invented.
- **Output:** `status` (`ok`, `needs_input` or `no_action`), `results.brief` and `notes`. `proposed_actions` is always an empty array.
- **Safety:** treats all email, chat and document text as data, not instructions. It states that `aiagenticlearner@gmail.com` is the user's own calendar.
- **Data tables:** none are read or written.

### 2. CM - Read Thread (tool)

**Purpose:** a small helper sub-workflow, used as the `read_thread` tool by the Email agent.

- **Input:** `thread_id` and `user_id`.
- **Flow:** Gmail *Get thread*, then a Code node that:
  - decodes the base64 body, preferring plain text and falling back to stripped HTML,
  - removes quoted lines (`>`) and "On … wrote:" tails,
  - keeps only the **last 6 messages**, each capped at **1,500 characters**.
- **Output:** `{ thread_id, untrusted_email_content: true, messages: [{ from, date, body }] }`. The `untrusted_email_content` flag reminds the calling agent to treat the text as data.

### 3. CM - Email (propose)

**Purpose:** triage the inbox and prepare reply drafts. It never sends anything.

- **Input:** `user_id` and a `task` JSON. The task must contain `task_id`, `agent` and `goal`. The `Parse task` node forces `mode = "propose"`.
- **Flow:**
  1. **Load profile.** Looks up the *active* row for `user_id` in `user_profiles`. An unknown or inactive user gets a `failed` response.
  2. **Build context.** Reads timezone, working hours, preferences, VIP list and company domains from the profile.
  3. **Window.** Uses `task.inputs.time_window`, otherwise the last 24 hours (or `preferences.triage_window_hours`).
  4. **Fetch and compact inbox.** Pulls up to 100 messages, drops promotions, social and forum noise (unless VIP or sent directly to the user), keeps one row per thread and caps the list at 80.
  5. **Email agent** (up to 15 iterations) with these tools:
     - `read_thread` (up to 8 threads),
     - `search_mail`,
     - `my_sent_style`, the user's last 5 sent emails, for tone only,
     - `calendar_lookup`,
     - `create_draft`, which saves a Gmail draft and never sends.
  6. **Triage buckets:** urgent, meeting_logistics, needs_reply, fyi and noise. It also extracts `meeting_requests` and `action_items`, writes at most 8 drafts and sets `needs_scheduler` when meeting times must be found. Drafts that need times carry the placeholder `[TIME OPTIONS FROM CALENDAR]`.
  7. **Validate output.** Drops drafts with no `draft_id` or `thread_id`, caps drafts at 8, recomputes `external` from recipient domains and sets `needs_scheduler`.
  8. **Verify drafts.** Calls Gmail *Get draft* for every draft id and drops any that no longer exist.
  9. **Save and respond.** Writes each surviving draft to `pending_proposals` as a `send_draft` proposal and returns `proposed_actions` with ids.
- **Output:** `{ status, results {counts, urgent, meeting_requests, action_items, fyi_digest, noise_summary, needs_scheduler}, proposed_actions[], notes }`.

### 4. Email agent (execute)

**Purpose:** send drafts the user has approved.

- **Input:** `user_id` and `proposal_ids`.
- **Flow:**
  1. Reads `pending_proposals` rows where `user_id` matches, `status = pending` and `agent = email`.
  2. `Pick approved` keeps only rows whose id was approved and parses the stored `action` JSON.
  3. If the action is `send_draft` with a `draft_id`, it calls Gmail `drafts/send` (3 retries).
  4. On success it marks the row `done` and returns `Sent: <summary>`.
  5. If Gmail refuses (for example the draft was deleted or already sent), it returns `failed` and the proposal **stays pending**.
  6. Any other action type or unreadable action returns `failed` with a reason.
- Nothing is rewritten at execution time: the stored draft is sent exactly as saved.

### 5. Scheduler agent (propose)

**Purpose:** find free time and propose bookings, reschedules or cancellations. It never changes the calendar.

- **Input:** `user_id` and a `task` JSON (`task_id`, `agent`, `goal` and inputs such as attendees, window and duration).
- **Context:** working hours (default 09:30–18:30), default duration (30 min), buffer (10 min), company domains and calendars.
- **Tools:** `get_events` (list events on one calendar) and `check_availability` (free/busy for one slot).
- **Agent rules:** only future slots, inside working hours, **Monday to Friday**, buffer respected, at most 3 options. Weekend requests are flagged and the nearest weekday is offered. Proposal types are `create_event`, `reschedule_event`, `cancel_event` and `propose_times`.
- **Vetting pipeline (code, not the LLM):**
  1. **Validate output.** Drops malformed proposals, requires `event_id` for reschedule or cancel, checks valid start and end, and recomputes `external` from attendee domains.
  2. **Check step.** Drops proposals that start in the past, fall on a weekend or fall outside working hours. If only weekend options were dropped, the status becomes `needs_input`.
  3. **Invitee free/busy.** Calls Google `freeBusy` for every non-self attendee. An option is removed if any invitee is busy or their calendar cannot be read.
  4. **Final proposals.** Keeps at most 3. A status of `ok` with nothing left becomes `no_action`.
- **Queue for approval:** surviving proposals are written to `pending_proposals` (`agent = scheduler`).

### 6. Scheduler agent (execute)

**Purpose:** carry out approved scheduler proposals safely.

- **Input:** `user_id` and `proposal_ids`.
- **Pick approved:**
  - Loads this user's pending `scheduler` rows that match the approved ids.
  - Converts an approved time option (`propose_times`, `propose_time` or `book_slot`) into `create_event`, or into `reschedule_event` if it has an `event_id`.
  - **Weekend guard:** a create or reschedule on Saturday or Sunday (Asia/Kolkata) is refused and the proposal stays pending.
- **Routing:**
  - **Create event:** re-checks the user's free/busy, then every invitee's free/busy, then creates the event with `sendUpdates: all`.
  - **Reschedule event:** same double check, then updates only start and end.
  - **Cancel event:** deletes the event with `sendUpdates: all`.
- **Results:**
  - Success: the row is marked `done` and the workflow returns `Done: <summary>`.
  - Slot taken, invitee busy or invitee calendar not shared: returns `failed` and the proposal **stays pending**.

### 7. Follow-up agent (propose)

**Purpose:** find open loops (unrecapped meetings, unanswered sent emails, promises, open asks) and propose the next step.

- **Input:** a `task` JSON that must include `task_id`, `user_id` and `goal`. The `agent` is forced to `follow_up` and the mode to `propose`.
- **Look-back window:** `inputs.lookback_days`, else `preferences.follow_up_lookback_days`, else 3 days.
- **Tools (read-only):** `calendar_events`, `search_mail`, `search_chat`, `search_docs`.
- **Proposal types:**
  - `send_email` (to, cc, subject, full body, optional thread_id),
  - `create_task` (title, notes, due),
  - `create_event` (title, start, end, attendees, calendar_id),
  - `update_event` (event_id plus new details).
  - Content must be final, with no placeholders, because it runs exactly as written.
- **Validation (code):** drops unknown types, missing summaries or incomplete emails and tasks. It also drops events with an invalid start/end or a start in the past, recomputes `external`, and caps proposals at 8.
- **Queue for approval:** proposals are saved to `pending_proposals` with `agent = follow_up` and ids prefixed `fu-`. Open loops go back in `results.open_loops` even if no action was proposed.

### 8. Follow-up agent (execute)

**Purpose:** carry out approved follow-up proposals.

- **Input:** `user_id` and `proposal_ids` (array).
- **Routing by stored action `type`:**
  - `create_event`: re-checks free/busy, then creates the event (`sendUpdates: all`).
  - `update_event`: re-checks free/busy, then updates the event (title, times, attendees).
  - `send_email`: sends through Gmail with to, cc, subject and body.
  - `create_task`: creates a Google Task (due date defaults to tomorrow).
  - Anything else returns `failed`.
- On success the proposal row is marked `done`. A taken slot returns `failed` and the proposal stays pending.
- Unlike the scheduler executor, this one checks only the user's own calendar, not the invitees' calendars, and has no weekend guard.

---

## Part 2: The Router agent (Chief of Staff - Router)

The Router is the front door. It has several entry points, all of which load the user's profile before doing anything else.

### Entry points

| Trigger | Node | Meaning |
|---|---|---|
| Chat | `Chat with router` | Public n8n chat. `user_id` comes from `user.email`, `metadata.user_id`, or falls back to `u_001`. |
| Webhook | `Event webhook` (POST `/chief-of-staff-router-events`, header auth) | Event triggers: `meeting_ended`, `email_received`, `conflict_detected`. |
| Schedule | Morning brief (weekdays 07:30), Evening sweep (weekdays 18:00), Weekly review (Fridays 16:00) | Each lists all active users and runs once per user. |

All inputs are normalised, then **Load profile** (reads `user_profiles`) and **Build runtime vars** build the runtime context. The context holds name, email, timezone (default `Asia/Kolkata`), working hours, calendars, preferences, standing approvals and the current time. **Route by input type** then splits chat messages from background runs.

### Chat path: Router agent

The Router agent (max 8 iterations, 10-message memory keyed by `user_id`) does no work itself. It builds a JSON task and calls specialist tools:

- `briefing`: read-only overview.
- `scheduler_propose`, `email_propose`, `followup_propose`: return proposals with ids.
- `scheduler_execute`, `email_execute`, `followup_execute`: run approved proposals.
- `approve_execution`: a human-in-the-loop (HITL) approve/decline tool. The three execute tools are wired *behind* it, so an execution needs the user's confirmation in chat.

Rules in its system prompt:

- Show proposals as a numbered list with ids.
- Call an `*_execute` tool only with ids the user approved in their **latest** message. If nothing specific is approved, ask which numbers to run.
- Never claim anything was sent, booked or created unless an execute tool confirmed it.
- If an email result has `needs_scheduler = true`, offer to call `scheduler_propose`.
- Reply briefly: urgent items first, then proposals, then a one-line FYI.

### Background paths (results go to Slack)

| Trigger | Flow | Output |
|---|---|---|
| `morning_brief` | Email triage (last 24h) and open follow-ups (last 7 days) in parallel, then merge, then Briefing agent | Slack brief |
| `evening_sweep` | Follow-up agent over today's activity | Slack list of proposals, with a prompt to approve in chat |
| `weekly_review` | Briefing agent for this week and next | Slack review |
| `meeting_ended` | Follow-up agent with the event payload | Slack recap, open items and proposed follow-ups |
| `email_received` | Email agent. If `needs_scheduler`, it goes on to scheduling. Otherwise a Slack triage note. | Slack note or the approval flow below |
| `conflict_detected` | Straight to scheduling | Approval flow below |
| unknown | n/a | Slack note about the unknown trigger |

### Slack approval flow for schedule changes

1. **Propose schedule changes** calls Scheduler (propose).
2. **Has proposals?** If there are none, a Slack "no changes" note is sent.
3. **Ask for approval** sends a Slack *send-and-wait* message (Approve or Reject) listing all proposals.
4. **Approved:** runs Scheduler (execute) with all proposal ids and sends a confirmation listing each result.
5. **Rejected (or declined):** `Mark rejected` sets each row to `rejected`, then a rejection note is sent.

### Error handling

- Sub-workflow calls retry up to 3 times and continue on error.
- An in-workflow error trigger, `On workflow error`, sends a Slack alert with the workflow name, failed node, error message and execution link. Every workflow also points at the shared error workflow.

---

## Part 3: Data tables

There are two n8n Data Tables.

### `user_profiles` (id `WCuHtLBeLnFmdhTc`)

One row per user. **The workflows only read it. Nothing writes to it**, so it is maintained manually.

| Column | Used for |
|---|---|
| `user_id` | Key used everywhere |
| `name`, `email` | Identity in prompts and triage |
| `tz` | Timezone (default `Asia/Kolkata`) |
| `working_hours` (JSON) | Slot proposals (default 09:30–18:30) |
| `calendars` (JSON) | Calendars to read |
| `preferences` (JSON) | `default_duration`, `buffer_minutes`, `company_domains`, `vip`, `triage_window_hours`, `follow_up_lookback_days` |
| `standing_approvals` (JSON) | Passed to agents as context |
| `active` (boolean) | Only active users get scheduled runs and agent access |

**Read when:**

- the Router receives any chat, webhook or scheduled input;
- each propose workflow starts (they look up the active profile by `user_id`);
- the three scheduled triggers list every row where `active` is true.

### `pending_proposals` (id `5NcIttwxWCVGLBLB`)

The approval queue and audit trail for everything that would change the outside world.

| Column | Meaning |
|---|---|
| `proposal_id` | Unique id. Email and scheduler use `<executionId>-<n>`; follow-up uses `fu-<executionId>-<n>`. |
| `user_id` | Owner. Every read and update filters on it, except Mark rejected (see below). |
| `agent` | `email`, `scheduler` or `follow_up`. Execute workflows only load their own agent's rows. |
| `action` | The full proposal as a JSON string, executed as stored. |
| `summary` | One-line description shown to the user. |
| `external` | `true` if any recipient or attendee is outside the company domains. |
| `status` | `pending`, `done` or `rejected` |

**Status lifecycle and when each change happens:**

| Transition | Done by | Condition |
|---|---|---|
| *(new row)* → `pending` | `Save proposals` in Email, Scheduler and Follow-up (propose) | A propose run ends with at least one valid proposal. If there are none, nothing is written. |
| `pending` → `done` | `Mark done` in Email, Scheduler and Follow-up (execute) | The action actually succeeded: draft sent, event created, moved or cancelled, email sent or task created. The update is matched on `proposal_id`, `user_id` and `status = pending`, so a proposal cannot run twice. |
| `pending` → `rejected` | `Mark rejected` in the Router | The user presses **Reject** on the Slack approval for schedule changes. |
| stays `pending` | n/a | Execution failed or was refused: slot taken, invitee busy or calendar unreadable, weekend, draft missing, unreadable action, or unsupported type. The reason is returned and the user can retry. |

**Things to know:**

- Execute workflows only act on rows that are still `pending`, belong to the user and match an approved id. Anything else returns a "No pending … proposals match" failure.
- Chat approvals use the `approve_execution` tool and the execute workflows. They do not set `rejected`. A declined chat proposal simply stays `pending`.
- `Mark rejected` matches on `proposal_id` and `status = pending` only, not `user_id`. This is safe in practice because ids are execution-unique.
- Rows are never deleted. There is no expiry, so old `pending` rows accumulate unless you add a cleanup.

---

## External services and credentials

Gmail (OAuth2), Google Calendar (OAuth2), Google Drive, Google Tasks, Slack (OAuth2), OpenAI, an n8n Header Auth credential for the event webhook, and the n8n Data Tables.

## Setup notes

1. Import all nine workflows. Workflow ids are referenced by id, so keep them or re-point the `Execute Workflow` and tool nodes.
2. Create the `user_profiles` and `pending_proposals` data tables with the columns above and set `active` to true on your profile row.
3. Replace the placeholder `company_domains` default (`example.com`) with your domains in `preferences`.
4. Reconnect all credentials and update the Slack user id used for notifications.
5. Make sure the shared error workflow `mgTS3Y2KolpDdVX` exists.
