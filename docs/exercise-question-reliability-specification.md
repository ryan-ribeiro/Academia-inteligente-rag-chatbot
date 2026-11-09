# Exercise question reliability and source coverage

Status: implementation specification, not a delivery report. Canonical product
requirements remain in `docs/requirements.md`; this document does not approve
new sources, clinical rules, dependencies, or changes to the RAG contract.

## 1. Problem and objective

The client asks `Uma pergunta, como fazer supino corretamente?` in `/assistente`
and receives `Não encontrei fundamentação suficiente para esclarecer sua pergunta.
Consulte seu instrutor.` The intended outcome is an evidence-grounded explanation
when current, eligible material actually supports the requested exercise and
aspect, and an honest, useful limitation when it does not. It must work for
assigned and unassigned exercises, with relevant own onboarding considered.

Ownership is RF-18, especially CA-18.1–4 and CA-18.6–12, the shared RAG contract,
RN-05/16/23/29/30/31, RNF01/05/06 and DEC-08/18. RF-15/19 and EXT-CA-AI-02.5–8
remain boundaries for requests that actually generate or modify training; this
task does not expand them. Preserve the distinction between an informational
question and an explicit generation/change request, and the instructor approval
gate. Follow `docs/frontend-design.md` for any UI changes and use pt-BR for all
client-visible text.

## 2. Investigation findings and limits

Read-only inspection on 2026-11-09, using the database's UTC date, found:

1. Three persisted turns matching the reported question had
   `insufficient_evidence` and zero citations. This establishes the observed
   output, not why each individual attempt failed. The persisted record does
   not retain the full per-attempt retrieval or writer decision.
2. The approved catalogue had 67 indexed public passages from 20 sources; 65
   passages had an unexpired review deadline. Two passages from `nhs-balance`
   expired on 2026-11-07 and must remain filtered. Counts alone do not measure
   exercise coverage, clinical suitability, or relevance to a question.
3. `muyor-bench-press-2023-technique` is a reviewed, licensed, current passage
   describing the barbell bench-press procedure of a study in physically active
   adults. A prior read-only retrieval of the exact question returned it along
   with an anatomy passage. This shows retrieval can work, not that every
   production request returned the same result or that the source supports all
   variants or individual restrictions. Its DOI and limitations are canonical
   metadata; use the entry already recorded in `docs/requirements.md`.
4. Inspection of names, sections, and passages found that many matches are
   strength-programming, anatomy, clinical population or muscle-activation
   literature. The squat review describes knee outcomes and excludes knee
   pathology; it is not itself a step-by-step technique guide. References to
   deadlifts, rows or push-ups in a broad passage do not establish procedural
   coverage. The reviewed corpus has **not** been established as sufficient or
   specialized for all assigned or unassigned exercises.
5. `KnowledgeService.retrieve` uses bounded hybrid lexical/vector search and
   can mark matching passages `supported`; that status alone does not establish
   that a passage supports the requested movement, variant and execution step.
   `resolve_citations` validates retrieved IDs and conservatively downgrades
   empty citations. It does not validate semantic support for each claim.
6. The question path calls the writer and makes one reassessment when the writer
   supplies no citations. A second empty or unsupported result becomes the
   generic fallback. Existing tests simulate a successful second response, but
   do not prove reliable behavior of the deployed writer with representative
   history, real retrieval, unsupported questions or repeated runs. The latest
   visible logs showed successful provider calls, not their content; these logs
   cannot alone establish whether the writer omitted citations or declined support.
7. The prior synthetic execution did produce a cited answer, but also associated
   a fictitious knee complaint with bench press without demonstrated relevance.
   The subsequent prompt amendment is not proof that this cannot recur.

Do not infer a single root cause from these observations. An old stored fallback,
a fresh retrieval gap, an unrelated retrieved passage, writer abstention, an
empty/invalid citation, response validation and frontend presentation must be
distinguished using the tests and privacy-safe instrumentation below. A transport
replay may legitimately return its previously saved answer; a newly submitted
turn with a new request UUID must perform fresh retrieval.

## 3. Source discovery and coverage assessment

