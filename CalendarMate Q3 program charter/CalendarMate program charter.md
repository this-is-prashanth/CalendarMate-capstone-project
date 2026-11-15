# CalendarMate program charter

CalendarMate is an assistant of four specialist agents behind one router that aims to give PMs, TPMs and senior ICs at ServionIQ back part of the roughly 2 hours a day they spend on meeting logistics, scheduling and email triage; the CTO is the sponsor. This is a draft for the CTO's review: targets, dates and owners are proposals unless marked as given.

## Vision

Every PM, TPM and senior IC starts the day with one page that says what matters, and spends minutes, not hours, on scheduling and inbox triage.

The load today, as given in the CTO's problem statement:

- 8 to 14 meetings a day across engineering, product, design and client teams
- 3 to 5 team calendars to cross-check before anything is scheduled
- 30 to 45 minutes every morning to work out what the day holds and what to prepare
- Frequent double-bookings, because availability checks are manual
- Meeting action items that are discussed but rarely tracked
- 60+ emails a day, many of them invites, reschedules and follow-ups
- No single view of the day, so people switch between calendar, email, chat and docs

Together this costs roughly 2 hours a day per person. CalendarMate removes most of it with four agents behind one router: Briefing, Scheduler, Email and Follow-up. It proposes and drafts; people approve anything that changes a calendar or sends a message.

## Scope

Version 1 covers the router and four agents for PMs, TPMs and senior ICs, and never acts on its own: every change to a calendar or message goes through an approved proposal.

| Area | In scope for v1 | Out of scope or deferred |
| --- | --- | --- |
| Briefing | A daily brief and prep for a single meeting, built from calendar, mail, chat, docs and open action items; read-only | Briefs for other people or whole teams (deferred) |
| Scheduler | Finding slots across 3 to 5 calendars using free/busy, explaining conflicts, and booking, moving and answering invites after approval | Moving meetings the user does not organize; it drafts a message to the organizer instead |
| Email | Triage by urgency, thread summaries, reply drafts in the user's tone, and pulling out meeting requests and action items | Sending, archiving or deleting mail without approval |
| Follow-up | Capturing decisions and action items after meetings, one tracked list, and recap and nudge drafts | Replacing the team's project tracker; assigning work to people who did not agree to it |
| Router and channels | One chat entry point, event triggers (meeting ended, mail received, conflict) and scheduled runs (morning brief, evening sweep, weekly review) | Voice and other channels (deferred); general requests such as writing code or HR questions |
| Platform | One orchestration platform, n8n or Langflow, chosen at the platform decision on 27 Nov; both designs are drafted | Building a custom orchestration framework |
| Users | PMs, TPMs and senior ICs at ServionIQ | Other roles and company-wide access until general availability |

## Success criteria

The program succeeds if pilot users get back about half of the roughly 2 hours a day they lose today, without a single unapproved action. Baselines come from the problem statement; every target is a proposal, to be fixed at the 27 Nov decision once the baseline is measured.

| Measure | Baseline | Proposed target | How it is measured |
| --- | --- | --- | --- |
| Daily time on meeting logistics, scheduling and email triage | About 2 hours | At least 50% lower, about 1 hour | Weekly time diary from pilot users, checked against usage logs |
| Morning prep time | 30 to 45 minutes | Under 10 minutes | Pilot survey, plus when the brief is opened |
| Double-bookings and conflicts | "Frequent", not yet counted | Count them in discovery, then halve the rate | Calendar audit before and during the pilots |
| Meetings whose action items are captured | "Rarely tracked" | At least 80% of meetings with action items, within 24 hours | Follow-up list checked against a sample of meetings |
| Triage accuracy | None | At least 90% of threads marked urgent are rated correct by the user | User ratings on the daily brief |
| Safety | None | Zero actions without an approved proposal; zero messages to external people without approval | Audit log: every write traces to a proposal id |
| Adoption | None | At least 70% of invited pilot users active each week | Usage logs |
| Satisfaction | None | At least 80% of pilot users would keep using it | End-of-pilot survey |

## Risks

The three highest risks are about data and unintended actions, and the design answers each the same way: agents propose, people approve. Impact is my assessment; owners are roles to be named.

| # | Risk | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| 1 | Private mail or calendar content reaches the wrong person, or sits in logs | High | Free/busy only for other people's calendars; no content shared between users; short retention of run data; security review before Pilot A | Security lead |
| 2 | A malicious email, invite or transcript tricks an agent into acting | High | Content treated as data; every write needs an approved proposal; execute steps run the stored action, not model output; injection cases in the test set | Tech lead |
| 3 | A wrong booking, send or cancellation, especially with external attendees, costs trust | High | Propose and execute split; free/busy re-checked before any write; external attendees always confirmed; audit log | Tech lead |
| 4 | Users do not trust it or do not notice a benefit, so adoption stalls | High | Volunteer pilots; brief delivered in the chat tool people already use; weekly feedback; time saved shown to users | Product owner |
| 5 | Time saved is real but cannot be shown | Medium | Baseline measured in discovery; time diary plus usage logs; targets agreed on 27 Nov | Program lead |
| 6 | Access to 3 to 5 calendars per user, mail, chat and docs is slow to approve or rate-limited | Medium | Access requests start in discovery; a people directory for time zones and hours; begin with the user's own calendars | IT admin |
| 7 | No source for meeting transcripts or notes, so Follow-up has little to work from | Medium | Choose the source in discovery; accept pasted notes as a fallback | Product owner |
| 8 | Platform limits appear late, for example memory in queue mode, scheduling or shared storage access | Medium | Platform decided on 27 Nov; tested under realistic load in Pilot A; both designs are drafted | Tech lead |
| 9 | Model quality, cost or latency drifts | Medium | Structured outputs and low temperature; 15 to 20 test inputs per agent; run traces reviewed weekly; model chosen per agent | Tech lead |

