# CalendarMate: reflection and next steps

CalendarMate has not run on real data yet, so there are no production traces. The findings below come from walking the design through realistic cases on paper. Treat them as hypotheses to confirm against real traces in week 1.

## Trace findings

- **Silent failure on empty results.** If a tool returns nothing, the agent can answer as if everything is fine. Fix: an explicit "nothing found" and "could not check" state in every agent output.
- **Unknown availability can look like free time.** A calendar that errors out must count as unknown, never free. The slot finder is code, not the model, for this reason.
- **Approvals depended on chat memory.** A user saying "yes" to something the model no longer remembered would fail. Fix: proposals are stored with an id, and approval executes the stored action.
- **Raw email text reaches the model.** Invites, emails and transcripts can carry instructions. They are treated as data, and drafts are never sent without a yes.
- **Platform limits to verify.** No built-in scheduler found in Langflow. Simple Memory is not recommended by n8n for queue mode. Data tables are visible to everyone in the project.

## 2-week improvement plan

**Week 1: measure.** Log a trace for every run (input, tool calls, output, user decision). Build eval sets: 15 to 20 cases per agent, plus a 60-email mailbox fixture labelled by two PMs. Prototype on n8n first, since it has native scheduling and approval nodes.

**Week 2: fix and gate.** Run the evals, fix the top three failure classes, and re-run. Do a privacy and security review and a prompt-injection red-team. End with a go/no-go for Pilot A, matching the charter's 27 Nov platform decision.

## Privacy and security

- Collect the minimum: read headers and snippets first, fetch full bodies only when needed. Set a retention limit on traces and proposals.
- Confirm with the model provider: no training on our data, retention terms and a data processing agreement.
- Least-privilege credentials. A Gmail compose scope can send mail, so sending stays behind the execute workflow and a confirmation.
- Keep an audit log of every proposal and every approved action.
- Other people's calendars: free/busy only. Tell colleagues their availability is read. External attendees always need confirmation.
- Restrict who can open the data tables, because project members can see all rows.

## Rollout for 50 PMs/TPMs

1. **Wave 1 (5 champions).** Briefing and Scheduler only, daily feedback.
2. **Wave 2 (15 users).** Add Email and Follow-up. Fix what wave 1 found.
3. **Waves 3 and 4 (35 users, by team).** Only after the Gate 2 targets are met.

Before wave 3, check capacity: 50 users at 60+ emails is over 3,000 emails a day, and 8 to 14 meetings each is 400 to 700 meetings a day. Confirm API quotas and model cost. Each agent can be switched off on its own. One feedback channel, short training and a champion per team.

## Link to evaluation and fine-tuning

Traces plus each accept, edit or reject become labelled data. Evaluate first: use code checks where possible (double-booking, wrong timezone), an LLM judge for tone and summaries, and human review for a sample. Run the eval set on every prompt change as a regression gate. Fine-tune later and only narrowly, for example an urgent or not-urgent email classifier or draft tone. Never fine-tune slot finding or safety rules; those stay in code and prompts. Mail data used for training needs consent and redaction.
