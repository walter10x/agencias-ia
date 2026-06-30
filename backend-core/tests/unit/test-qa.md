# Test Plan: Módulo de Prospección Automática y Feedback

**Module:** `backend-core/app/` — Prospection (Lead + Feedback)
**Phase:** RED (TDD) — Tests written before implementation exists
**Files created:** 4 test files, 0 implementation files

---

## Critical (test first)

- [x] [TC-001] Given valid phone and client_id, when Lead() is created with defaults, then all fields are set correctly (status=new, source=whatsapp, score=0)
- [x] [TC-002] Given empty or whitespace phone, when Lead() is constructed, then ValueError("phone cannot be empty") is raised
- [x] [TC-003] Given a New lead, when mark_contacted() is called, then status becomes CONTACTED and last_contacted_at is set
- [x] [TC-004] Given a lead with score=80, when mark_not_interested() is called, then score becomes 0
- [x] [TC-005] Given a lead with score=90, when add_score(20) is called, then score caps at 100
- [x] [TC-006] Given a Feedback with rating=5, when constructed, then all defaults apply (comment='', lead_id=None)
- [x] [TC-007] Given rating=0 or rating=6, when Feedback() is constructed, then ValueError("Rating must be between 1 and 5") is raised

## Happy Path

### Lead Entity

- [x] [TC-008] Lead entity creation with all fields explicitly set
- [x] [TC-009] Lead accepts valid status string values (new, contacted, interested, not_interested, converted, archived)
- [x] [TC-010] Lead accepts score boundaries (0 and 100)
- [x] [TC-011] Lead accepts valid sources (whatsapp, webchat, telegram, manual, import)
- [x] [TC-012] Full pipeline transition: new → contacted → interested → converted
- [x] [TC-013] mark_interested() changes status and sets timestamp
- [x] [TC-014] mark_converted() sets score=100 and status=CONVERTED
- [x] [TC-015] archive() changes status to ARCHIVED
- [x] [TC-016] add_score(0) is a no-op
- [x] [TC-017] add_score(negative) decreases score
- [x] [TC-018] update_notes() changes notes and advances updated_at

### LeadStatus Enum

- [x] [TC-019] All 6 enum values match database CHECK constraint
- [x] [TC-020] valid_statuses() classmethod returns all values
- [x] [TC-021] Enum values are unique strings
- [x] [TC-022] Invalid string raises ValueError

### Lead Equality

- [x] [TC-023] Two leads with same id are equal (different attrs)
- [x] [TC-024] Two leads with different id are not equal
- [x] [TC-025] Lead not equal to non-Lead types
- [x] [TC-026] hash(lead) == hash(lead.id)

### Feedback Entity

- [x] [TC-027] Feedback creation with minimum data (rating only)
- [x] [TC-028] Feedback accepts all fields (id, client_id, lead_id, conversation_id, rating, comment)
- [x] [TC-029] Feedback accepts rating values 1, 3, 5
- [x] [TC-030] Feedback lead_id defaults to None
- [x] [TC-031] Feedback conversation_id defaults to None
- [x] [TC-032] Feedback accepts both lead_id and conversation_id as UUID
- [x] [TC-033] Feedback without lead (EC-28) creates successfully
- [x] [TC-034] Feedback comment defaults to empty string
- [x] [TC-035] Feedback equality based on id alone
- [x] [TC-036] Feedback hash is stable

### CreateLeadUseCase

- [x] [TC-037] Valid input → LeadOutput, save called, find_by_client_and_phone checked
- [x] [TC-038] Duplicate client_id + phone → returns existing lead (idempotent), save NOT called

### ListLeadsUseCase

- [x] [TC-039] Returns list[LeadOutput] + total count with pagination params
- [x] [TC-040] Filter by status='new' → only new leads returned

### UpdateLeadUseCase

- [x] [TC-041] Update only status → LeadOutput with new status, other fields unchanged
- [x] [TC-042] Update only score → LeadOutput with new score
- [x] [TC-043] Update only notes → LeadOutput with new notes
- [x] [TC-044] Update only name → LeadOutput with new name
- [x] [TC-045] Update status + score + notes simultaneously

### GetLeadStatsUseCase

- [x] [TC-046] Returns LeadStatsOutput with total, by_status, conversion_rate, new_today, avg_score

### SendProactiveMessageUseCase

- [x] [TC-047] Happy path: message sent, lead status updated to contacted
- [x] [TC-048] At exactly 99 sent today, one more message is allowed (passes rate limit)

### CreateFeedbackUseCase

- [x] [TC-049] Valid input → FeedbackOutput, save called
- [x] [TC-050] Without lead_id/conversation_id → success, optional fields are None
- [x] [TC-051] Only rating + comment → success

### ListFeedbackUseCase

- [x] [TC-052] Returns list[FeedbackOutput] + total count with pagination

### GetFeedbackStatsUseCase

- [x] [TC-053] Returns FeedbackStatsOutput with total, average_rating, rating_distribution
- [x] [TC-054] Rating distribution includes keys 1 through 5 even if zero

## Edge Cases & Errors

