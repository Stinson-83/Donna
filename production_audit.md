# Production-Readiness Audit: FastAPI WhatsApp Backend

This document details a comprehensive production-readiness audit of the Donna WhatsApp backend, specifically evaluating the codebase against 31 critical scalability, reliability, distributed systems, and operational concerns.

## Part 1: Distributed Systems & Concurrency

### 1. In-memory task tracking may not work across multiple servers
* **Verification**: **Verified**. State is stored in global dictionaries (`_active_tasks`, `_pending_items`, `_sending_phase`, `_phone_locks`).
* **Location**: `api/main.py`, lines 67-70.
* **Failure Mode**: In a multi-server setup, User's message 1 goes to Server A, and message 2 goes to Server B. Both servers create independent locks and `donna_turn` tasks, causing duplicate concurrent AI runs and violating the cancel-and-restart invariant.
* **Severity**: **Critical**
* **Solution**: Replace in-memory dictionaries with a distributed state store (Redis). Use distributed locks (e.g., Redlock) and store `_pending_items` in Redis lists. Alternatively, use a queueing system with `user_id` partitioning to ensure sticky worker routing.

### 2. Pending merged messages lost during crash
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 238 `_pending_items[phone] = pending`.
* **Failure Mode**: While the original payloads are saved in the DB, the specific execution and merge state (e.g., knowing that 3 rapid messages should be processed as 1 combined payload) exists only in RAM. If the server crashes, the startup script replays all unacknowledged DB rows, triggering a massive wave of immediate independent executions rather than preserving the exact merged state.
* **Severity**: **High**
* **Solution**: Persist merge/batch state and active task metadata to a durable KV store (Redis) or use a durable orchestration engine (Temporal/Celery).

### 7. Race condition around `_sending_phase`
* **Verification**: **Verified**.
* **Location**: `api/main.py`, lines 235-249.
* **Failure Mode**: When `is_sending` is `True`, the `_dispatch` function executes the `else` block, which unconditionally spawns a *new* concurrent task (`asyncio.create_task`) without waiting for the sending phase to complete. This results in two parallel tasks for the same user running simultaneously.
* **Severity**: **High**
* **Solution**: Modify the lock behavior: if `is_sending` is active, the new message should be appended to the queue, and the system should yield, allowing the current task to finish before picking up the queued message.

### 14. In-memory lock structures grow without bound
* **Verification**: **Verified**.
* **Location**: `api/main.py`, lines 73-78 (`_lock_for`).
* **Failure Mode**: `_phone_locks` creates a new `asyncio.Lock` for every unique phone number ever seen. The locks are *never* deleted from the dictionary (the `finally` block on line 221 cleans up everything *except* `_phone_locks`). This constitutes a memory leak that grows with the number of unique users.
* **Severity**: **Medium**
* **Solution**: Implement a periodic cleanup task for idle locks or migrate lock management entirely to Redis with TTLs.

### 22. Distributed message ordering not guaranteed
* **Verification**: **Verified**.
* **Location**: FastAPI router and `_dispatch` handling.
* **Failure Mode**: Without sticky sessions, two sequential messages from a user might be processed by two different workers. If Worker B processes message 2 slightly faster than Worker A processes message 1, they are handled out of strict FIFO order.
* **Severity**: **High**
* **Solution**: Implement Kafka partitioned by `user_id` to guarantee strict FIFO ordering and sequential processing per user.

### 24. Memory usage continuously grows with active users
* **Verification**: **Verified**.
* **Location**: Global dictionaries (`api/main.py`).
* **Failure Mode**: In addition to `_phone_locks`, any hanging asyncio tasks (e.g., due to unhandled `CancelledError` edge cases) will permanently trap references in `_active_tasks` and `_pending_items`.
* **Severity**: **Medium**
* **Solution**: Move conversational state tracking to Redis with appropriate TTLs.

### 31. Architecture constrained by a single-process execution model
* **Verification**: **Verified**.
* **Location**: The entire `api/main.py` entrypoint.
* **Failure Mode**: One FastAPI process handles I/O (webhooks), DB operations, third-party API communication, and LLM processing on the same event loop. Under heavy load, CPU-bound parsing or network I/O stalls the event loop, causing health check failures and webhook timeouts.
* **Severity**: **High**
* **Solution**: Decompose into microservices: an Ingress API (FastAPI) that just enqueues events, and a Worker Service (Celery/Temporal) that pulls from queues to execute the AI pipeline.

---

## Part 2: Async Processing & Queueing

