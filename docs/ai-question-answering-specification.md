# AI chat question answering

## Scope

Implement RF-18/CA-18.9–12 in the existing client training chat. The canonical
requirements, shared RAG contract, RN-05, RN-16, RN-23, RN-29, RN-30,
RNF01, RNF05, RNF06 and DEC-08/DEC-18 remain applicable. Responses and
user-visible limitations are in Brazilian Portuguese.

## Behavior

1. Resolve the authenticated client and interpret the current turn. Detect
   direct and indirect requests for information, independent of question marks,
   case, accents and whitespace. Preserve the existing rules for explicit plan
   generation and draft changes, including requests phrased as questions.
2. For each question, query the approved PostgreSQL/pgvector hybrid retrieval
   service using the question and relevant client-owned context. The query must
   happen before an answer or clarification, including for an exercise already
   present in a training sheet. A transport replay of an already persisted
   request may return its existing response without repeating the query.
3. Consider the client's authoritative completed onboarding: goal and experience
   provide context; include limitations, complaints, health conditions and
   medications only when relevant to the question or safe response. Missing or
   incomplete onboarding is a limitation, not a reason to invent facts. Never
   include another client's data or unnecessary sensitive fields.
4. Answer exercise technique questions for exercises in the client's sheets and
   exercises never assigned to the client. Relevant saved exercise instructions
   may disambiguate the request; assignment is not a prerequisite. Do not assume
   an unassigned exercise is suitable. Ask a focused question if the movement or
   requested detail is ambiguous.
5. Ground substantive instructions in eligible retrieved passages. Validate
   canonical citations through the existing backend contract and display Fontes.
   Onboarding personalizes the answer but cannot substitute for evidence. When
   retrieval is unavailable, outdated or insufficient, disclose the limitation
   and do not fabricate technique, references, diagnosis or individualized dose.
6. Do not mutate current, approved or historical plans. A question alone does
   not authorize editing a proposal. Keep existing retention, idempotency and
   provider failure behavior.

The retriever's existing source eligibility, freshness, tenant filtering and
untrusted-passage rules apply. Do not add client questions or onboarding facts
to the shared corpus or sensitive data to logs. Use the existing provider-neutral
adapter and avoid new infrastructure or dependencies.

## Unit test acceptance matrix

Use fake retrieval and writing adapters; no live external service is required.
Tests should exercise observable service behavior and verify ordering and inputs.

- Recognize `Como fazer o exercício X?`, the same phrase without `?`, and
  `Me explique como fazer X`. A plain statement remains conversational. Explicit
  generation and draft-change commands retain their existing routing.
- Verify each question invokes retrieval before the writer, including when X is
  assigned and when it is not. A persisted request UUID replay must not create a
  duplicate answer or extra provider call.
- Cover X in the current sheet, in a proposal, in an older sheet, and absent
  from all sheets. Each case uses retrieval; the unassigned case is not rejected
  merely for being unassigned. Ambiguous names produce a focused clarification.
- Verify the writer receives relevant completed onboarding for the authenticated
  client, including a relevant limitation for an exercise question, and excludes
  unrelated sensitive fields. Missing or incomplete onboarding is not inferred.
- Use two clients to prove isolation of onboarding, sheet context, messages and
  client-scoped retrieved passages. Verify sensitive facts are not logged.
- Cover supported, empty, expired and unavailable retrieval. Assert truthful
  status and limitations, canonical citations only, and no fabricated answer
  presented as supported. Reject unknown citation IDs.
- Assert no question path alters plan content, revision, status or approval;
  cover provider failure and preservation of the client message on retry.

Run the focused new tests and existing chat, RAG, generation and adaptation
regressions. Review the diff and report test results and unresolved limitations.
These tests verify orchestration and contracts; they do not establish clinical
suitability or guarantee that every possible exercise is covered by the corpus.