### Lead Entity — Validation

- [x] [TC-055] Whitespace-only phone raises ValueError
- [x] [TC-056] Invalid status string "deleted" raises ValueError
- [x] [TC-057] Score below 0 raises ValueError
- [x] [TC-058] Score above 100 raises ValueError
- [x] [TC-059] Invalid source "email" raises ValueError

### Feedback Entity — Validation

- [x] [TC-060] Rating 0 raises ValueError with "got 0" message
- [x] [TC-061] Rating 6 raises ValueError with "got 6" message
- [x] [TC-062] Negative rating raises ValueError

### CreateLeadUseCase — Errors

- [x] [TC-063] Empty client_id → InvalidLeadError (EC-01)
- [x] [TC-064] Whitespace-only client_id → InvalidLeadError
- [x] [TC-065] Empty phone → InvalidLeadError (EC-02)
- [x] [TC-066] Invalid source "email" → InvalidLeadError (EC-05)

### ListLeadsUseCase — Errors

- [x] [TC-067] Empty client_id → ValueError
- [x] [TC-068] Status filter with zero results → ([], 0) (EC-10)
- [x] [TC-069] Client with no leads → ([], 0) (EC-09)

### UpdateLeadUseCase — Errors

- [x] [TC-070] Non-UUID lead_id → LeadNotFoundError (EC-11)
- [x] [TC-071] Non-existent lead_id → LeadNotFoundError (EC-12)
- [x] [TC-072] Invalid status "deleted" → InvalidLeadError (EC-14)
- [x] [TC-073] Score < 0 → InvalidLeadError (EC-13)
- [x] [TC-074] Score > 100 → InvalidLeadError (EC-13)

### SendProactiveMessageUseCase — Errors

- [x] [TC-075] Daily limit (100) reached → ProactiveMessageLimitError (EC-16)
- [x] [TC-076] Lead not found → LeadNotFoundError (EC-17)
- [x] [TC-077] Invalid lead UUID → LeadNotFoundError before any checks
- [x] [TC-078] DAILY_LIMIT constant equals 100

### CreateFeedbackUseCase — Errors

- [x] [TC-079] Empty client_id → InvalidFeedbackError (EC-21)
- [x] [TC-080] Whitespace-only client_id → InvalidFeedbackError
- [x] [TC-081] Rating 0 → InvalidFeedbackError (EC-20)
- [x] [TC-082] Rating 6 → InvalidFeedbackError (EC-20)
- [x] [TC-083] Negative rating → InvalidFeedbackError

### ListFeedbackUseCase — Errors

- [x] [TC-084] Empty client_id → ValueError
- [x] [TC-085] Client with no feedback → ([], 0)

### GetFeedbackStatsUseCase — Errors

- [x] [TC-086] Client with no feedback → zeroed stats (total=0, avg=0.0, distribution all zeros)

---

## Test Files Created

| File | Tests | Coverage |
|------|-------|----------|
| `tests/unit/test_lead_entity.py` | 4 classes, ~32 tests | Lead entity, LeadStatus enum, transitions, score, notes, equality |
| `tests/unit/test_feedback_entity.py` | 5 classes, ~18 tests | Feedback entity, rating validation, optional fields, equality |
| `tests/unit/test_lead_use_cases.py` | 5 classes, ~28 tests | CreateLeadUC, ListLeadsUC, UpdateLeadUC, GetLeadStatsUC, SendProactiveMsgUC |
| `tests/unit/test_feedback_use_cases.py` | 3 classes, ~16 tests | CreateFeedbackUC, ListFeedbackUC, GetFeedbackStatsUC |

**Total: ~94 test functions across 4 files**

## Non-Existent Imports (RED phase — will fail until implementation)

```
app.domain.lead.entity              → Lead, LeadStatus
app.domain.feedback.entity          → Feedback
app.domain.lead.repository          → LeadRepository (ABC)
app.domain.feedback.repository      → FeedbackRepository (ABC)
app.domain.shared.errors            → InvalidLeadError, LeadNotFoundError,
                                       InvalidFeedbackError, ProactiveMessageLimitError
app.domain.channels.message_sender_port → MessageSenderPort
app.application.dtos                → CreateLeadInput, ListLeadsInput, UpdateLeadInput,
                                       GetLeadStatsInput, SendProactiveMessageInput,
                                       LeadOutput, LeadStatsOutput,
                                       CreateFeedbackInput, ListFeedbackInput,
                                       GetFeedbackStatsInput, FeedbackOutput,
                                       FeedbackStatsOutput
app.application.lead.create_lead    → CreateLeadUseCase
app.application.lead.list_leads     → ListLeadsUseCase
app.application.lead.update_lead    → UpdateLeadUseCase
app.application.lead.get_lead_stats → GetLeadStatsUseCase
app.application.lead.send_message   → SendProactiveMessageUseCase
app.application.feedback.create_feedback  → CreateFeedbackUseCase
app.application.feedback.list_feedback    → ListFeedbackUseCase
app.application.feedback.get_feedback_stats → GetFeedbackStatsUseCase
```
