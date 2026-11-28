## Cross-Language Porting

When `config.json:from_lang != to_lang`, **Phase 4 (Translate) runs in
two stages per function** — everything else in the loop is unchanged:
translate across language, verify, then accelerate.

```text
caller ({from_lang})
   │   Stage A — transitions/{from_lang}-to-{to_lang}.md
   │   translate fn → {to_lang} on CPU; verify vs original via interop
   ▼
{fn}_{to_lang}     ← caller selects this under USE_{TO_LANG}_TRANSLATION
  (dispatcher)       dispatcher selects only on USE_{FRAMEWORK}
   │
   ├──(USE_{FRAMEWORK} off)──> {fn}_{to_lang}_host  CPU body, never guarded
   │                                             (Stage B's reference)
   └──(USE_{FRAMEWORK} on)───> {fn}_{framework}
                                   Stage B — flavors/{to_lang}/{framework}/
```

Rules:

- **Stage A first, fully.** The transition file (Stage A1–A5) must
  build, numerically verify against the original (interop test),
  and commit before Stage B starts. Set
  `phases.language_translate: true`.
- **Stage A emits two symbols; never collapse them.**
  `{fn}_{to_lang}_host` is the translated CPU body and never carries
  a framework guard; `{fn}_{to_lang}` is a dispatcher that forwards
  to it. Stage B treats the **host symbol** as the original
  and puts its GPU guard in the dispatcher only. If the guard lands
  in the host body, or the dispatcher is used as the CPU reference,
  a GPU build runs the GPU in both slots: CPU-vs-GPU reads exactly
  0.0 and the Stage A regression check silently disappears.
- **The guard/reference gate is mandatory.** Before Stage B, and again
  after any Stage B guard or build-system edit, build and run the
  original-language interop path with `USE_{TO_LANG}_TRANSLATION=1` and
  `USE_{FRAMEWORK}=0` (the framework preprocessor symbol must be omitted).
  The run log must contain `NSIGHT_AI_PORT_LANG_EXEC: {fn}` and must not
  contain `NSIGHT_AI_PORT_FRAMEWORK_EXEC: {fn}`; either failure blocks the
  handoff. An unexplained exact `0.0` CPU-vs-GPU difference blocks
  verification: it is the run-time sign that the host body was guarded or
  the dispatcher was used as the CPU reference.
- **Two layered guards.** The original-language caller dispatches
  `USE_{TO_LANG}_TRANSLATION` (`from_lang` vs `to_lang`); the dispatcher
  dispatches `USE_{FRAMEWORK}` (CPU vs GPU). The full GPU build
  enables **both** (e.g. `USE_CPP_TRANSLATION=1 USE_CUDA=1`).
- **The original language is the source of truth.** Every round
  gates on the new CPU and GPU code agreeing with the **original**
  implementation. A CPU-vs-GPU difference is a diagnostic, never
  the gate.
- **Test executables have their `main` in the original language.**
  Every standalone test — Stage A and Stage B — is a `{from_lang}`
  program, calling the original directly and the candidate through
  the same interop shim the production call site uses. A test
  written in the target language bypasses that shim and cannot
  catch interop defects. See
  [verification guide](verification-guide.md#test-main-must-be-in-the-original-language).
- **Pair-specific gotchas live in the transition file.** Read them
  before Stage A.
- **Same-language ports skip Stage A entirely** (`phases.language_translate`
  stays `false`/ignored); Phase 4 is the single framework-pack flow.
