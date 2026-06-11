# Memory_System.md

# Purpose

Memory is the foundation of Donna.

Without memory, Donna is a chatbot.

With memory, Donna becomes a chief of staff.

Without memory:

Every conversation starts from zero.

With memory:

Donna continuously develops understanding.

The purpose of memory is not storage.

The purpose of memory is understanding.

Memory exists so Donna can:

* understand the user
* understand relationships
* understand goals
* understand commitments
* understand preferences
* understand context
* understand patterns
* understand history

The quality of Donna is directly proportional to the quality of its memory system.

---

# Core Principle

Most AI systems remember conversations.

Donna remembers lives.

The objective is not:

> What happened?

The objective is:

> What might matter later?

This distinction drives every memory decision.

---

# What Memory Is Not

Donna should NOT store everything.

Bad Memory:

* every email
* every message
* every click
* every calendar event
* every conversation

This creates:

* noise
* cost
* clutter
* poor retrieval

Donna should store meaning.

Not raw data.

---

# Memory Philosophy

Raw Data

↓

Observations

↓

Insights

↓

Understanding

↓

User Model

Memory should move upward through these layers.

---

# Memory Architecture

The memory system consists of four layers.

```text
Raw Information
↓
Working Memory
↓
Long-Term Memory
↓
User Operating System
```

---

# Layer 1: Raw Information

Source systems.

Examples:

* Gmail
* Calendar
* WhatsApp
* Flights
* Documents
* Bank
* Notes
* Calls

This information remains in source systems.

Donna does not duplicate everything.

Donna retrieves when needed.

---

# Layer 2: Working Memory

Purpose:

Current context.

Short-lived information.

Examples:

* active conversation
* current workflow
* current task
* current travel plans
* today's priorities

Working memory changes rapidly.

Retention:

Hours to days.

---

# Layer 3: Long-Term Memory

Purpose:

Store information that remains valuable over time.

Examples:

* preferences
* relationships
* goals
* commitments
* patterns

This is where Graphiti lives.

---

# Layer 4: User Operating System

Purpose:

Highest abstraction layer.

Examples:

* values family highly
* prefers speed over perfection
* highly proactive
* cost conscious

This is the distilled understanding of the user.

The User Operating System is the final output of the memory system.

---

# Memory Categories

All memories belong to categories.

---

## Preferences

Examples:

* Apple Music
* Aisle seats
* Grab Standard
* Morning meetings

Purpose:

Predict future choices.

---

## Relationships

Examples:

Mom

Co-founder

Investor

Friend

Professor

Purpose:

Understand people.

Not contacts.

Relationships.

---

## Goals

Examples:

* Raise funding
* Lose weight
* Get into YC

Purpose:

Prioritize correctly.

---

## Commitments

Examples:

* Send deck
* Reply to investor
* RSVP wedding

Purpose:

Track obligations.

---

## Patterns

Examples:

* Calls mom on birthdays
* Skips gym Fridays
* Replies quickly to investors

Purpose:

Understand behavior.

---

## Experiences

Examples:

* Thailand trip
* Previous startup
* Graduation

Purpose:

Provide historical context.

---

## Decisions

Examples:

* Chose Grab Standard
* Picked aisle seat
* Selected cheaper flight

Purpose:

Learn decision style.

---

## Active Watches

Examples:

* Tokyo Flights
* Investor Reply
* AWS Bill

Purpose:

Track ongoing situations.

---

# Memory Extraction

Memory should never be manually written.

Memory is extracted.

Every important event enters:

```text
Event
↓
Memory Extraction Engine
↓
Memory Candidate
↓
Validation
↓
Storage
```

---

# Example

Raw Event:

> Mom likes lilies.

Memory Extractor:

Category:
Relationship Preference

Memory:

Mom → likes lilies

Store.

---

# Another Example

Raw Event:

User books aisle seat 10 times.

Memory Extractor:

Observation:
Repeated preference

Memory:

Prefers aisle seats

Confidence: 0.96

Store.

---

# Memory Confidence

Every memory has confidence.

Nothing is absolute.

Example:

```json
{
  "memory": "Prefers Apple Music",
  "confidence": 0.91
}
```

---

Confidence increases when:

* confirmed
* repeated
* observed frequently

Confidence decreases when:

* contradicted
* outdated

---

# Memory Schema

Every memory should contain:

