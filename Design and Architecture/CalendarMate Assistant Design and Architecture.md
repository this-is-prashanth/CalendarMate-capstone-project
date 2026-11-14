# CalendarMate: Design and Architecture

The assistant is a router-plus-specialists system on n8n in which agents only propose, a person approves, and separate execute workflows act on exactly what was approved.

## Architecture diagram

![architecture · Router, 4 specialists, approval gate, 3 executors](images/CalendarMate-Assistant-Design-and-Architecture-image1.png)

architecture · Router, 4 specialists, approval gate, 3 executors

Chat, schedules and webhooks enter through the Router. Specialists save proposals to pending\_proposals, a person approves, and only the execute layer writes to Gmail, Calendar and Tasks.

## Functionality mapping

Every user need maps to one trigger, one specialist and one approval rule; only briefs skip approval, because they change nothing.

| Need | Trigger | Workflows involved |
| --- | --- | --- |
| Morning brief | Weekdays 07:30 schedule, or a chat request | Router, Email (propose), Follow-up (propose), Briefing |
| Evening sweep | Weekdays 18:00 schedule | Router, Follow-up (propose) |
| Weekly review | Fridays 16:00 schedule | Router, Briefing |
| Inbox triage and reply drafts | Chat, email\_received webhook, or the morning brief | Email (propose), Read Thread, Email (execute) |
| Meeting requests and conflicts | Chat, conflict\_detected webhook, or mail flagged needs\_scheduler | Scheduler (propose), Scheduler (execute) |
| Post-meeting follow-ups | meeting\_ended webhook, or chat | Follow-up (propose), Follow-up (execute) |
| Failure visibility | Any workflow error | Router error trigger, shared error workflow |

## Orchestration pattern

The system uses a supervisor (router) over specialist agents called as tools, a hybrid of LLM routing for chat and fixed routing for background events, with every side effect behind a human approval gate.

**How it works**

1. The Router agent turns a chat request into a JSON task and calls one specialist as a tool. In background runs, a Switch node on the trigger name does the same job without an LLM.
2. The specialist reads systems read-only and returns proposals. Code validates them and stores them in pending\_proposals as pending.
3. The user approves by proposal id, in chat through the approve\_execution tool or in Slack through an Approve/Reject message.
4. An execute workflow re-reads the stored row, re-checks the world (free/busy, draft still exists) and acts. It marks the row done only on success.

**Why this pattern**

- **Supervisor with specialists:** each agent gets one job, a short prompt and only the tools that job needs. The Router carries no calendar, mail or Slack tools, so a confused request cannot reach them directly.
- **Hybrid routing:** chat is open-ended, so an LLM picks the specialist. Schedules and webhooks name their intent exactly (morning\_brief, meeting\_ended), so a Switch node is cheaper, faster and deterministic.
- **Propose, approve, execute:** mail, invitations and calendar changes reach other people and cannot be undone. Splitting thinking from acting makes the approval step a hard boundary in the design, not a promise in a prompt.
- **State in a table, not in the conversation:** the approved action is the stored row, so what the user saw is what runs. The model cannot rewrite it between approval and execution.

## Agent design decisions

Each agent has the narrowest permissions and the smallest output contract its job allows, and code, not the model, enforces every rule that matters.

| Agent | Key design decisions |
| --- | --- |
| Router | Does not do the work itself. Executes only ids approved in the user's latest message, and never reports success unless an execute tool confirmed it. |
| Briefing | Always returns proposed\_actions: \[\]. Every fact must cite a source, and an empty field is preferred to a guess. |
| Email (propose) | Triage runs on a compacted one-row-per-thread list, so the model reads less mail. It reads sent mail for tone only and never quotes it. It never commits the user to money, deadlines or decisions. |
| Read Thread | Quoted replies are stripped and the result is flagged untrusted, which keeps prompts small and limits injection surface. |
| Scheduler (propose) | Slots must be future, weekday and inside working hours with a buffer. The model does not claim invitee availability, because code checks it afterwards. |
| Follow-up (propose) | Writes final content with no placeholders, because the approved action runs exactly as stored. Lists open loops even when it proposes nothing. |
| Execute workflows | Plain deterministic logic: re-read the stored row, re-validate, act, then mark done. |

## Tool selection rationale

Tools were chosen to keep reads cheap and read-only for agents, writes deterministic and approval-gated, and the whole system inside one n8n instance.

| Tool or component | Used for | Why it was chosen |
| --- | --- | --- |
| n8n sub-workflows, called as tools or via Execute Workflow | Each agent as its own workflow | Isolated, separately testable units with a clear input and output contract; the Router can call them without knowing their internals. |
| n8n AI Agent nodes on OpenAI gpt-4.1-mini | Router and the four reasoning agents | Native tool-calling with iteration caps; one model keeps behaviour consistent across agents. |
| Structured Output Parser | Briefing, Email, Scheduler, Follow-up | Forces typed JSON that the validation code can check, instead of free text. |
| Window-buffer memory (10 messages, keyed by user\_id) | Router chat | Lets a user approve by number in a follow-up message without restating the proposals. |
| Chat HITL tool approve\_execution | Gate in front of the three execute tools | Puts a human confirmation in the tool path itself, not just in the prompt. |
| Slack send-and-wait | Approvals for background scheduling runs | An asynchronous Approve/Reject for runs nobody is chatting in; the same channel carries briefs and alerts. |
| Slack search | Briefing, Follow-up | Open asks and decisions often live in chat rather than mail. |
| Gmail (nodes plus HTTP drafts/send) | Triage, drafts, sending | Saving a draft first lets the user see exact text; sending that saved draft guarantees the sent text matches the reviewed text. |
| Google Calendar (nodes plus HTTP freeBusy) | Events, availability, booking | The node checks one calendar; the free/busy API checks every invitee in one call, and a calendar that cannot be read counts as not free. |
| Google Drive file search | Briefing, Follow-up | Finds agendas and decks by name, with a link; read-only. |
| Google Tasks | Approved follow-up reminders | A lightweight target for "remind me" actions. |
| n8n Data Tables | user\_profiles, pending\_proposals | Built into n8n, so profiles and the approval queue need no extra database or credentials. |
| Code nodes | Parsing, validation, caps, weekend and hours rules | Deterministic checks that the model cannot talk its way past. |
| Schedule triggers, and a header-authenticated webhook | Briefs, sweeps, reviews, event triggers | Proactive behaviour without a user prompt, while the webhook accepts only authenticated callers. |
| Shared error workflow and an error trigger | Failure alerts | Failures are posted to Slack with workflow, node and execution link, so silent breakage is unlikely. |