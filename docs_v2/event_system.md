# Event_System.md

# Purpose

The Event System is the nervous system of Donna.

Everything that happens inside Donna begins as an event.

Every workflow.

Every notification.

Every insight.

Every memory.

Every recommendation.

Every action.

Every watcher update.

Everything starts with an event.

The Event System is responsible for detecting change and distributing awareness of that change throughout the system.

Without the Event System:

Donna is reactive.

With the Event System:

Donna becomes continuously aware.

---

# Core Principle

Donna should not continuously think.

Donna should continuously listen.

Most AI systems operate like:

```text
Think
Think
Think
Think
Think
```

This is expensive and inefficient.

Donna should operate like:

```text
Wait
↓
Something Happens
↓
React
```

This is event-driven architecture.

The system sleeps until something important occurs.

---

# What Is An Event?

An event is any meaningful change in state.

Examples:

* email received
* message received
* calendar updated
* flight delayed
* bill due
* birthday approaching
* user booked flight
* user skipped gym
* subscription renewing
* flight price dropped
* task completed

Events are facts.

Events are not interpretations.

Example:

Good Event:

```json
{
  "event_type": "flight_delayed",
  "delay_minutes": 120
}
```

Bad Event:

```json
{
  "event_type": "important_flight_delay"
}
```

Importance should be determined later.

Events should remain objective.

---

# Event Philosophy

Events answer:

> What happened?

Workflows answer:

> What process should run?

Agents answer:

> What does this mean?

Keeping these responsibilities separate is critical.

---

# High Level Architecture

```text
Connected Systems
        ↓
Triggers
        ↓
Event Producers
        ↓
Event Bus
        ↓
Workflow Engine
        ↓
Context Assembly
        ↓
Claude Agent
        ↓
Decision Engines
```

The Event System exists before reasoning begins.

---

# Event Sources

Donna receives events from many sources.

---

# Source Type 1: External Applications

Examples:

* Gmail
* Calendar
* WhatsApp
* Slack
* Notion
* Spotify
* Flights
* Banking
* Uber
* Grab

Events are generated through integrations.

Example:

New Email

↓

Event Generated

---

# Source Type 2: User Actions

Examples:

* approved recommendation
* rejected recommendation
* booked flight
* cancelled subscription
* completed task

User actions are extremely valuable.

They teach Donna.

---

# Source Type 3: Watchers

Watchers continuously monitor situations.

Examples:

Flight Watcher

Finance Watcher

Health Watcher

Relationship Watcher

Subscription Watcher

Travel Watcher

When something changes:

Watcher emits event.

---

Example:

Tokyo Flight Watch

Price Drops

↓

Price Change Event

---

# Source Type 4: Scheduler

The Scheduler itself produces events.

Example:

Reminder scheduled for tomorrow.

Tomorrow arrives.

↓

Scheduled Event Fired.

---

# Source Type 5: Internal Systems

Examples:

Memory Updated

Goal Created

Goal Completed

Preference Changed

Relationship Updated

These can trigger downstream workflows.

---

# Event Producers

Event Producers create events.

Examples:

Gmail Producer

Calendar Producer

WhatsApp Producer

Watcher Producer

Scheduler Producer

Memory Producer

Their job is simple:

Detect change.

Generate event.

Publish event.

Nothing more.

---

# Event Bus

The Event Bus is Donna's central nervous system.

Purpose:

Receive events.

Route events.

Distribute events.

The Event Bus does not:

* reason
* prioritize
* analyze
* make decisions

The Event Bus only transports information.

---

# Why The Event Bus Exists

Without an Event Bus:

```text
Gmail → Workflow

Calendar → Workflow

Flights → Workflow

Messages → Workflow
```

Everything becomes tightly coupled.

Difficult to scale.

Difficult to maintain.

---

With an Event Bus:

```text
Everything
↓
Event Bus
↓
Workflows
```

All systems communicate consistently.

---

# Event Structure

Every event should contain:

```json
{
  "event_id": "",
  "event_type": "",
  "source": "",
  "timestamp": "",
  "payload": {}
}
```

---

Example

```json
{
  "event_type": "new_email",
  "source": "gmail",
  "timestamp": "2026-06-11",
  "payload": {
    "sender": "investor@example.com"
  }
}
```

---

# Event Categories

