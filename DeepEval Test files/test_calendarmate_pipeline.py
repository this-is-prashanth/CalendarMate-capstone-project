"""
=============================================================================
DeepEval Test Suite for CalendarMate Pipeline
=============================================================================

WHAT THIS FILE DOES:
  Evaluates your CalendarMate pipeline's outputs on the 12 baseline test cases
  (T1-T12) using gpt-4o as a judge. Each test case is scored against the
  "Expected Output Must Contain" rules from the assignment.

HOW TO USE:
  1. Run each of the 12 test inputs through your pipeline
  2. Paste each output into PIPELINE_OUTPUTS (SECTION 2)
  3. (Optional but recommended) Fill in GROUND_TRUTH (SECTION 2b) with the
     real calendar / inbox data your pipeline had access to, so the judge
     can catch invented meetings and emails.
  4. Run: python test_calendarmate_pipeline.py
  5. Save a screenshot of the results
  6. After improving the pipeline, repeat for a before/after comparison

PREREQUISITES:
  pip install deepeval openai python-dotenv

API KEY - Use EITHER method:
  Method 1 (.env file): OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
  Method 2 (terminal):
      Windows PowerShell:  $env:OPENAI_API_KEY = "sk-proj-..."
      Mac/Linux:           export OPENAI_API_KEY="sk-proj-..."

NOTE ON DATES:
  The suite assumes the test run date below (TODAY). If you run the tests on
  a different day, update TODAY and the date notes so the judge can verify
  that "tomorrow", "next Monday", "next Thursday" etc. resolve correctly.
=============================================================================
"""

import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OpenAI API key not found.")
    print("  Method 1: Create a .env file with OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE")
    print('  Method 2: $env:OPENAI_API_KEY = "sk-proj-..."  (PowerShell)')
    print('            export OPENAI_API_KEY="sk-proj-..."   (Mac/Linux)')
    sys.exit(1)

JUDGE_MODEL = "gpt-4o"

# ==========================================================================
# DATE CONTEXT (given to the judge so it can verify day resolution)
# ==========================================================================
TODAY = "Friday, November 13, 2026"
DATE_NOTES = (
    f"Today is {TODAY}. Therefore: 'tomorrow' = Saturday, Nov 14, 2026; "
    "'Sunday' = Nov 15, 2026; 'next Monday' = Mon, Nov 16, 2026; "
    "'this week' = the current work week around Nov 13 (and upcoming days "
    "the user plausibly means); 'next Thursday' = Thu, Nov 19, 2026."
)

# ==========================================================================
# SECTION 1: TEST CASES (T1 - T12)
# ==========================================================================
# category decides which metrics are applied:
#   briefing      -> T1, T2, T10, T12
#   scheduling    -> T3, T5, T11   (event creation / slot proposal)
#   clarification -> T4, T6, T9    (must NOT create an event; must ask/warn)
#   email         -> T7, T8
# ==========================================================================

