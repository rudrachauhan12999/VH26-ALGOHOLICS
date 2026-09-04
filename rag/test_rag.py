"""
test_rag.py

Demonstrates every mandatory scenario for the RAG troubleshooting system.
Run with:

    python -m rag.demo.build_demo_data   # generate demo PDFs (once)
    python -m rag.ingest_manuals         # build the vector index (once)
    python rag/test_rag.py               # run this test script

Each test prints the query, the resulting status, and the full JSON
response, then asserts the expected status so a broken pipeline fails
loudly instead of silently.
"""

import json
import sys

from rag.pipeline import troubleshoot
from rag.vectorstore.vector_store import VectorStore


def _print_result(title: str, result: dict):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
    print(json.dumps(result, indent=2))


def _assert_status(result: dict, expected: str, label: str):
    actual = result.get("status")
    ok = actual == expected
    marker = "PASS" if ok else "FAIL"
    print(f"[{marker}] {label}: expected status='{expected}', got '{actual}'")
    return ok


def main():
    if not VectorStore.exists_on_disk():
        print(
            "No vector index found. Run these first:\n"
            "  python -m rag.demo.build_demo_data\n"
            "  python -m rag.ingest_manuals",
            file=sys.stderr,
        )
        sys.exit(1)

    results = []

    # TEST 1: exact code + machine/model given -> success
    r1 = troubleshoot("E101", machine="Machine A", model="X200")
    _print_result("TEST 1: E101 on Machine A / X200", r1)
    results.append(_assert_status(r1, "success", "TEST 1"))
    if r1["status"] == "success":
        assert r1["answer"]["error_code"] == "E101"
        assert all(s["machine"] == "Machine A" for s in r1["answer"]["sources"])

    # TEST 2: same code, different machine -> different, correct answer
    r2 = troubleshoot("E101", machine="Machine B", model="H500")
    _print_result("TEST 2: E101 on Machine B / H500", r2)
    results.append(_assert_status(r2, "success", "TEST 2"))
    if r2["status"] == "success":
        assert all(s["machine"] == "Machine B" for s in r2["answer"]["sources"])

    # TEST 3: bare code, no machine/model -> ambiguous
    r3 = troubleshoot("E101")
    _print_result("TEST 3: bare E101, no machine/model", r3)
    results.append(_assert_status(r3, "ambiguous", "TEST 3"))
    if r3["status"] == "ambiguous":
        machines = {opt["machine"] for opt in r3["options"]}
        assert {"Machine A", "Machine B"}.issubset(machines)

    # TEST 4: natural language, machine mentioned in text -> success
    r4 = troubleshoot("Why is Machine A overheating?")
    _print_result("TEST 4: natural language question", r4)
    results.append(_assert_status(r4, "success", "TEST 4"))

    # TEST 5: unsupported query -> insufficient
    r5 = troubleshoot("My machine is making a weird clicking noise.")
    _print_result("TEST 5: unsupported query", r5)
    results.append(_assert_status(r5, "insufficient", "TEST 5"))

    # TEST 6: follow-up question using conversation memory
    conversation_id = "demo-conversation-1"
    first_turn = troubleshoot("E101 on Machine A", conversation_id=conversation_id)
    _print_result("TEST 6a: first turn establishing context", first_turn)
    results.append(_assert_status(first_turn, "success", "TEST 6a"))

    follow_up = troubleshoot("What if that doesn't fix it?", conversation_id=conversation_id)
    _print_result("TEST 6b: follow-up question", follow_up)
    # The follow-up has no code/machine/model of its own - it should reuse
    # the Machine A / E101 context from the first turn and still resolve to
    # a concrete (non-ambiguous) answer.
    results.append(_assert_status(follow_up, "success", "TEST 6b"))
    if follow_up["status"] == "success":
        assert all(s["machine"] == "Machine A" for s in follow_up["answer"]["sources"])

    print(f"\n{'=' * 70}")
    passed = sum(results)
    print(f"{passed}/{len(results)} test cases passed")
    print("=" * 70)

    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
