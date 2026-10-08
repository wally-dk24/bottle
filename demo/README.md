# ProofDeploy demo on a real bug: bottle `static_file()` conditional requests

Fork of [bottlepy/bottle](https://github.com/bottlepy/bottle) demonstrating
ProofDeploy's loop — **diff → probes → verdicts** — against a genuine
historical bug, fixed upstream by bottle's own author in commit `b73bd1d`:

> fix: If-Modified-Since should be ignored if If-None-Match is present.

Per RFC 7232 sec 3.3, `If-Modified-Since` MUST be ignored whenever
`If-None-Match` is present. Before the fix, a request carrying a
*non-matching* ETag plus a fresh `If-Modified-Since` date fell through to
the date check and wrongly returned `304 Not Modified` — the client would
keep a stale copy thinking it was fresh.

## The demo

`demo/probes.json` holds three probes authored from the fix diff (following
the proofdeploy skill — expected results taken from RFC 7232 and the repo's
own `test_etag_overrides_ims`, never from the changed code):

1. `if-none-match-overrides-if-modified-since` — the bug: non-matching ETag
   + fresh IMS → **200** with the file (buggy code returns 304).
2. `non-matching-etag-alone-returns-200` — guard: INM path intact.
3. `old-ims-returns-200-with-file` — guard: IMS path intact.

`demo/verify.py` is an honest stand-in for `proofdeploy verify` (WAL-58):
it checks each ref into a temp worktree, starts the adapter with that ref's
`bottle.py` on `PYTHONPATH`, fires the probes, and renders verdicts.

```bash
# buggy parent vs fixed commit: the first probe FAILs on the buggy ref
python3 demo/verify.py b73bd1d^ b73bd1d
```

## Schema finding

The v0 probe schema requires `expect.json` or `expect.contains`
(status-only probes are rejected as "health checks"). For conditional-request
semantics the status code *is* the claim — a `304`-vs-`200` probe has no
meaningful body to assert on. Filed as feedback for the schema: allow
status-as-claim or add header expectations.

## Notes

- All demo work lives in this fork (`demo/`, `proofdeploy.yml`). Nothing has
  been opened against upstream bottlepy/bottle.
- The demonstrated bug is already fixed upstream; this replays history, it
  does not disclose anything new.