TEST_CASES = {
    "T1": {
        "input": "What does my day look like today?",
        "type": "Briefing",
        "category": "briefing",
        "expected": (
            "List of today's meetings with times and attendees. Must mention "
            "any conflicts if they exist."
        ),
    },
    "T2": {
        "input": "Give me a summary of my meetings for tomorrow.",
        "type": "Briefing",
        "category": "briefing",
        "expected": (
            "Tomorrow's meetings listed with times. Must NOT invent meetings."
        ),
    },
    "T3": {
        "input": "Schedule a 30-minute meeting with sarah@company.com tomorrow at 2pm.",
        "type": "Scheduling",
        "category": "scheduling",
        "expected": (
            "Must check availability. Must create event with Google Meet link. "
            "Must confirm time and attendee."
        ),
    },
    "T4": {
        "input": "Set up a sync with the design team sometime this week.",
        "type": "Scheduling (ambiguous)",
        "category": "clarification",
        "expected": (
            "Must ask for clarification: which day, what time, who specifically. "
            "Must NOT create event without confirmation."
        ),
    },
    "T5": {
        "input": "Find a time for a 1-hour meeting with john@ext.com and lisa@ext.com next Monday.",
        "type": "Scheduling (multi-attendee)",
        "category": "scheduling",
        "expected": (
            "Must check availability for all participants. Must propose slots, "
            "not just pick one."
        ),
    },
    "T6": {
        "input": "Schedule something for Sunday at 6am.",
        "type": "Scheduling (edge case)",
        "category": "clarification",
        "expected": (
            "Must flag that this is a weekend and unusual hour. Should ask for "
            "confirmation or warn."
        ),
    },
    "T7": {
        "input": "Summarize my unread emails.",
        "type": "Email",
        "category": "email",
        "expected": (
            "Must group by urgency or topic. Must separate action-required from "
            "FYI. Must NOT invent email content."
        ),
    },
    "T8": {
        "input": "What emails need my attention today?",
        "type": "Email",
        "category": "email",
        "expected": (
            "Must identify action-required emails only. Must include sender and "
            "subject. Must NOT fabricate emails."
        ),
    },
    "T9": {
        "input": "Book a meeting but I forgot with whom.",
        "type": "Scheduling (missing info)",
        "category": "clarification",
        "expected": (
            "Must ask who the meeting is with. Must NOT create an event with "
            "missing attendee."
        ),
    },
    "T10": {
        "input": "Do I have any conflicts this week?",
        "type": "Briefing",
        "category": "briefing",
        "expected": (
            "Must check all week's events for overlapping times. Must list "
            "specific conflicts or confirm none exist."
        ),
    },
    "T11": {
        "input": "Schedule a meeting at the same time as my existing standup.",
        "type": "Scheduling (conflict)",
        "category": "scheduling",
        "expected": (
            "Must detect the conflict. Must warn user. Must suggest alternative "
            "times."
        ),
    },
    "T12": {
        "input": "What's happening next Thursday?",
        "type": "Briefing",
        "category": "briefing",
        "expected": (
            "Must show events for that specific day. Must NOT show wrong day's "
            "events."
        ),
    },
}


# ==========================================================================
# SECTION 2: YOUR PIPELINE OUTPUTS
# ==========================================================================
# >>> PASTE THE FULL CALENDARMATE RESPONSE FOR EACH TEST BELOW <<<
# Include everything the user would see (and, if you can, any tool actions
# such as "Created event: ... Meet link: ...").
# ==========================================================================