Events should be categorized.

---

## Communication Events

Examples:

* email received
* message received
* missed call
* voicemail

---

## Calendar Events

Examples:

* event created
* event updated
* event cancelled

---

## Financial Events

Examples:

* bill due
* payment completed
* low balance

---

## Travel Events

Examples:

* flight booked
* flight delayed
* gate changed

---

## Health Events

Examples:

* meal logged
* workout skipped
* sleep tracked

---

## Relationship Events

Examples:

* birthday approaching
* anniversary approaching

---

## Goal Events

Examples:

* goal created
* milestone reached

---

## Subscription Events

Examples:

* renewal approaching
* usage dropped

---

## Watcher Events

Examples:

* threshold reached
* state changed

---

# Event Priority

Events themselves should not contain importance.

However they may contain urgency metadata.

Example:

```json
{
  "event_type": "flight_departing",
  "departure_time": "...",
  "hours_remaining": 2
}
```

Reasoning systems determine importance later.

---

# Event Lifecycle

Every event follows:

```text
Generated
↓
Published
↓
Received
↓
Workflow Started
↓
Processed
↓
Archived
```

---

# Event Persistence

Events should be stored.

Benefits:

* debugging
* replay
* auditing
* analytics

Example:

If a workflow fails:

Replay event.

No data loss.

---

# Event Replay

Donna should be able to replay events.

Example:

New workflow added.

Past events can be replayed.

New memories generated.

New insights discovered.

---

# Event Deduplication

Duplicate events happen.

Example:

Gmail sends same webhook twice.

System should identify duplicates.

Prevent duplicate workflows.

Prevent duplicate actions.

---

# Event Ordering

Events should preserve chronology.

Example:

Flight Booked

↓

Flight Delayed

↓

Flight Cancelled

Correct ordering matters.

Many workflows depend on sequence.

---

# Event Fan-Out

One event can trigger multiple workflows.

Example:

New Investor Email

↓

Email Workflow

↓

Memory Workflow

↓

Commitment Workflow

↓

Dashboard Update Workflow

Single event.

Multiple reactions.

---

# Event Routing

Each event should route automatically.

Examples:

New Email

↓

Email Workflow

Flight Delayed

↓

Travel Workflow

Bill Due

↓

Finance Workflow

Birthday Approaching

↓

Relationship Workflow

Routing should be deterministic.

---

# Event To Workflow Mapping

Examples:

```text
new_email
→ Email Workflow

flight_delayed
→ Travel Workflow

birthday_approaching
→ Relationship Workflow

subscription_renewal
→ Subscription Workflow

meal_logged
→ Health Workflow
```

This mapping should be centralized.

---

# Event To Memory Pipeline

Many events generate memories.

Example:

User repeatedly books aisle seats.

↓

Booking Events

↓

Memory Extraction

↓

Preference Learned

↓

User Model Updated

Events are the source of learning.

---

# Event To Watcher Pipeline

Events can create watches.

Example:

Investor says:

"Will get back to you Friday."

↓

Email Event

↓

Commitment Extraction

↓

Watcher Created

↓

Waiting For Investor Reply

The watch exists because an event occurred.

---

# Event To Dashboard Pipeline

Events continuously update dashboard state.

Example:

Bill Due Event

↓

Finance Workflow

↓

Dashboard Updated

↓

Appears In Logistics

---

# Event To Notification Pipeline

Events never directly notify.

Instead:

```text
Event
↓
Workflow
↓
Importance Engine
↓
Notification Decision
↓
Notify
```

This prevents spam.

---

# Event System Principles

The Event System should be:

Reliable

Observable

Replayable

Scalable

Decoupled

Auditable

Deterministic

Extensible

---

# Relationship With The Rest Of Donna

The Event System is the starting point.

Everything else depends on it.

Events create workflows.

Workflows create memories.

Memories improve the User Model.

The User Model improves decisions.

Better decisions create a better Donna.

---

# Long-Term Vision

The Event System should allow Donna to become aware of meaningful changes anywhere in a user's life.

The more systems Donna observes:

* email
* messages
* travel
* finance
* health
* relationships
* goals

the richer the event stream becomes.

The richer the event stream becomes,

the better Donna understands the user.

The Event System is how reality enters Donna.

Everything else is built on top of it.