### 3. No worker queue; webhook executes AI processing directly
* **Verification**: **Verified**.
* **Location**: `api/main.py`, lines 408-451.
* **Failure Mode**: `await _dispatch()` is called synchronously within the HTTP handler. This creates an asyncio task directly in the event loop. 5,000 users = 5,000 tasks contending for the single event loop, leading to immediate system exhaustion.
* **Severity**: **Critical**
* **Solution**: The webhook should parse the payload, enqueue a job to SQS/Kafka/Redis, and return `200 OK` immediately. Background workers handle execution.

### 4. No backpressure mechanism
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 248.
* **Failure Mode**: `asyncio.create_task` has no bound. If LLM providers slow down (e.g., OpenAI latency increases), incoming tasks continue piling up without limit until the OS kills the process due to OOM.
* **Severity**: **High**
* **Solution**: Limit concurrency using a global `asyncio.Semaphore`, or rely on fixed-size worker thread/process pools via a dedicated queuing engine.

### 8. Startup replay creates a traffic storm
* **Verification**: **Verified**.
* **Location**: `api/main.py`, lines 252-280 (`_replay_queued_inbox`).
* **Failure Mode**: After a 1-hour outage, 100,000 queued messages are fetched and dispatched simultaneously upon startup, instantly exhausting connections and rate limits, causing an immediate secondary crash.
* **Severity**: **High**
* **Solution**: Implement throttled/paginated replay. Push failed items into a durable queue rather than processing them in a massive `for` loop on boot.

### 18. No prioritization mechanism
* **Verification**: **Verified**.
* **Location**: `api/main.py`. All tasks use the same asyncio scheduler.
* **Failure Mode**: Long-running workflows (e.g., 2-minute API scraping) consume the same thread-pool priority as simple "Hello" greetings, starving basic interactions of compute.
* **Severity**: **Low**
* **Solution**: Implement priority queues using Celery/RabbitMQ, routing rapid conversational turns to a high-priority queue and long-running tools to a background queue.

### 19. WhatsApp send failures lose outbound messages
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 207 (`await _wa.send_many`).
* **Failure Mode**: If a network failure occurs during `send_many`, an exception is caught, the task finishes, and the DB marks the turn as failed (line 219), but the outbound message is lost forever.
* **Severity**: **High**
* **Solution**: Create a durable outbound queue (Delivery Service). When `donna_turn` completes, enqueue the generated response. The Delivery Service polls the queue and applies exponential backoff for Meta API failures.

### 20. No dead-letter queue (DLQ)
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 219 (`mark_failed`).
* **Failure Mode**: Errors are simply updated to "failed" in Postgres. There is no automated re-processing workflow, alert trigger, or DLQ for systematic triage.
* **Severity**: **Low**
* **Solution**: Implement a standard DLQ pattern. Unrecoverable messages go to a DLQ partition for engineering review.

### 30. Webhook processing performs too much work before acknowledgment
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 437 (`await insert_inbound`).
* **Failure Mode**: The DB insert occurs *before* returning `200 OK` to Meta. Under heavy DB load, this insert may take >10 seconds, causing Meta to timeout the webhook and trigger unnecessary retries.
* **Severity**: **Medium**
* **Solution**: Acknowledge the webhook immediately after placing it in an ultra-fast in-memory/Redis queue, and handle the DB insert asynchronously.

---

## Part 3: State Management, Idempotency & Workflows

### 5. Meta webhook retries cause duplicate processing
* **Verification**: **Verified**.
* **Location**: `ingress/whatsapp.py`, lines 35-39.
* **Failure Mode**: `_SEEN_MSG_IDS` is an in-memory dictionary with a 60-second TTL. Meta's exponential backoff can span up to 24 hours. A retry at minute 5 will bypass this cache and result in duplicate AI responses.
* **Severity**: **High**
* **Solution**: Implement a distributed Redis cache using `SETNX` on `wa_message_id` with a 24-48 hour TTL.

### 6. Coroutine cancellation does not stop LLM billing
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 239 (`existing.cancel()`).
* **Failure Mode**: Standard asyncio cancellation terminates the local task and drops the HTTP connection, but does *not* notify the LLM provider. The user typing "H -> He -> Hello" creates 3 requests; 2 are cancelled locally, but OpenAI still processes and bills for all 3.
* **Severity**: **Medium**
* **Solution**: Implement a strict 1-3 second debounce delay before initiating the LLM call. Utilize API-specific cancellation endpoints (if available) when abandoning a request.

### 12. Long-running workflows don't fit cancel-and-restart
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 239.
* **Failure Mode**: A user asks the agent to perform a complex 2-minute booking process. 1 minute in, the user texts "Are you there?". The cancel-and-restart logic terminates the booking workflow entirely.
* **Severity**: **High**
* **Solution**: Decouple intent resolution from execution. Conversational turns happen instantly, while identified long-running workflows are dispatched to a separate workflow engine (e.g., Temporal) that ignores conversational interruptions unless explicitly asked to cancel.