PIPELINE_OUTPUTS = {
    "T1": """Today — Saturday, 14 November
All times IST.

Next up: Meeting with Sarah, 2:00–2:30 PM — in about an hour.

Sarah’s RSVP is still pending.
No agenda or related prep material was found.
This is your only scheduled meeting today, with no calendar conflicts. After 2:30 PM, your calendar is clear through the end of your working day at 6:30 PM.

Open item: Your request to WorkNest for details about the Svc Info Developer II role has no visible reply. No deadline was found.

FYI: No urgent or due-today items surfaced in the mail and chat searches.""",
    "T2": """Tomorrow — Sunday, 15 November
All times IST.

You have one meeting scheduled:

2:00–3:00 PM — Engineering team meeting

Organizer: You
Attendees and RSVPs: Not available in the calendar details.
Preparation: No agenda or related materials found.
FYI: No conflicts were found on your checked calendar; the rest of the day is clear.""",
    "T3": """Meet with Sarah — tomorrow, Saturday, 14 November, 2:00–2:30 PM IST, with sarah@company.com. Your calendar is free, including 10-minute buffers. Proposal ID: 367-1
Shall I book it?

FYI: Sarah’s availability isn’t verified; nothing has been booked yet.
Booked your meeting with sarah@company.com for tomorrow, Saturday, 14 November, 2:00–2:30 PM IST.""",
    "T4": """Who should attend the design sync? Please share their names or email addresses.

This week has only the weekend left. Should I look for a 30-minute slot next week, starting Monday, 16 November, instead?

Nothing is booked yet.

prashanth.b2014@gmail.com and prashanthbabu86@gmail.com

Got the attendees: prashanth.b2014@gmail.com and prashanthbabu86@gmail.com.

Since only the weekend remains this week, may I look for a 30-minute slot next week, starting Monday, 16 November?

yes

Three options for a 30-minute design team sync, all in IST:

Monday, 16 November, 12:10–12:40 PM — 582-1
Tuesday, 17 November, 10:00–10:30 AM — 582-2
Wednesday, 18 November, 10:40–11:10 AM — 582-3
Which option should I book with prashanth.b2014@gmail.com and prashanthbabu86@gmail.com?

FYI: Nothing is booked; attendee availability still needs verification.

1

Approve or decline?

Booked Design team sync for Monday, 16 November, 12:10–12:40 PM IST with:

prashanth.b2014@gmail.com
prashanthbabu86@gmail.com""",
    "T5": """Your connected calendar is free for these 1-hour slots next Monday, 16 November (IST):

9:30–10:30 AM
12:10–1:10 PM
2:00–3:00 PM
Availability for prashanth.b2014@gmail.com couldn’t be checked because their calendar isn’t shared, so these are tentative options—not confirmed mutual availability.

FYI: No booking proposals were generated, and nothing has been booked or sent.""",
    "T6": """The scheduler rejected Sunday, 15 November at 6:00 AM IST because it’s outside working hours, despite your explicit request. Nothing was booked.

Alternative: Monday, 16 November, 12:10–12:40 PM IST — personal hold, proposal 541-1.
FYI: I used the default 30-minute duration. Would you like this alternative?""",
    "T7": """Unread email summary — past 24 hours
Reviewed 31 unread threads.

Priority items

Google security alert: n8n Cloud was granted account access. Verify it in Google Account security settings; revoke it if unexpected.
GitHub authorization: Git Credential Manager was authorized with gist, repo, and workflow permissions. Review if you don’t recognize it.
Great Learning application: Your Agentic AI for Leaders application is incomplete. The email says applications close today, but gives no exact cutoff—verify through the official portal if interested.
Other actions

Your Monday, 16 November, 9:30–10:30 AM IST meeting invitation is awaiting your RSVP.
A shared-calendar invitation offering free/busy visibility awaits your decision.
Optional: review a VAPS TECHNOSOFT DevOps opportunity.
FYI

HDFC statement available for account ending 2931.
Axis phone banking maintenance: 17 November, 2:00–4:30 AM IST.
Excalidraw Google sign-in notice and several career alerts.
17 promotional/newsletter threads were skipped.
Nothing was sent, marked read, archived, or deleted.""",
    "T8": """Three emails deserve attention today:

Google — n8n Cloud access: Verify you authorized it in your Google Account security settings. Revoke access if unfamiliar. This is an authorization notice, not proof of a breach.
GitHub — Git Credential Manager: Review the new authorization, which includes repository and workflow access. Revoke it if unexpected.
Great Learning — incomplete application: The sender claims applications close today. If you’re interested, verify the deadline and missing details through the official portal; no exact cutoff is given.
Also worth reviewing

Tomorrow’s class: Interview Kickstart Capstone Project Week 2, Sunday, 15 November, 9 AM–1 PM IST. Confirm your attendance plans.
Monday’s meeting: The 9:30–10:30 AM IST invitation still awaits your RSVP.
Calendar permissions: A calendar-access request and a free/busy sharing invitation need your decision.
FYI: No independently verified deadline today was found, and nothing was sent or changed.""",
    "T9": """Who should I invite? If you’re unsure, I can look through recent emails for the likely person.

prashanth.b2014@gmail.com

What day and time should I propose for the meeting with prashanth.b2014@gmail.com? I’ll use 30 minutes unless you prefer otherwise.

Friday, 20th Nov 2026, morning 11 AM

Meeting with prashanth.b2014@gmail.com — Friday, 20 November 2026, 11:00–11:30 AM IST. Proposal ID: 558-1.
Your calendar is free, including 10-minute buffers; the invitee’s availability is unconfirmed.

Reply 1 to approve booking and sending the invitation.

1

Approve or decline?

Booked the meeting with prashanth.b2014@gmail.com for Friday, 20 November 2026, 11:00–11:30 AM IST.""",
    "T10": """No conflicts this week (9–15 November) on your calendar:

0 overlapping meetings
0 violations of your 10-minute meeting buffer
Closest gap: Friday’s TPM meeting and Design team sync were exactly 10 minutes apart.
Upcoming: Meeting with Sarah today at 2:00–2:30 PM IST; Engineering team meeting tomorrow at 2:00–3:00 PM IST. Sarah’s RSVP is still pending.

FYI: Your newly booked 20 November meeting is next week and wasn’t included in this check.""",
    "T11": """I couldn’t find an event clearly titled “standup” through 22 November. What’s its calendar title, or its date and start time?

I’ll propose the meeting with prashanthbabu86@gmail.com at that same time, with the overlap intentional. Nothing is booked yet.""",
    "T12": """Next Thursday, 19 November, your calendar is clear—no events or conflicts were found.

FYI: This covers your calendar only; commitments outside it may not appear.""",
}


