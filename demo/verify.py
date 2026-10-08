#!/usr/bin/env python3
"""verify.py — DEMO harness for the bottle-fork ProofDeploy demonstration.

Runs the probes in demo/probes.json against two refs of bottle (buggy parent
and fixed commit), using a git worktree per ref and PYTHONPATH to select the
bottle under test. The adapter app (demo/app.py) always runs from THIS
checkout; only `import bottle` resolves to the worktree.

This is a demo stand-in for `proofdeploy verify` (WAL-58): no provisioning,
no isolation, no JSONL records. It exists so the diff -> probes -> verdicts
loop can be SEEN against a real historical bug.

Substitutions: ${NOW_HTTP_DATE} in probe headers is replaced with the current
time formatted as an HTTP date (so If-Modified-Since is always "fresh").

Usage: python3 demo/verify.py <buggy-ref> <fixed-ref>
Stdlib only.
"""
import email.utils
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

PORT = 8471
STARTUP_TIMEOUT = 15


def sh(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {(r.stderr or '')[:200]}")


def wait_ready(url, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def run_probe(probe, subs):
    req = probe["request"]
    headers = {k: (v.replace("${NOW_HTTP_DATE}", subs["NOW_HTTP_DATE"])
                   if isinstance(v, str) else v)
               for k, v in req.get("headers", {}).items()}
    r = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{req['path']}",
        headers=headers, method=req["method"])
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            status, raw = resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read().decode()
    exp = probe["expect"]
    problems = []
    if status != exp["status"]:
        problems.append(f"status: expected {exp['status']}, got {status}")
    if "contains" in exp and exp["contains"] not in raw:
        problems.append(f"body does not contain {exp['contains']!r}")
    if problems:
        return "FAIL", "; ".join(problems)
    return "PASS", f"status {status}, expectations held"


def verify_ref(repo, ref, probes):
    work = tempfile.mkdtemp(prefix="pd-bottle-")
    svc = None
    try:
        sh(["git", "worktree", "add", "--detach", work, ref], cwd=repo)
        env = dict(os.environ, PYTHONPATH=work)
        svc = subprocess.Popen(
            [sys.executable, os.path.join(repo, "demo", "app.py")],
            cwd=repo, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not wait_ready(f"http://127.0.0.1:{PORT}/health", STARTUP_TIMEOUT):
            return [("INCONCLUSIVE", "service never became ready")]
        subs = {"NOW_HTTP_DATE": email.utils.formatdate(time.time(), usegmt=True)}
        out = []
        for p in probes:
            verdict, evidence = run_probe(p, subs)
            out.append((verdict, p["id"], evidence))
        return out
    finally:
        if svc:
            svc.terminate()
        sh(["git", "worktree", "remove", "--force", work], cwd=repo)
        shutil.rmtree(work, ignore_errors=True)


def main(buggy, fixed):
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    probes = json.load(open(os.path.join(repo, "demo", "probes.json")))["probes"]
    overall = 0
    for label, ref in (("BUGGY ", buggy), ("FIXED ", fixed)):
        print(f"===== {label} ref: {ref} =====")
        results = verify_ref(repo, ref, probes)
        for verdict, pid, evidence in results:
            print(f"  [{verdict}] {pid}\n        {evidence}")
        failed = sum(1 for v, _, _ in results if v == "FAIL")
        if failed:
            print(f"  VERIFICATION FAILED — {failed} claim(s) broken\n")
            overall = 1
        else:
            print(f"  VERIFICATION PASSED — {len(results)}/{len(results)} probes green\n")
    return overall


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <buggy-ref> <fixed-ref>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