### 13. External side effects cannot be undone after cancellation
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 213 (`except asyncio.CancelledError:`).
* **Failure Mode**: The agent triggers a tool that sends an email, and then a new user message arrives. The task is cancelled, but the email is already sent, resulting in state inconsistency.
* **Severity**: **Medium**
* **Solution**: Implement the Transactional Outbox pattern or a Two-Phase Commit framework. Tools should "propose" side-effects, which are only executed after the LLM completes generation and commits the turn.

### 15. Brain execution lacks timeout protection
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 172 (`await donna_turn(state)`).
* **Failure Mode**: If a downstream service inside `donna_turn` hangs, the task waits indefinitely, holding the `_phone_locks` mutex forever and freezing the user's pipeline.
* **Severity**: **High**
* **Solution**: Wrap `donna_turn` execution in `asyncio.wait_for(donna_turn(state), timeout=X)` to enforce a hard SLA.

### 17. Message merging generates excessively large prompts
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 86 (`combined = "\n".join(texts)`).
* **Failure Mode**: A user spamming 200 rapid messages will have them joined into a massive multi-page string, polluting the prompt and wasting context tokens.
* **Severity**: **Low**
* **Solution**: Introduce a maximum length limit or payload count for merging. Summarize or truncate merged payloads exceeding X tokens.

### 21. Crash replay processes stale messages
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 259 (`fetch_queued_by_phone()`).
* **Failure Mode**: After a prolonged outage (e.g., 24 hours), startup logic pulls all unacknowledged DB rows. Users receive immediate AI replies to day-old messages, leading to major confusion.
* **Severity**: **Medium**
* **Solution**: Apply an expiration threshold (e.g., drop messages older than 2 hours).

### 29. Long conversations require repeatedly loading large histories
* **Verification**: **Likely / Pending full runtime review**.
* **Failure Mode**: Long-lived daily user sessions will cause prompt context windows to grow indefinitely, increasing latency and API costs linearly with conversation length.
* **Severity**: **Medium**
* **Solution**: Implement rolling windows, conversation snapshotting, or dynamic memory summarization techniques.

---

## Part 4: Data & Infrastructure Reliability

### 10. Database write amplification
* **Verification**: **Verified**.
* **Location**: `api/main.py`, lines 108-151, 437.
* **Failure Mode**: Processing a single user message triggers 5 separate transactions (`insert_inbound`, `_save_user_message`, `_save_assistant_message`, `_backfill_assistant_wamid`, `mark_processed`). At 5,000 concurrent users, this is 25,000 DB transactions, which will severely bottleneck Postgres IOPS.
* **Severity**: **High**
* **Solution**: Batch these operations. For example, insert the user message and inbound wrapper in one transaction, and the assistant message and `mark_processed` in another.

### 16. Single database instance bottleneck
* **Verification**: **Verified**. Single `async_session` pool structure.
* **Failure Mode**: Even with batching, tens of thousands of active users will max out single-instance connection limits.
* **Severity**: **Medium**
* **Solution**: Introduce PgBouncer for connection pooling. Implement DB Read Replicas for analytics and use Partitioning on `chat_messages` by `user_id`.

### 28. Users can upload extremely large media files
* **Verification**: **Verified**.
* **Location**: `ingress/whatsapp.py`, line 290 (`dl.content`).
* **Failure Mode**: The code downloads media entirely into RAM. A user uploading a 200MB video forces the FastAPI process to allocate 200MB memory. A coordinated attack can quickly OOM the server.
* **Severity**: **High**
* **Solution**: Stream incoming media chunks directly to a temporary file on disk or immediately proxy it to an S3 bucket via streaming multi-part upload.

---

## Part 5: Operational Robustness

### 9. No user-level rate limiting
* **Verification**: **Verified**.
* **Location**: Globally absent.
* **Failure Mode**: A malicious script can send 100 messages a second via WhatsApp, consuming massive server CPU, DB IOPS, and potentially LLM API bandwidth.
* **Severity**: **Medium**
* **Solution**: Implement strict token-bucket rate limiting per phone number at the webhook ingress layer using Redis.

### 11. Observability is insufficient
* **Verification**: **Verified**.
* **Location**: Globally uses standard Python logging.
* **Failure Mode**: Unexplained latency spikes occur in production, and engineers cannot tell if the delay is in Meta's API, the DB, or OpenAI.
* **Severity**: **Medium**
* **Solution**: Integrate OpenTelemetry for distributed tracing, and Prometheus for RED (Rate, Errors, Duration) metrics.