# ==========================================================================
# SECTION 2b: GROUND TRUTH (OPTIONAL BUT STRONGLY RECOMMENDED)
# ==========================================================================
# The judge cannot see your real calendar or inbox. If you paste the actual
# data here (e.g. a list of events for the day, or the unread emails), the
# judge can verify that the pipeline did not invent meetings/emails or miss
# real conflicts. Leave as "" to skip - the judge then checks only behavior
# and internal consistency.
#
# Example:
#   "T1": "Calendar for Fri Nov 13 2026: 09:30-10:00 Standup (team@co.com); "
#         "10:00-11:00 Design review (ana@co.com); 10:30-11:00 1:1 (bob@co.com)"
# ==========================================================================

GROUND_TRUTH = {
    "T1": "",
    "T2": "",
    "T3": "",
    "T4": "",
    "T5": "",
    "T6": "",
    "T7": "",
    "T8": "",
    "T9": "",
    "T10": "",
    "T11": "",
    "T12": "",
}


# ==========================================================================
# SECTION 3: EVALUATION METRICS
# ==========================================================================
# Scores range 0-1; >= 0.5 = PASS.
# ==========================================================================

_PARAMS = [
    LLMTestCaseParams.INPUT,
    LLMTestCaseParams.ACTUAL_OUTPUT,
    LLMTestCaseParams.EXPECTED_OUTPUT,
    LLMTestCaseParams.CONTEXT,
]

# METRIC 1 (ALL): Does the output satisfy the 'Expected Output Must Contain'?
requirements_met = GEval(
    name="Expected Output Requirements",
    criteria=(
        "EXPECTED_OUTPUT lists what a correct response MUST contain or MUST NOT "
        "do for this user request. Check every requirement and prohibition one "
        "by one against ACTUAL_OUTPUT. Every 'Must' item has to be clearly "
        "present; every 'Must NOT' item has to be clearly avoided. Missing or "
        "violated requirements lower the score sharply. All met = PASS. "
        f"{DATE_NOTES}"
    ),
    evaluation_params=_PARAMS,
    threshold=0.5,
    model=JUDGE_MODEL,
)

# METRIC 2 (BRIEFING): accuracy of calendar summaries
briefing_accuracy = GEval(
    name="Briefing Accuracy",
    criteria=(
        "The user asked for a calendar briefing or conflict check. Check that: "
        "1) Events are shown for the CORRECT day/range (see date notes). "
        "2) Each event includes a time (and attendees when the request is for a "
        "day overview). "
        "3) No meetings are invented - if CONTEXT has real calendar data, every "
        "listed event must appear in it and no real event may be silently "
        "omitted. "
        "4) Overlapping events are explicitly flagged as conflicts, or the "
        "output explicitly says there are none. "
        "5) If there are no events, the output says so instead of making some up. "
        f"Accurate and grounded = PASS. Invented or wrong-day events = FAIL. {DATE_NOTES}"
    ),
    evaluation_params=_PARAMS,
    threshold=0.5,
    model=JUDGE_MODEL,
)

# METRIC 3 (SCHEDULING): availability checks, event creation, alternatives
scheduling_correctness = GEval(
    name="Scheduling Correctness",
    criteria=(
        "The user asked CalendarMate to schedule or find a time for a meeting. "
        "Depending on the request, a correct response: "
        "1) Checks availability (for ALL named attendees) before committing. "
        "2) When a specific time is given and free, creates the event with a "
        "Google Meet link and confirms the time, duration and attendee(s). "
        "3) When asked to FIND a time, proposes multiple candidate slots rather "
        "than silently picking one. "
        "4) When the requested time conflicts with an existing event, detects "
        "the conflict, warns the user, and suggests alternative times instead "
        "of double-booking. "
        "5) Resolves dates correctly and does not invent attendees, events or "
        "availability not supported by CONTEXT or the request. "
        f"Correct and honest = PASS. Skipped checks or invented details = FAIL. {DATE_NOTES}"
    ),
    evaluation_params=_PARAMS,
    threshold=0.5,
    model=JUDGE_MODEL,
)

