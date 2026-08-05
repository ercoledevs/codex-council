# Normalized check excerpts

These blocks preserve the command, named cases, totals, and observed result.
They are not byte-for-byte process stdout, and original exit-code telemetry was
not retained.

## Plain arm

```text
node --test test/state-codec.test.js
node --check app.js
node --check state-codec.js
node --check e2e/incident-board.spec.js

✔ normalizes missing and invalid state
✔ decodes URL encoding and rejects unknown statuses
✔ encodes only non-default values
✔ round-trips arbitrary query text
tests 4
pass 4
fail 0
```

## Hyper arm

```text
node --test
node --check app.js
node --check state-codec.js
node --check e2e/browser.cjs

✔ normalizes defaults and accepts only known statuses
✔ decodes URL state and uses the first duplicate value
✔ encodes only non-default values in canonical order
✔ round-trips unicode and reserved query characters
tests 4
pass 4
fail 0
```

The browser command was not run. Browser claims remain `UNKNOWN`.

## Published patch replay

Both saved patches passed `git apply --check`, applied cleanly to fresh baseline
copies, and reproduced their 4/4 codec test results.

## Published evidence verification · 2026-07-24

The repository evidence test copied the shipped baseline into fresh temporary
directories, verified task/baseline SHA-256 values, ran `git apply --check`,
applied both patches, reran each codec suite, and checked `app.js` plus
`state-codec.js` syntax. The test exited successfully:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_docs.DocsTests.test_evidence_lab_records_are_replayable_and_honest
```

The browser harness was still excluded. Browser behavior remains `UNKNOWN`.