### 23. Typing indicators flood WhatsApp APIs
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 447 (`asyncio.create_task(_wa.send_typing(...))`).
* **Failure Mode**: Under heavy traffic, 5,000 users trigger 5,000 unthrottled concurrent requests to Meta APIs just for typing indicators.
* **Severity**: **Low**
* **Solution**: Debounce typing indicators. Only send a typing indicator if one hasn't been sent for the user in the last X seconds.

### 25. No cost controls
* **Verification**: **Verified**.
* **Location**: Globally absent.
* **Failure Mode**: A single compromised or malicious user endlessly triggers expensive tools and large LLM context generations, racking up hundreds of dollars in API bills.
* **Severity**: **High**
* **Solution**: Implement a user quota system, tracking token expenditure daily per `user_id` and cutting off access upon limits.

### 26. No graceful degradation path
* **Verification**: **Verified**.
* **Location**: `api/main.py`, line 173.
* **Failure Mode**: If OpenAI/Claude suffers an outage, every single user is statically replied to with "hm, one sec" continually. The system effectively goes down.
* **Severity**: **Medium**
* **Solution**: Integrate fallback routing. If Claude fails, dynamically fall back to Gemini or OpenAI.

### 27. No circuit breaker for failing external services
* **Verification**: **Verified**.
* **Location**: Globally absent.
* **Failure Mode**: If an external API like Gmail or Meta completely fails, the system continues allowing requests to wait the full timeout (e.g., 30s) before failing, leading to severe worker exhaustion.
* **Severity**: **Medium**
* **Solution**: Utilize Circuit Breaker patterns. If 5 consecutive Meta requests fail, fast-fail subsequent requests for a few minutes.

---

## Phased Roadmap to Production Scale

**Current State**: MVP Scale (Single Process, In-Memory State)  
**Target State**: Production Scale (Microservices, Kafka/Redis, Durable Workflows)

### Phase 1: Stabilization & Memory Safety (Immediate Priority)
_Goal: Prevent catastrophic OOMs and single-server crashes._
1. **Concurrency Control (Issue 4, 15)**: Wrap LLM executions in `asyncio.Semaphore` and `asyncio.wait_for`.
2. **Memory Leak Fix (Issue 14, 24)**: Clean up `_phone_locks` or migrate them to Redis.
3. **Media Streaming (Issue 28)**: Refactor `_download_media` to stream large files to disk/S3 instead of memory.
4. **Idempotency (Issue 5)**: Move Meta webhook deduplication from an in-memory dictionary to Redis `SETNX`.

### Phase 2: Decoupling & Queueing (Short-Term Priority)
_Goal: Eliminate the single-process bottleneck and survive traffic spikes._
1. **Webhook Decoupling (Issue 3, 30, 31)**: Refactor `api/main.py` so the webhook only pushes to Redis/Kafka and returns `200 OK`. 
2. **Worker Pool Setup**: Implement background workers (e.g., Celery or dedicated `asyncio` worker processes) that consume from the queue.
3. **Distributed Locks & Merge (Issue 1, 2, 7, 22)**: Replace local `_phone_locks` with Redis Redlock. Ensure workers pull all pending messages for a user atomically.

### Phase 3: Infrastructure Resilience & Database Scaling (Medium-Term Priority)
_Goal: Ensure the database doesn't become the primary bottleneck._
1. **DB Write Batching (Issue 10)**: Consolidate the 5 DB transactions into a single atomic block per conversational turn.
2. **Connection Pooling (Issue 16)**: Implement PgBouncer.
3. **Cost Controls & Rate Limiting (Issue 9, 25)**: Deploy Redis-based token bucket rate limiting on the webhook ingress and implement a budget/quota layer before LLM execution.
4. **Debounce Optimization (Issue 6)**: Implement a 2-second debounce layer on the worker side to save LLM tokens on rapid user typing.

### Phase 4: Observability & Workflow Engines (Long-Term Priority)
_Goal: True distributed orchestration for advanced agentic behavior._
1. **Workflow Engine (Issue 12, 13)**: Integrate Temporal or an equivalent workflow engine to manage long-running tasks, decoupling them from the conversational "cancel-and-restart" chat loop.
2. **Observability (Issue 11)**: Add OpenTelemetry tracing to track latency across Meta -> Webhook -> Worker -> AI -> Delivery.
3. **Delivery Service & DLQ (Issue 19, 20)**: Implement a dedicated outbound messaging queue with automatic retry handling and a Dead Letter Queue for failed messages.
4. **Graceful Degradation (Issue 26, 27)**: Implement circuit breakers for Meta/OpenAI APIs and fallback LLM logic.

---

# Addendum: Findings Beyond the Original Scalability Scope