```json
{
  "memory_id": "",
  "category": "",
  "content": "",
  "confidence": 0,
  "source": "",
  "created_at": "",
  "updated_at": ""
}
```

---

# Relationship Memory Graph

Relationships are graph entities.

Example:

```text
Mom
├─ likes lilies
├─ birthday
├─ called at noon
└─ high importance
```

---

Example:

```text
Anirudh
├─ restaurant recommendations
├─ close friend
└─ weekly interaction
```

---

Relationships should be interconnected.

Not isolated notes.

---

# Commitment Memory

Commitments require special handling.

Example:

Investor email:

> Please send deck by Friday.

Memory:

Commitment:
Send deck by Friday

Status:
Open

Priority:
High

Owner:
User

Until completed, commitment remains active.

---

# Goal Memory

Goals are dynamic.

Example:

Goal:
Raise funding

Associated Memories:

* investor emails
* pitch decks
* meetings
* introductions

Memories should attach to goals.

---

# Pattern Memory

Patterns emerge over time.

Patterns are never explicitly stored by users.

Patterns are inferred.

Example:

Observed:

Calls Mom on birthdays.

Observed:

Calls Mom on Mother's Day.

Pattern:

Important family events trigger calls.

Store.

---

# Experience Memory

Experiences provide context.

Example:

Previous founder.

Previous internship.

University projects.

Travel history.

These memories influence future recommendations.

---

# Retrieval Philosophy

Storage is easy.

Retrieval is hard.

The memory system should optimize retrieval.

Not storage.

---

# Retrieval Rule

When an event occurs:

Retrieve only relevant memories.

Never load everything.

---

Example

Event:

Flight booking.

Retrieve:

* travel preferences
* airline preferences
* seat preferences

Do not retrieve:

* Spotify preferences
* gym history

---

# Context Assembly

Before Claude reasons:

Retrieve:

Goals

Preferences

Relationships

Patterns

Commitments

Relevant Watches

Then build context.

Then reason.

Memory should support reasoning.

Not overwhelm it.

---

# Memory Aging

Not all memories stay important forever.

Memory importance changes.

---

Examples

Temporary:

Current hotel booking

Current project

Current exam

Can expire.

---

Permanent:

Mom likes lilies

Prefers aisle seats

Usually calls parents

Should remain.

---

# Memory Decay

Confidence should naturally decay.

Example:

Preference learned 5 years ago.

No supporting evidence.

Confidence decreases.

The system remains adaptable.

---

# Memory Updating

Memories are not static.

Example:

User switches from Spotify to Apple Music.

Old Memory:

Spotify Preferred

Confidence decreases.

New Memory:

Apple Music Preferred

Confidence increases.

Memory evolves.

---

# Memory Conflict Resolution

Conflicting memories will occur.

Example:

Memory A:

Prefers aisle seat.

Confidence:
0.95

Memory B:

Recently booked window seat 5 times.

Confidence:
0.90

System should not delete.

System should reconcile.

Updated understanding:

Preference uncertain.

Needs more evidence.

---

# Memory Importance

Not all memories are equal.

Importance should be stored.

Example:

Mom birthday preference

Importance:
High

---

Example:

Favorite pizza topping

Importance:
Low

Importance influences retrieval.

---

# Active Memory Layer

Frequently used memories should remain accessible.

Examples:

Current goals

Current commitments

Important relationships

Current travel

Active watches

These should be retrievable quickly.

---

# Memory And The User Model

Memory feeds the User Model.

```text
Events
↓
Memory Extraction
↓
Memory Graph
↓
User Model Update
↓
Better Understanding
```

The User Model is built on memory.

---

# Success Criteria

The memory system is successful when:

Donna remembers things the user would otherwise forget.

Donna notices patterns the user never noticed.

Donna predicts preferences correctly.

Donna understands relationships accurately.

Donna retrieves relevant context consistently.

Donna becomes more useful with time.

---

# Long-Term Vision

The ultimate goal of memory is not recall.

The ultimate goal of memory is understanding.

The memory system should eventually allow Donna to answer:

* What matters to this user?
* What is this user trying to achieve?
* How does this user make decisions?
* Who matters most?
* What is likely to be forgotten?
* What should be prepared next?

When Donna can answer those questions reliably, the memory system is working.

Memory is not the product.

Understanding is the product.

Memory is how Donna gets there.