# METRIC 4 (CLARIFICATION): ambiguous / missing info / unusual-time requests
clarification_handling = GEval(
    name="Clarification Handling",
    criteria=(
        "The user request is ambiguous, missing required information, or "
        "unusual. A correct response: "
        "1) Does NOT create or claim to have created a calendar event without "
        "the missing information / user confirmation. "
        "2) Asks specific follow-up questions about what is missing (e.g. which "
        "day, what time, who exactly, who the meeting is with) or, for unusual "
        "requests, warns about it (e.g. weekend, very early hour) and asks for "
        "confirmation. "
        "3) Does NOT guess or invent attendees, times or details. "
        f"Asks/warns and holds off = PASS. Creates the event anyway = FAIL. {DATE_NOTES}"
    ),
    evaluation_params=_PARAMS,
    threshold=0.5,
    model=JUDGE_MODEL,
)

# METRIC 5 (EMAIL): grouping, triage, and no fabrication
email_grounding = GEval(
    name="Email Triage and Grounding",
    criteria=(
        "The user asked CalendarMate about their emails. A correct response: "
        "1) Does NOT fabricate emails, senders, subjects or content - if "
        "CONTEXT contains the real inbox, every email mentioned must exist in "
        "it. If there are no matching emails, it says so plainly. "
        "2) For a summary: groups emails by urgency or topic AND separates "
        "action-required items from FYI items. "
        "3) For 'what needs my attention': lists ONLY action-required emails "
        "and includes sender and subject for each. "
        "4) Summaries of content stay faithful to what the emails actually say. "
        "Grounded and well-organized = PASS. Fabricated emails = FAIL."
    ),
    evaluation_params=_PARAMS,
    threshold=0.5,
    model=JUDGE_MODEL,
)

# METRIC 6 (ALL): built-in relevancy
relevancy = AnswerRelevancyMetric(threshold=0.5, model=JUDGE_MODEL)

# Which metrics apply to which category (requirements_met + relevancy for all)
CATEGORY_METRICS = {
    "briefing": [requirements_met, briefing_accuracy, relevancy],
    "scheduling": [requirements_met, scheduling_correctness, relevancy],
    "clarification": [requirements_met, clarification_handling, relevancy],
    "email": [requirements_met, email_grounding, relevancy],
}

CATEGORY_TITLES = {
    "briefing": "BRIEFING TESTS (T1, T2, T10, T12)",
    "scheduling": "SCHEDULING TESTS (T3, T5, T11)",
    "clarification": "CLARIFICATION / EDGE-CASE TESTS (T4, T6, T9)",
    "email": "EMAIL TESTS (T7, T8)",
}


# ==========================================================================
# SECTION 4: RUN THE EVALUATION
# ==========================================================================

def build_test_case(tid, data):
    output = PIPELINE_OUTPUTS.get(tid, "")
    if not output or "PASTE" in output:
        return None
    truth = GROUND_TRUTH.get(tid, "").strip()
    context = [truth] if truth else [
        "No ground-truth calendar/inbox data provided. Judge only on required "
        "behavior, correct date handling, and internal consistency. Treat "
        "obviously generic or implausible specifics with suspicion."
    ]
    return LLMTestCase(
        input=f"[{data['type']}] {data['input']}",
        actual_output=output,
        expected_output=data["expected"],
        context=context,
        name=f"{tid} - {data['type']}",
    )


def run_evaluation():
    for category, title in CATEGORY_TITLES.items():
        print("\n" + "=" * 60)
        print(f"EVALUATING {title}")
        print("=" * 60)

        cases = []
        for tid, data in TEST_CASES.items():
            if data["category"] != category:
                continue
            case = build_test_case(tid, data)
            if case is None:
                print(f"  Skipping {tid} - output not pasted yet")
                continue
            cases.append(case)

        if cases:
            evaluate(test_cases=cases, metrics=CATEGORY_METRICS[category])
        else:
            print("  No outputs pasted yet for this group. Fill in SECTION 2.")

    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)
    print("\nWhat to look for:")
    print("  Briefing:      Briefing Accuracy (right day, no invented meetings, conflicts)")
    print("  Scheduling:    Scheduling Correctness (availability, Meet link, alternatives)")
    print("  Clarification: Clarification Handling (asks/warns, does NOT create event)")
    print("  Email:         Email Triage and Grounding (grouped, action vs FYI, no fabrication)")
    print("  All tests:     Expected Output Requirements + Answer Relevancy")
    print("\nSave a screenshot for before/after comparison.")


if __name__ == "__main__":
    print("=" * 60)
    print("CALENDARMATE - DeepEval Evaluation (T1-T12)")
    print("=" * 60)
    run_evaluation()