The 31 issues above are real and well-characterized, but the audit looked **only** at `api/main.py` and `ingress/whatsapp.py` through a distributed-systems lens. A full-repo pass surfaced a second class of problems the original audit never reached: **correctness bugs that break the app on every turn, security holes at the trust boundary, a broken migration chain, and direct contradictions with the project's own stated architecture (`CLAUDE.md`).** These are arguably higher priority than the scaling work, because several of them mean the system is not merely unscalable — it is **silently malfunctioning even at single-user scale.** Issues are numbered 32+ to continue the original list.

## Part 6: Correctness & Code Integrity (these break at single-user scale)

### 32. Terminator tool imports a module that does not exist — memory writes never fire
* **Verification**: **Verified.** `voice_synth.py` does not exist anywhere in the repo.
* **Location**: `donna_runtime/tools.py:1655-1657`. `send_burst` is the mandatory single terminator for **every** turn. After `send_burst_result()` populates the outbound buffer (`tool_logic.py:280-282`), line 1655 runs `from .voice_synth import maybe_synthesize_voice` — which raises `ModuleNotFoundError`. Because the exception is raised *before* line 1657, **`_fire_memory_hooks()` never executes.**
* **Failure Mode**: User-facing replies still deliver (buffer was already filled), so the breakage is invisible from the chat. But the post-turn memory hooks — `save_chat_messages`, `record_episode` (Supermemory), `ingest_to_graph` (Graphiti), `extract_user_facts` — **never run via this path.** Episodic memory, the knowledge graph, and the Living Profile silently stop being written. The SDK also receives a tool exception for the terminator on every turn, which can trip the double-terminator `PreToolUse` guard on any retry.
* **Severity**: **Critical**
* **Solution**: Restore/commit `voice_synth.py`, or guard the import (`try/except ImportError`) and move `_fire_memory_hooks()` ahead of it. Add a smoke test asserting `send_burst` returns cleanly and fires hooks.

### 33. Image and web tools import non-existent modules — guaranteed runtime crash on use
* **Verification**: **Verified.** `image_client.py`, `voice_intent.py`, and the entire `backend/web/` package are absent.
* **Location**: `donna_runtime/tools.py:1077` (`from .image_client import ...`), `:1279` (`from backend.web.search import agentic_search`), `:1375` (`from backend.web.pipeline import run_web_research`); `donna_runtime/context_builder.py:460` (`from .voice_intent import detect_voice_request`). All four wrapper tools (`image`, `web_search`, `agentic_web_search`, `research`) are registered in `DONNA_TOOLS` and advertised to the model, but invoking any of them raises `ModuleNotFoundError`.
* **Failure Mode**: The model is told these tools exist and will pick them; each call throws. Four of the ten advertised capabilities are non-functional. The repo as committed is incomplete, not just unscalable.
* **Severity**: **Critical**
* **Solution**: Either commit the missing modules or remove the tools from `DONNA_TOOLS` and their descriptions until they exist. Add an import-smoke test that imports every tool's dependency graph.

### 34. Broken Alembic migration chain — `alembic upgrade head` fails
* **Verification**: **Verified.** Files present: `0001, 0002, 0004, 0005`. `0004_integrations_and_emails.py:12` sets `down_revision = "0003"`, but **no `0003` revision exists.**
* **Location**: `backend/db/migrations/versions/`.
* **Failure Mode**: `alembic upgrade head` aborts with "Can't locate revision identified by '0003'". Migrations 0004/0005 (integrations, email_messages, proactive_pings) can never be applied via Alembic. The app limps along only because startup calls `db.migrations.create_tables()` (`Base.metadata.create_all`, `api/main.py:286`) instead — meaning **Alembic and `create_all` are two competing, divergent schema sources** and Alembic is dead on arrival.
* **Severity**: **High**
* **Solution**: Add the missing `0003` revision (or repoint `0004.down_revision` to `"0002"`). Decide on ONE schema authority — make `create_all` dev-only and run Alembic in deploy, or drop Alembic.

### 35. Schedule worker lock is not atomic — duplicate reminders under >1 worker
* **Verification**: Reported by subsystem review; consistent with read-modify-write pattern.
* **Location**: `backend/memory/jobs/schedule_worker.py` (lock check then separate `UPDATE ... status='running'`).
* **Failure Mode**: The "is it locked?" read and the claiming `UPDATE` are separate statements. Two reminder workers (the deploy topology explicitly runs a separate `reminders` role, and Railway can restart/overlap) can both pass the check and both fire the same `DonnaSchedule`, double-pinging the user. `bin/start.sh` runs this as its own process, so concurrency is the expected case, not the edge case.
* **Severity**: **Medium**
* **Solution**: Use `SELECT ... FOR UPDATE SKIP LOCKED` or a Postgres advisory lock to claim rows atomically, or an atomic `UPDATE ... WHERE status='pending' RETURNING`.

