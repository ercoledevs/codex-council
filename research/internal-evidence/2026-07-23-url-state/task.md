# Task

Make the dependency-free incident board shareable and resilient without
changing its visual language.

## Required behavior

- Hydrate the `query` and `status` filters from `?query=` and `?status=`.
- Update the current URL with `history.replaceState` after user changes, while
  omitting default/empty values.
- Reject unknown status values and recover to `all`.
- Browser back/forward (`popstate`) must restore controls and results.
- Reset must clear both filters and the URL.
- Announce result-count changes through an appropriate live region without
  making the initial page load noisy.
- Render incident content without assigning untrusted strings to `innerHTML`.
- Preserve keyboard focus and the current responsive layout.
- Add dependency-free unit tests for the state codec plus a real browser test
  for hydration, filtering, reset, history, keyboard access, console errors,
  and horizontal overflow at desktop and mobile widths.

## Verification

- `node --test`
- Browser test against a local HTTP server.