## Stakeholders

The CTO sponsors the program, and PMs, TPMs and senior ICs are both its users and its pilot groups.

| Group | What they care about | Role in the program |
| --- | --- | --- |
| CTO | Getting back the roughly 2 hours a day lost to logistics | Sponsor: sets scope and approves each gate |
| PMs and TPMs | The heaviest meeting and email load | Primary users; pilot volunteers; weekly feedback |
| Senior ICs | The same load | Primary users; pilot volunteers |
| Engineering, product and design teams | Their calendars are checked and their meetings summarized | Affected: free/busy is visible to agents; they may receive nudges and recaps |
| Client teams and external attendees | Meetings with ServionIQ staff | Affected: contacted only after explicit user approval |
| Security and privacy | Handling of mail, calendar and meeting content | Reviews the design; approves the start of each pilot |
| IT and workspace admins | Access to calendar, mail, chat and docs, and the credentials | Grant access and manage credentials |
| Program lead and build team | Delivery to the plan | Run the weekly review and the gates; names to be assigned |

## Decision-making

Decisions sit at the lowest level that can make them, and anything that changes the scope, an agent's permissions or a gate goes to the CTO.

| Decision | Decides | Consulted | When |
| --- | --- | --- | --- |
| Scope changes; go or no-go at each gate | CTO | Program lead, Security | 27 Nov, 15 Jan, 26 Feb, 30 Apr |
| Platform: n8n or Langflow | Tech lead, confirmed by the CTO | IT admin, Security | By 27 Nov |
| Actions that may run without a per-action yes | CTO and Security together | Product owner | Before Pilot B |
| Access to calendars, mail, chat and docs | IT admin with Security | Tech lead | Before each pilot |
| Changes to agent prompts and routing rules | Product owner with Tech lead | Pilot users | Weekly, and only if the test set still passes |
| Pilot groups and rollout waves | Program lead with Product owner | Team leads | Before each stage |

A decision not settled at its level goes to the weekly program review, then to the CTO.

Standing rules for agent actions, taken from the design and not open to change without the CTO:

- Agents read and draft freely; anything another person can see needs an explicit yes first.
- Anything involving an external attendee always needs a yes, even if similar internal actions were pre-approved.
- Other people's calendars are read as free/busy only.
- Emails, invites, chat messages and transcripts are data, never instructions.
- Every write traces to one approved proposal.

## Rollout plan

Rollout widens in stages, and each stage unlocks more autonomy only after its gate passes. Gate criteria are the success-criteria targets once they are agreed.

| Stage | When (proposed) | Audience | Agents and autonomy | Gate to move on |
| --- | --- | --- | --- | --- |
| 0. Internal | 30 Nov to 18 Dec | Build team | Router, Briefing and Email on their own accounts; read and draft only | Test set passes, including injection cases |
| 1. Pilot A | 4 to 15 Jan | A small group of volunteer PMs and TPMs | Briefing and Email; read and draft only; no sends or bookings | Gate 1: triage accuracy and satisfaction on target; no privacy incident |
| 2. Pilot B | 1 to 26 Feb | A wider volunteer group, including senior ICs | All four agents; writes only after a per-action yes | Gate 2: zero unapproved actions; time-saved trend on target |
| 3. Org rollout | 1 Mar to 30 Apr | PMs, TPMs and senior ICs, team by team in waves | All four agents; pre-approved actions for internal-only meetings only if the CTO and Security agree | Gate 3: success criteria met; adoption on target |
| 4. Operate | From 30 Apr | All users | Monthly review of metrics, cost and incidents | Ongoing |

- Each wave gets a short onboarding and one feedback channel, which the weekly review reads.
- Rollback is per agent: switch off its execute step and it keeps proposing but cannot act.
- A privacy incident or an unapproved action pauses the rollout until the cause is fixed and the CTO agrees to resume.

## Open questions for the sponsor

- Which platform, n8n or Langflow? It is needed by 27 Nov.
- Who are the program lead, tech lead and product owner? The owners above are roles.
- How large are the pilot groups, and who volunteers?
- Do the proposed targets match what the CTO expects?
- Where do meeting transcripts or notes come from, and which tracker holds action items?
- Which actions, if any, may be pre-approved for internal-only meetings?
- What are the budget and team size? They were not given, so the plan assumes neither.
- Does ServionIQ take a year-end break between 21 Dec and 3 Jan?