### 36. Procedural Rules (Tier 2) are synthesized but never retrieved
* **Verification**: Reported; `synthesis/procedural_rules_tier2.py` writes `ProceduralRule` rows but no live tool/context path reads Tier-2 rules into the loop.
* **Location**: `backend/memory/synthesis/procedural_rules_tier2.py`; no consumer in `donna_runtime/context_builder.py` or tools.
* **Failure Mode**: Dead investment — Haiku spend to author rules that never influence a turn. (Layer 4 of the "nine backends" is effectively write-only.)
* **Severity**: **Low**
* **Solution**: Wire a `list_rules`/context injection path, or stop synthesizing until consumed.

### 37. Outbound delivery has no retry, backoff, or idempotency key
* **Verification**: **Verified** by reading `delivery/whatsapp.py` `_post`/`send_many`.
* **Location**: `delivery/whatsapp.py` (single `httpx` POST, raises on ≥400, 10s timeout, no retry).
* **Failure Mode**: A 429/5xx from Meta drops the bubble permanently (overlaps Issue 19). A success-with-timed-out-response causes a resend on any higher-level retry because there is no idempotency key. `send_many` also fires bubbles with no pacing/rate awareness.
* **Severity**: **Medium**
* **Solution**: Add bounded exponential backoff for 429/5xx and a per-message idempotency key; centralize in the durable Delivery Service proposed in Issue 19.

## Part 7: Security (trust-boundary gaps the original audit did not cover)

### 38. WhatsApp webhook has NO payload signature verification
* **Verification**: **Verified.** No `X-Hub-Signature-256` / HMAC / app-secret check exists in `api/main.py` or `config.py`. (Note: the *Composio* webhook at `api/composio_webhook.py:61` is correctly HMAC-verified — so the inconsistency is glaring.)
* **Location**: `api/main.py:408` `POST /webhook`. The GET verify handler only checks the static `verify_token`; the POST handler trusts any well-formed JSON.
* **Failure Mode**: Anyone who learns the public webhook URL can POST forged inbound messages for **any** phone number, driving real LLM turns, real outbound WhatsApp sends to victims, memory writes, and API spend. This is a direct, unauthenticated path to the brain.
* **Severity**: **Critical**
* **Solution**: Verify `X-Hub-Signature-256 = HMAC-SHA256(app_secret, raw_body)` with `hmac.compare_digest` before parsing/dispatching. Reject on mismatch. Store the Meta App Secret as a required secret.

