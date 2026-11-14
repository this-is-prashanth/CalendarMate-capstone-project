"""
=============================================================================
Fine-Tuning: CalendarMate (2 Models)
=============================================================================

WHAT THIS FILE DOES:
  1. Validates your training data files (checks JSONL format)
  2. Uploads them to OpenAI's servers
  3. Creates two fine-tuning jobs (one per agent, run in parallel)
  4. Waits for training to complete (15-40 minutes)
  5. Tests each fine-tuned model on a CalendarMate edge case
  6. Prints both fine-tuned model IDs (you paste these into n8n)

THE TWO MODELS:
  Model 1 - Intent Analyzer (training_data_intent.jsonl)
      Reads the user's request and outputs a structured analysis:
      INTENT (BRIEFING / SCHEDULING / EMAIL), whether required details are
      missing (attendee, day, time), whether the request is ambiguous or
      unusual (weekend, 6am), and what tools/checks are needed
      (availability check, conflict check, Meet link).
  Model 2 - Response Composer (training_data_responder.jsonl)
      Takes the user's request + the analysis + tool results and writes the
      final reply: asks clarifying questions instead of guessing, warns on
      conflicts and suggests alternatives, never invents meetings/emails.

  If your CalendarMate pipeline has only ONE agent, set JOBS below to a
  single entry and delete the other.

HOW TO USE:
  1. Put training_data_intent.jsonl and training_data_responder.jsonl in the
     same folder as this file (22 examples each are provided; add more of your
     own with different wording if you like)
  2. Set your OpenAI API key (either method below)
  3. Run: python fine_tune_calendarmate.py
  4. Wait for completion. Do NOT close the terminal.
  5. Copy the two model IDs printed at the end

IMPORTANT - AVOID TRAIN/TEST LEAKAGE:
  Do NOT put the exact T1-T12 test inputs into your training data. Write
  training examples with DIFFERENT wording, people, days and times that
  teach the same behaviours (e.g. "Set up a catch-up with marketing soon"
  for ambiguity instead of T4's wording). Otherwise your after-fine-tuning
  scores just show memorisation, not improvement.

PREREQUISITES:
  pip install openai python-dotenv

API KEY - Use EITHER method (both work):
  Method 1 (.env file): Create a .env file in this folder with:
      OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
  Method 2 (terminal): Set the environment variable before running:
      Windows PowerShell:  $env:OPENAI_API_KEY = "sk-proj-..."
      Mac/Linux:           export OPENAI_API_KEY="sk-proj-..."

MODELS:
  Base model for fine-tuning: gpt-4o-mini-2024-07-18
  Fine-tuned models will be named like:
    ft:gpt-4o-mini-2024-07-18:your-org:calendarmate-intent:XXXXX
    ft:gpt-4o-mini-2024-07-18:your-org:calendarmate-responder:XXXXX

COST:
  Roughly $1-3 total for both models (22 examples each, 3 epochs).

=============================================================================
"""

import sys
import os
import json
import time

# --------------------------------------------------------------------------
# Fix Windows emoji/unicode display issues
# --------------------------------------------------------------------------
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# --------------------------------------------------------------------------
# LOAD API KEY
# --------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI

if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OpenAI API key not found.")
    print("")
    print("Use EITHER method:")
    print("  Method 1: Create a .env file in this folder with:")
    print("            OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE")
    print("")
    print("  Method 2: Set it in your terminal before running:")
    print("            Windows PowerShell: $env:OPENAI_API_KEY = \"sk-proj-...\"")
    print("            Mac/Linux:          export OPENAI_API_KEY=\"sk-proj-...\"")
    sys.exit(1)

client = OpenAI()

# --------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------
BASE_MODEL = "gpt-4o-mini-2024-07-18"
N_EPOCHS = 3