Before altering the corpus, prepare a versioned exercise/variant coverage matrix
based on the actual current exercise dictionary and a representative synthetic
sample of names in client-owned plans. Do not export client names, plan contents,
health details or chat transcripts. Group aliases, equipment and modalities while
preserving distinct variants (for example, supino reto com barra, com halteres,
inclinado and máquina). Include common strength, bodyweight, machine, cable,
flexibility and mobility movements, plus a deliberately unsupported exercise.
Do not treat the finite matrix as proof of coverage for every possible exercise.

For each candidate passage record: exercise and variant, relevant setup and
movement aspects actually supported, exact source and locator, population,
limitations, review owner/date/deadline, language, license and adaptation or
attribution requirements. Classify as `direct`, `partial`, `not_applicable`,
`expired` or `missing`, with reasons. Coverage requires content review, not a
keyword, similarity score, citation count, database label or writer assertion.
Report per-family denominators, named gaps and excluded material. Restriction
handling must not infer diagnosis, safety or individual suitability from a
population study or a stated symptom.

Examples for discovery, **not approved ingestion or professional endorsement**:

- [Muyor et al., bench press procedure](https://doi.org/10.5114/jhk/161468):
  already indexed, CC BY 4.0; one experimental barbell variant, not a universal
  tutorial or a prescription. Audit its exact cited content and population.
- [Squat biomechanics study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6050697/):
  reports CC BY 4.0 and examines variations; evaluate its actual text, version,
  applicability and exercise-specific limitations before deciding whether any
  passage can fill a gap. It does not automatically authorize a technique.
- [Resistance-training technique review](https://pmc.ncbi.nlm.nih.gov/articles/PMC10801605/):
  reports CC BY 4.0 but is a narrative review with exercise-specific evidence
  gaps; assess whether individual passages address execution, rather than dose
  or hypertrophy alone.
- [Exercise Delivery, University of Queensland](https://uq.pressbooks.pub/exercisedelivery/):
  its stated CC BY-NC-SA license is **not** permitted by the canonical contract.
  Retain as a discovery reference only; do not embed or send its content to the
  writer unless a separately approved license or authorization is obtained.

Record technical license/content review separately from professional judgment.
New material requires approved OGL-3.0, CC-BY-4.0 or CC-BY-SA-4.0 terms,
commercial reuse, attribution, dates, integrity/provenance and review deadlines.
Review exact text and third-party exceptions; do not assume a repository license
covers every asset. Review candidate instructions for correctness and applicability
with a qualified professional before claiming they are safe for a population.
No approval may be fabricated. Ingest only sources meeting the existing policy,
with reproducible acquisition and startup reconciliation. Report unsupported
exercises rather than silently broadening licenses or changing review gates.

## 4. Required correction behavior

### 4.1 Trace and routing

1. Derive the client from the authenticated subject, identify the current turn's
   intent and exercise/variant, and preserve explicit plan-generation/change
   routing and existing idempotency. Do not let previous messages override a
   clearly stated current question.
2. Perform mandatory approved hybrid retrieval before answering or clarifying.
   Ground any query expansion in the current question, safe aliases and relevant
   own plan context; do not add unrelated old exercises or another client's data.
   Preserve six-passage maximum, permission, license and freshness filters.
3. Add bounded, non-sensitive diagnostics that differentiate intent,
   retrieval status and eligible passage count, applicability outcome, writer
   result, missing/invalid citations, reassessment and final disposition. Do not
   log prompts, passages, identities, credentials, raw onboarding, chat, or model
   response text. A successful HTTP/provider call is not evidence of a good answer.

### 4.2 Applicability, writer and fallback

4. Before claiming support, distinguish evidence for the requested movement,
   variant and requested aspect from merely related background. Specify and test
   the selection/applicability method; retain provenance for every selected
   passage. Never turn a retrieval hit or a writer-selected ID into automatic
   proof of claim-level support. If identification is ambiguous, ask one focused
   question; if the available evidence is partial, state exactly what is missing.
5. Supply the writer only the bounded authorized context, relevant onboarding and
   eligible passages. The answer must explain the supported aspects directly,
   distinguish a study protocol from a universal instruction, avoid unsupported
   numerical angles/loads, and not invent diagnosis, safety, medication changes,
   individual suitability or an association between an unrelated health fact and
   the exercise. Do not present the model's analysis as the answer.
6. The writer must select actual supporting passage IDs. The backend resolves
   canonical metadata; it never auto-attaches a source to an unverified claim or
   accepts unknown IDs. If a writer omits a citation despite relevant evidence,
   allow one bounded reassessment on the same retrieved context. An explicit
   unsupported or ambiguous result stays an honest limitation or clarification;
   never force `supported` merely to avoid the fallback. Respect the existing
   retry budget and controlled timeout/error behavior.
7. Where evidence supports only a portion of the question, state the supported
   portion and the missing part without presenting unsupported advice as grounded.
   Differentiate true absence, expired material, technical unavailability,
   unresolved ambiguity and invalid model output in pt-BR. Do not fabricate
   `Fontes`. Unsupported exercises remain answerable as limitations rather than
   rejected because they do not appear in a plan.
8. Store the canonical response/citations and show the existing `Fontes` UI.
   The same UUID replays its saved response; a newly submitted question obtains
   a fresh result. Do not silently rewrite prior chat messages or alter any plan,
   proposal, onboarding, approval or history. Keep the 30-day retention policy.

## 5. Tests and acceptance

Use fake providers and embeddings for deterministic unit tests; no live external
service is required in the unit suite. Add or update tests for:

1. Exact report and paraphrases, with and without punctuation, accent/case
   variations, prior unrelated conversation, current/draft/historical/unassigned
   exercise and explicit generation/change commands. Confirm routing and fresh
   retrieval for new UUIDs, cached replay for the same UUID, and no plan mutation.
2. A source that describes the requested barbell bench press, one that mentions
   bench press only in a study abstract, unrelated anatomy, a different variant,
   expired material, and sources belonging to another client. Assert that only
   eligible, applicable content supports each substantive instruction, with
   canonical provenance. Source presence alone must not pass applicability.
3. A first writer response without citations followed by a correctly grounded
   answer; repeated omission; invalid/unretrieved IDs; a false supported claim;
   explicit writer abstention despite search matches; and a provider timeout.
   Assert bounded calls, no auto-citation, truthful final status, preserved user
   message on controlled failure and no ungrounded instructional answer.
4. Relevant and irrelevant onboarding restrictions, incomplete onboarding,
   correction in recent own chat, two-client isolation and sensitive-log capture.
   Assert no diagnosis, unrelated condition/exercise association, unnecessary
   medication disclosure, or inferred onboarding update.
5. No result, expired-only result, search outage, ambiguous variant and unknown
   exercise. Check distinct pt-BR feedback, valid `Fontes` rendering, accessible
   error/retry behavior and no false safety or universal-coverage claim.
6. Catalogue ingestion and idempotent restart, exact source/license/deadline
   filtering and revoked source removal; real isolated PostgreSQL/pgvector tests
   must exercise the actual hybrid query and tenant boundary without live AI.

In addition to unit and isolated PostgreSQL tests, run a separate, explicitly
labelled development probe against the actual deployment model and retrieval.
Use only synthetic clients/onboarding and disposable or rolled-back state; do not
write to a real client's conversation or training. Freeze and report multiple
repetitions of the exact reported question and paraphrases with/without history,
relevant/irrelevant restrictions, assigned/unassigned variants and unsupported
or expired evidence. Record source IDs, final status, non-sensitive reason codes,
response quality, elapsed time and failures. Verify that the explanation is
actually supported by the source, not merely accompanied by a valid citation.
Measure latency and memory; if the environment cannot safely run both models,
record the interruption and resource condition without presenting sequential
unloading or a single successful sample as proof of production reliability.

Completion requires the coverage matrix and source review, all applicable unit,
integration and frontend regressions passing, successful actual-path development
probe with honest limitations, and no unrelated modifications. Report exact
commands, results, known gaps, decisions and any required professional review.
The task does not commit or push unless explicitly requested.
