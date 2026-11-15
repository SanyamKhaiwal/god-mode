"""Check the advisor's suggestions on sample prompts. Usage: python -I test_advisor.py"""
import importlib.util
import os
import uuid

spec = importlib.util.spec_from_file_location("advisor", os.path.expanduser("~/.claude/hubs/model-advisor.py"))
adv = importlib.util.module_from_spec(spec); spec.loader.exec_module(adv)

# (prompt, model, expected: "up" = suggest Opus, "down" = suggest Sonnet, None = silent)
CASES = [
    ("Rename the WORD constant to WORD_RE in tokenize.py", "opus", "down"),
    ("Fix the typo in the README installation section", "opus", "down"),
    ("Add a --keep-stopwords flag to the CLI and tests for it", "opus", "down"),
    ("Add an --explain flag that shows the BM25 score and matched terms for every result, json and text", "opus", "down"),
    ("Users report the download queue sometimes deadlocks under load when two spiders share a slot; find the race condition", "sonnet", "up"),
    ("Our login flow has a CSRF vulnerability, audit the authentication and fix it", "sonnet", "up"),
    ("The test suite is flaky, one test fails randomly and I have no idea why", "sonnet", "up"),
    ("Redesign the architecture of the plugin system so modules can be loaded lazily across all services", "sonnet", "up"),
    ("Physics solver loses precision at high speeds, floating-point drift in the tire model", "sonnet", "up"),
    ("Add a config file with precedence CLI > env > file and a search history with --rerun", "sonnet", None),
    ("Fix the IndexError when calling search_stack twice in one process", "sonnet", None),
    ("Add unit tests for the sentence_count function", "sonnet", "haiku"),
    ("Add an authentication middleware that checks the session cookie on the login route", "sonnet", None),
    ("Wire up the authorization header in the API client and add a crypto-price widget to the dashboard", "sonnet", None),
    ("Audit the app for SQL injection and XSS vulnerabilities", "sonnet", "up"),
    ("Rename the WORD constant to WORD_RE in tokenize.py", "sonnet", "haiku"),
    ("Fix the typo in the README installation section", "sonnet", "haiku"),
    ("Add a retry mechanism with exponential backoff to the downloader, with tests", "sonnet", None),
    ("Rename the WORD constant to WORD_RE in tokenize.py", "haiku", None),
    ("What does the _get_bm25 function do?", "sonnet", None),
    ("ok", "opus", None),
    ("/model sonnet", "opus", None),
    ("Find the race condition in the event bus", "opus", None),
    ("Trace how a request flows end-to-end from the spider to the downloader and explain every delay", "sonnet", "up"),
    ("Investigate why the cache returns stale rows after a reload", "sonnet", "up"),
]

ok = 0
for prompt, model, expected in CASES:
    sid = str(uuid.uuid4())
    msg = adv.advise({"prompt": prompt, "model": model, "session_id": sid})
    got = None if not msg else ("up" if "/model opus" in msg else "haiku" if "/model haiku" in msg else "down")
    good = got == expected
    ok += good
    print(f"{'PASS' if good else 'FAIL'}  [{model:6}] expected={str(expected):5} got={str(got):5}  {prompt[:70]}")
# once-per-session: second hard prompt in the same session stays silent
sid = str(uuid.uuid4())
first = adv.advise({"prompt": "Find the race condition in the scheduler", "model": "sonnet", "session_id": sid})
second = adv.advise({"prompt": "Now the deadlock in the worker pool", "model": "sonnet", "session_id": sid})
good = bool(first) and not second
ok += good
print(f"{'PASS' if good else 'FAIL'}  suggests at most once per session")
BUGCASES = [
    ("Fix the IndexError when calling search_stack twice in one process", True),
    ("Traceback: KeyError in core.py line 120 when the domain is missing, please fix", True),
    ("The test_parse test fails with AssertionError after my change to tokenize.py", True),
    ("the export endpoint crashes when the list is empty", True),
    ("ok lets do the remaining tests, I need a fix route with results", False),
    ("fix all the bugs you have mentioned and let me know once verified", False),
    ("is the bug in the advisor fixed? what is the current status", False),
    ("so we have a bug fix note firing on casual messages, whats the plan", False),
    ("whats the final verdict on our god-mode skill after the fix", False),
]
nb = 0
for prompt, expected in BUGCASES:
    got = bool(adv.bugfix_context(prompt))
    good = got == expected
    nb += good
    print(f"{'PASS' if good else 'FAIL'}  bugfix-note expected={expected!s:5} got={got!s:5}  {prompt[:70]}")
print(f"{ok + nb}/{len(CASES) + 1 + len(BUGCASES)}")