# One entry per fine-tuned agent. Remove an entry if you only have one agent.
#   key        short id used in printouts
#   name       display name
#   file       training JSONL file
#   suffix     becomes part of the fine-tuned model name
#   n8n_node   which n8n node gets the model ID
#   test_system / test_input   sanity-check prompt sent after training
#   test_hint  what a correct response should look like
JOBS = [
    {
        "key": "intent",
        "name": "Intent Analyzer",
        "file": "training_data_intent.jsonl",
        "suffix": "calendarmate-intent",
        "n8n_node": "Intent LLM",
        "test_system": "You are the CalendarMate intent analyzer. Given the user's message and today's date, extract structured data. Classify INTENT as BRIEFING, SCHEDULING or EMAIL. Resolve relative dates (today, tomorrow, next Monday) against today's date. List MISSING_INFO (attendee, day, time) and set NEEDS_CLARIFICATION to YES if the request is ambiguous or incomplete. Flag weekends, unusual hours (before 07:00 or after 20:00) and dates in the past under UNUSUAL_FLAGS. Set CREATE_EVENT_ALLOWED to NO whenever information is missing, the request is unusual, or a conflict must be resolved first. Never invent attendees, times, meetings or emails the user did not mention.",
        # Test case modelled on T9 (missing attendee), different wording
        "test_input": "Today: Mon 09 Mar 2026 | Timezone: Asia/Kolkata\nMessage: Please put a call on my calendar for Wednesday, I can't remember who it's with.",
        "test_hint": "Expect: INTENT=SCHEDULING, MISSING_INFO includes attendee, NEEDS_CLARIFICATION=YES.",
    },
    {
        "key": "responder",
        "name": "Response Composer",
        "file": "training_data_responder.jsonl",
        "suffix": "calendarmate-responder",
        "n8n_node": "Response LLM",
        "test_system": "You are CalendarMate's response writer. Given the user's request, the analysis and the tool results, write the final reply. Use ONLY the tool results for meetings and emails; never invent meetings, emails, attendees or times. If information is missing or the request is unusual (weekend, very early or late hour, past date), ask a clarifying question or warn the user, and do NOT claim an event was created until details are confirmed. If a conflict exists, warn the user and suggest alternative times. When proposing a time to find, offer several slots. When an event is created, confirm title, date, time, attendees and the Google Meet link. If a tool failed or returned nothing, say so plainly.",
        # Test case modelled on T4/T6 (ambiguous + unusual), different wording
        "test_input": (
            "Today: Mon 09 Mar 2026 | Timezone: Asia/Kolkata\n"
            "User request: Set up a catch-up with the marketing folks sometime soon.\n\n"
            "Analysis:\nINTENT: SCHEDULING\nSUB_TYPE: AMBIGUOUS_REQUEST\nMISSING_INFO: [specific day, start time, specific attendees, duration]\n"
            "NEEDS_CLARIFICATION: YES\nCREATE_EVENT_ALLOWED: NO\nTOOLS_NEEDED: [none until clarified]\n\n"
            "Tool results:\nNo tools run. Waiting for the user to clarify."
        ),
        "test_hint": "Expect: asks which day/time/who; does NOT say the event was created.",
    },
]


# ==========================================================================
# STEP 1: VALIDATE TRAINING DATA
# ==========================================================================

def validate_jsonl(filepath):
    """Check that the training data file exists and has the correct format."""
    print(f"\n  Validating {filepath}...")
    if not os.path.exists(filepath):
        print(f"  ERROR: {filepath} not found in this folder.")
        sys.exit(1)

    count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  ERROR: Line {i} is not valid JSON ({e})")
                sys.exit(1)

            messages = data.get("messages")
            assert isinstance(messages, list) and messages, f"Line {i}: missing 'messages' list"
            roles = [m["role"] for m in messages]
            assert roles[0] == "system", f"Line {i}: first message must be 'system'"
            assert "user" in roles, f"Line {i}: must have a 'user' message"
            assert roles[-1] == "assistant", f"Line {i}: last message must be 'assistant'"
            assert all(m.get("content") for m in messages), f"Line {i}: empty message content"
            count += 1

    if count < 10:
        print(f"  WARNING: only {count} examples. OpenAI requires at least 10; 20-30 works better.")
    print(f"  PASSED - {count} training examples found")
    return count


# ==========================================================================
# STEP 2: UPLOAD AND CREATE FINE-TUNING JOB
# ==========================================================================

def upload_and_train(filepath, suffix):
    """Upload training data and create a fine-tuning job."""
    print(f"\n  Uploading {filepath}...")
    with open(filepath, "rb") as f:
        file_obj = client.files.create(file=f, purpose="fine-tune")
    print(f"  File ID: {file_obj.id}")

    print(f"  Creating fine-tuning job (suffix: {suffix})...")
    job = client.fine_tuning.jobs.create(
        training_file=file_obj.id,
        model=BASE_MODEL,
        hyperparameters={"n_epochs": N_EPOCHS},
        suffix=suffix,
    )
    print(f"  Job ID: {job.id}")
    return job.id