### 39. SSRF in media download and inbound URL enrichment
* **Verification**: **Verified** by reading the fetch paths.
* **Location**: `ingress/whatsapp.py:290-305` (`_download_media` GETs the `url` returned by Meta's media endpoint with no scheme/host validation, full body into RAM — also Issue 28); `ingress/node.py` URL-enrichment GETs up to 3 user-supplied URLs from message text.
* **Failure Mode**: The URL-enrichment path fetches attacker-controlled URLs server-side with no allow-list and no private-IP/`localhost`/`169.254.169.254`/`file:`/`data:` blocking — a classic SSRF into cloud metadata or internal services. Combined with #38 (forged inbound), this is fully unauthenticated.
* **Severity**: **High**
* **Solution**: Enforce `https` only, resolve and reject private/link-local/loopback ranges, pin media downloads to Meta CDN host patterns, cap response size, and stream to disk (ties into Issue 28).

### 40. Default public webhook verify token + plaintext secrets in compose
* **Verification**: **Verified.** `config.py` ships `whatsapp_verify_token` defaulting to a hardcoded public string; `docker-compose.yml` hardcodes `donna/donna` Postgres creds.
* **Location**: `config.py` (verify-token default), `docker-compose.yml` (DB password).
* **Failure Mode**: A deploy that forgets to override the verify token lets an attacker complete webhook (re)subscription. Compose creds are dev-only but invite copy-paste into prod.
* **Severity**: **Medium**
* **Solution**: Remove the default (fail closed if unset). Source all secrets from env/secret manager; never commit defaults that "work."

### 41. ProactivePing has no uniqueness constraint — quota bypass on webhook replay
* **Verification**: Reported; `record_ping` inserts unconditionally and quota is a `COUNT`.
* **Location**: `backend/integrations/proactive_rate_limit.py` (record/count), `proactive_email_trigger.py`.
* **Failure Mode**: Meta/Composio webhook replays (expected — Issue 5) re-trigger scoring and can double-count or, worse, re-fire a proactive ping, since dedup upstream is the in-memory 60s cache. No `(user_id, source, message_ref)` unique key.
* **Severity**: **Low**
* **Solution**: Unique constraint on `(user_id, source, message_ref)` and upsert; check dedup before scoring.

## Part 8: Architecture Fidelity & Cost (contradicts the project's own `CLAUDE.md`)

### 42. Main model is Sonnet 4.6, not Haiku 4.5 — violates a stated non-negotiable and the cost budget
* **Verification**: **Verified.** `donna_runtime/config.py:11-13` hardcodes `MODEL_NAME = "claude-sonnet-4-6"` for main, proactive, and upgrade models.
* **Location**: `donna_runtime/config.py:11-13`, consumed at `options.py:41`.
* **Failure Mode**: `CLAUDE.md` lists "Main model: Haiku 4.5. Sonnet only for specific upgrade cases" as a **non-negotiable**, and sets a per-turn budget of "<$0.01 on Haiku with caching." Running Sonnet on every reactive turn blows that budget by roughly an order of magnitude and contradicts the design. Either the config is wrong or the docs are stale — but they cannot both be right, and nothing routes Haiku for the default path.
* **Severity**: **Medium** (cost/architecture; not a crash)
* **Solution**: Set the default to Haiku 4.5 and reserve Sonnet for the declared upgrade cases, or amend `CLAUDE.md` and the cost-discipline section to reflect a deliberate Sonnet choice.

### 43. Prompt-cache prefix likely below Haiku's 4,096-token floor
* **Verification**: Reported in `docs/donna-context-and-eval-playbook.md`; not re-measured here.
* **Location**: System prompt assembly in `donna_runtime/prompt.py` + Living Profile injection.
* **Failure Mode**: The docs note the stable prefix (`_DONNA_CORE` ~1,400 tokens + profile) may not clear the 4,096-token minimum required for prompt caching to engage, so caching can **silently no-op** — every turn pays full input cost. This compounds #42. (Moot only if the Sonnet/Haiku decision changes the floor.)
* **Severity**: **Low**
* **Solution**: Measure the cached prefix token count in CI; pad/restructure to clear the floor, or accept and document no-cache cost.

### 44. Per-message hook/retrieval LLM fan-out strains the "no chained LLM calls" rule and the cost budget
* **Verification**: Reported across retrieval + hooks.
* **Location**: `retrieval/expansion.py` (query expansion, Haiku, per recall), `gates/graph_ingest_gate.py` (gate judgment, Haiku), `hooks/extract_user_facts.py` (fact extraction, Haiku) — plus language detection.
* **Failure Mode**: A single user message can trigger ~1–3 extra Haiku calls outside the BRAIN loop. `CLAUDE.md` says "No chained LLM calls outside the BRAIN loop unless inside a declared subagent." These are arguably the sanctioned hook/synthesis exceptions, but they are unmetered, hardcoded-timeout (8–12s), and multiply the per-turn cost the budget assumes. At scale they also have no shared cost ceiling (overlaps Issue 25).
* **Severity**: **Low**
* **Solution**: Meter and cap auxiliary LLM calls per turn/user; make timeouts configurable; confirm each is a declared exception or fold into the loop.

### 45. Proactive quiet-hours window is computed in UTC, not the user's timezone
* **Verification**: Reported; comment in code acknowledges the naivety.
* **Location**: `backend/integrations/proactive_rate_limit.py` (`now.time()` compared to user sleep/wake without `zoneinfo` conversion).
* **Failure Mode**: Quiet hours (e.g., 22:00–07:00) are checked against UTC, so any user not on UTC can be pinged mid-sleep or wrongly suppressed mid-day. `User.timezone` exists but is ignored here.
* **Severity**: **Medium**
* **Solution**: Convert `now` to the user's timezone via `zoneinfo` before the quiet-window comparison.

## Part 9: Repository Hygiene (non-runtime, but real)

### 46. README documents a different project; dashboard is a disconnected mock
* **Verification**: **Verified.** Top-level `README.md` describes "claw-code" (a Claude Code port), not Donna. `dashboard/web/lib/getPlan.ts` returns a hardcoded fixture (`return morningAaravPlan`) with no backend/DB calls.
* **Location**: `README.md`; `dashboard/web/lib/getPlan.ts`.
* **Failure Mode**: Onboarding/operability hazard — the entry-point docs do not describe the deployed system, and the "legible dashboard" promised in `CLAUDE.md` is a static prototype wired to no live data (IST/Mumbai time hardcoded in `lib/generator.ts`).
* **Severity**: **Low**
* **Solution**: Replace the README with Donna's actual run/deploy docs (the `docs/deploy*.md` content is accurate). Gate the dashboard behind a real `getPlan()` data source before claiming it as a feature.

Note: the original audit's Issue list is accurate, but one deployment sub-claim circulating in review is wrong — the `/health` endpoint **does** exist (`api/main.py:327`), matching `railway.json`. No action needed there.

---

## Remediation Log — Parts 6–8 (correctness / security / architecture)

The following were **fixed** in code (289 hermetic tests green after the changes):

| # | Title | Fix |
|---|-------|-----|
| 32 | Terminator imports missing `voice_synth` | `tools.py::send_burst` now guards the import in `try/except ImportError`; `_fire_memory_hooks()` runs regardless, so memory writes resume. |
| 33 | `image`/`web_search`/`agentic_web_search`/`research` import missing modules | Each tool guards its optional import and returns a graceful "not configured here" message instead of crashing; `context_builder._detect_voice_request` falls back to `False`. |
| 34 | Broken Alembic chain (missing `0003`) | `0004.down_revision` repointed `"0003"→"0002"`; docstring updated. `alembic upgrade head` now resolves. |
| 35 | Non-atomic schedule-worker lock | `schedule_worker.run_once` now claims rows with a single conditional `UPDATE ... WHERE fired=False AND (unlocked OR expired OR mine)` and proceeds only when `rowcount == 1`. |
| 37 | No outbound delivery retry | `WhatsAppChannel._post` retries 429/5xx and transport errors up to 3× with exponential backoff. |
| 38 | No WhatsApp webhook HMAC | `POST /webhook` now verifies `X-Hub-Signature-256` against `WHATSAPP_APP_SECRET` over the raw body (`hmac.compare_digest`); GET verify is `compare_digest` + fail-closed. |
| 39 | SSRF in URL enrichment + media download | New `ingress/net_guard.is_safe_public_url` (scheme + resolved-IP allowlist); `node.py` validates each URL and disables auto-redirects; media download validates the CDN URL and disables redirects. |
| 40 | Default public verify token | `whatsapp_verify_token` default removed (fail closed); added `whatsapp_app_secret`. |
| 41 | ProactivePing double-count on replay | `record_ping` skips inserting a duplicate fired ping for the same `(user_id, source, message_ref)`. |
| 42 | Wrong main model (Sonnet) | `donna_runtime/config.py` defaults to `claude-haiku-4-5-20251001` for main + proactive (env-overridable); Sonnet reserved for `UPGRADE_MODEL_NAME`. |
| 45 | Quiet hours computed in UTC | `proactive_rate_limit` converts `now` to the user's `User.timezone` via `zoneinfo` before the window check; added a Singapore-vs-UTC regression test. |

**Capability modules now implemented (closes the absence behind #32/#33):**

| Module / symbol | What it does | Degrades when |
|---|---|---|
| `donna_runtime/tool_logic.py::compose_image_prompt` | Deterministic (no-LLM) prompt builder; raises `ValueError` on empty intent | n/a |
| `donna_runtime/hooks.py::set_image_prompt_hash`/`get_image_prompt_hash` | Turn-scoped contextvar for `ImageToolEvent.prompt_hash` | n/a |
| `donna_runtime/image_client.py` | fal image generation → hosted URL; `ImageSafetyError`/`ImageUploadError`/`ImageProviderError` | `FAL_KEY` unset → `ImageProviderError` (tool → text) |
| `donna_runtime/voice_synth.py::maybe_synthesize_voice` | ElevenLabs TTS → WA media upload → replaces buffer with `AudioMessage`; always strips the marker | voice disabled / no key / TTS fail → text fallback |
| `donna_runtime/voice_intent.py::detect_voice_request` | Deterministic regex for explicit voice asks | n/a |
| `backend/web/search.py::search_web`/`agentic_search` | Exa `/search` + `/answer` (read-and-synthesize) | `EXA_API_KEY` unset → `status=degraded` |
| `backend/web/pipeline.py::run_web_research` | Deep research → `ResearchAnswer`/`ResearchTrace` | provider unconfigured → empty answer, `merged_count=0` |

Integration wiring also added: `_build_outbound` now maps `voice_response` → `VoiceResponseMarker` (the trigger `voice_synth` reads); `delivery/whatsapp.py` gained `upload_media()` and a `_media_ref()` helper so generated audio/images send by WA media id as well as public URL; config gained `FAL_KEY`/`FAL_IMAGE_MODEL`/`EXA_API_KEY`. 16 new unit tests; full suite 305 green. Features are live where their provider key is set, and degrade cleanly (never crash) where it is not.

**Still open (deferred — not pure correctness/security):** #36 (wire a Tier-2 rules retrieval path), #43 (measure/pad the prompt-cache prefix above the 4,096-token floor), #44 (meter + cap auxiliary per-turn LLM calls).