# ==========================================================================
# STEP 3: WAIT FOR COMPLETION
# ==========================================================================
# Polls all jobs together every 30 seconds so waiting on one model does not
# hide the status of the other.
# ==========================================================================

def wait_for_jobs(job_ids):
    """job_ids: {key: (display_name, job_id)} -> {key: model_id or None}"""
    print("\n  (This takes 15-40 minutes. Do NOT close this terminal.)\n")
    results = {}
    pending = dict(job_ids)

    while pending:
        for key, (name, job_id) in list(pending.items()):
            job = client.fine_tuning.jobs.retrieve(job_id)

            if job.status == "succeeded":
                print(f"  [{name}] COMPLETE - {job.fine_tuned_model}")
                results[key] = job.fine_tuned_model
                del pending[key]
            elif job.status in ("failed", "cancelled"):
                print(f"  [{name}] {job.status.upper()}")
                if getattr(job, "error", None):
                    print(f"  Error: {job.error}")
                results[key] = None
                del pending[key]
            else:
                trained = ""
                if getattr(job, "trained_tokens", None):
                    trained = f" | Tokens trained: {job.trained_tokens}"
                print(f"  [{name}] Status: {job.status}{trained}")

        if pending:
            time.sleep(30)

    return results


# ==========================================================================
# STEP 4: TEST THE FINE-TUNED MODEL
# ==========================================================================

def test_model(model_id, name, system_prompt, test_input, hint):
    """Send a test input to the fine-tuned model and print the response."""
    print(f"\n  Testing {name}...")
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": test_input},
        ],
    )
    output = response.choices[0].message.content
    print(f"  Test input: '{test_input[:80]}...'")
    print(f"  {hint}")
    print("  Response (first 500 chars):")
    print(f"  {'-' * 50}")
    for line in output[:500].split("\n"):
        print(f"  {line}")
    print(f"  {'-' * 50}")


# ==========================================================================
# MAIN
# ==========================================================================

def main():
    print("=" * 60)
    print(f"FINE-TUNING: CalendarMate ({len(JOBS)} Models)")
    print(f"Base model: {BASE_MODEL}")
    print("=" * 60)

    # --- Validate and launch every job ---
    job_ids = {}
    for n, job in enumerate(JOBS, 1):
        print("\n" + "-" * 60)
        print(f"MODEL {n}: {job['name']}")
        print("-" * 60)
        validate_jsonl(job["file"])
        job_id = upload_and_train(job["file"], job["suffix"])
        job_ids[job["key"]] = (job["name"], job_id)

    # --- Wait for all jobs ---
    print("\n" + "=" * 60)
    print("WAITING FOR ALL JOBS (running in parallel on OpenAI)")
    print("=" * 60)
    models = wait_for_jobs(job_ids)

    # --- Sanity-test each model ---
    for job in JOBS:
        model_id = models.get(job["key"])
        if model_id:
            test_model(
                model_id, job["name"],
                job["test_system"], job["test_input"], job["test_hint"],
            )

    # --- Print results ---
    print("\n" + "=" * 60)
    print("RESULTS - COPY THESE MODEL IDs")
    print("=" * 60)
    for job in JOBS:
        model_id = models.get(job["key"])
        if model_id:
            print(f"\n  {job['name']} model ID:")
            print(f"  {model_id}")
            print(f"  --> Paste into '{job['n8n_node']}' node in n8n")
        else:
            print(f"\n  {job['name']}: FAILED - check the error above and your training file")

    # --- Next steps ---
    print(f"\n{'=' * 60}")
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Open your CalendarMate n8n workflow")
    for i, job in enumerate(JOBS, 2):
        print(f"{i}. Click '{job['n8n_node']}' node -> change model to the {job['name']} ID above")
    step = len(JOBS) + 2
    print(f"{step}. Save workflow")
    print(f"{step + 1}. Run the same 12 test inputs (T1-T12) again")
    print(f"{step + 2}. Paste new outputs into test_calendarmate_pipeline.py")
    print(f"{step + 3}. Run: python test_calendarmate_pipeline.py")
    print(f"{step + 4}. Compare before vs after scores")


if __name__ == "__main__":
    main()
