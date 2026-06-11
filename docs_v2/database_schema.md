# Database_Schema.md

# Purpose

This document defines the core database architecture for Donna.

The database is not merely storage.

The database is the persistent representation of:

* the User Model
* memories
* workflows
* watches
* commitments
* relationships
* goals
* integrations
* events

The database should be designed to support:

* long-term personalization
* proactive behavior
* workflow orchestration
* memory retrieval
* auditability
* explainability

---

# Database Philosophy

Donna uses two primary storage systems:

## PostgreSQL

Purpose:

Structured operational data.

Stores:

* users
* workflows
* watches
* schedules
* events
* commitments
* integrations

---

## Graphiti Knowledge Graph

Purpose:

Relationship-based memory.

Stores:

* people
* preferences
* goals
* memories
* patterns
* relationships

---

# High Level Architecture

```text
Postgres
├── Users
├── Integrations
├── Events
├── Workflows
├── Watches
├── Commitments
├── Schedules
├── Dashboard State
└── Action History

Graphiti
├── Entities
├── Memories
├── Relationships
├── Preferences
├── Goals
├── Patterns
└── Experiences
```

---

# USERS

## users

```sql
users
```

Purpose:

Core user record.

---

Columns

```sql
id UUID PRIMARY KEY

email TEXT

name TEXT

timezone TEXT

created_at TIMESTAMP

updated_at TIMESTAMP

onboarding_status TEXT
```

---

# USER MODEL

## user_model

Purpose:

High-level operating system snapshot.

---

Columns

```sql
id UUID

user_id UUID

life_context TEXT

decision_style JSONB

current_focus TEXT

summary TEXT

updated_at TIMESTAMP
```

---

Example

```json
{
  "decision_style": {
    "speed_over_perfection": true,
    "cost_sensitive": false
  }
}
```

---

# GOALS

## goals

Purpose:

Track user goals.

---

Columns

```sql
id UUID

user_id UUID

title TEXT

description TEXT

category TEXT

priority INTEGER

status TEXT

confidence FLOAT

created_at TIMESTAMP

updated_at TIMESTAMP
```

---

Example

```text
Raise Funding

Get YC Interview

Lose 5kg
```

---

# RELATIONSHIPS

## relationships

Purpose:

Store important people.

---

Columns

```sql
id UUID

user_id UUID

person_name TEXT

relationship_type TEXT

importance_score INTEGER

interaction_frequency INTEGER

last_interaction TIMESTAMP

created_at TIMESTAMP
```

---

Example

```text
Mom

Co-founder

Investor
```

---

# COMMITMENTS

## commitments

Purpose:

Track obligations.

---

Columns

```sql
id UUID

user_id UUID

title TEXT

description TEXT

owner TEXT

due_date TIMESTAMP

priority INTEGER

status TEXT

source TEXT

created_at TIMESTAMP
```

---

Examples

```text
Send Deck

Reply To Investor

Submit Visa Application
```

---

# PREFERENCES

## preferences

Purpose:

Store learned preferences.

---

Columns

```sql
id UUID

user_id UUID

category TEXT

value TEXT

confidence FLOAT

source TEXT

last_confirmed TIMESTAMP
```

---

Examples

```text
Travel → Aisle Seat

Music → Apple Music

Transport → Grab Standard
```

---

# PATTERNS

## patterns

Purpose:

Store behavioral observations.

---

Columns

```sql
id UUID

user_id UUID

pattern TEXT

description TEXT

confidence FLOAT

evidence_count INTEGER

updated_at TIMESTAMP
```

---

Examples

```text
Calls Mom At Noon

Prefers Morning Meetings

Responds Quickly To Investors
```

---

# EVENTS

## events

Purpose:

Store all system events.

---

Columns

```sql
id UUID

user_id UUID

event_type TEXT

source TEXT

payload JSONB

created_at TIMESTAMP
```

---

Examples

```text
new_email

flight_delayed

birthday_approaching
```

---

# WORKFLOWS

## workflows

Purpose:

Track workflow executions.

---

Columns

```sql
id UUID

user_id UUID

workflow_type TEXT

status TEXT

trigger_event_id UUID

started_at TIMESTAMP

completed_at TIMESTAMP
```

---

Statuses

```text
pending

running

waiting

completed

failed

cancelled
```

---

# WORKFLOW EXECUTIONS

## workflow_steps

Purpose:

Track workflow state.

---

Columns

```sql
id UUID

workflow_id UUID

step_name TEXT

status TEXT

started_at TIMESTAMP

completed_at TIMESTAMP
```

---

# WATCHES

## watches

Purpose:

Track ongoing situations.

This is one of the most important tables.

---

Columns

```sql
id UUID

user_id UUID

watch_type TEXT

title TEXT

status TEXT

importance INTEGER

deadline TIMESTAMP

next_check TIMESTAMP

metadata JSONB

created_at TIMESTAMP
```

---

Examples

```text
Tokyo Flight Watch

Investor Reply Watch

AWS Bill Watch

Birthday Watch
```

---

# WATCH HISTORY

## watch_events

Purpose:

Track watch lifecycle.

---

Columns

```sql
id UUID

watch_id UUID

event_type TEXT

details JSONB

created_at TIMESTAMP
```

---

# SCHEDULER

## scheduled_tasks

Purpose:

Store future executions.

---

Columns

```sql
id UUID

user_id UUID

task_type TEXT

execute_at TIMESTAMP

payload JSONB

status TEXT
```

---

Examples

```text
Reminder

Check Flight

Birthday Follow-Up
```

---

# INTEGRATIONS

## integrations

Purpose:

Connected accounts.

---

Columns

```sql
id UUID

user_id UUID

provider TEXT

status TEXT

connected_at TIMESTAMP

permissions JSONB
```

---

Examples

```text
gmail

calendar

grab

spotify
```

---

# TOOL EXECUTIONS

## tool_executions

Purpose:

Audit tool usage.

---

Columns

```sql
id UUID

user_id UUID

tool_name TEXT

workflow_id UUID

request JSONB

response JSONB

created_at TIMESTAMP
```

---

# ACTION HISTORY

## actions

Purpose:

Track all Donna actions.

---

Columns

```sql
id UUID

user_id UUID

action_type TEXT

description TEXT

workflow_id UUID

created_at TIMESTAMP
```

---

Examples

```text
Notification Sent

Ride Booked

Reminder Created

Subscription Cancelled
```

---

# NOTIFICATIONS

## notifications

Purpose:

Track notifications.

---

Columns

```sql
id UUID

user_id UUID

title TEXT

body TEXT

importance TEXT

status TEXT

created_at TIMESTAMP
```

---

Statuses

```text
sent

dismissed

clicked

expired
```

---

# DASHBOARD STATE

## dashboard_sections

Purpose:

Power dashboard UI.

---

Columns

```sql
id UUID

user_id UUID

section TEXT

entity_id UUID

entity_type TEXT

rank INTEGER

updated_at TIMESTAMP
```

---

Examples

```text
Watching

Scheduled

Logistics

Holding

Done
```

---

# DOCUMENTS

## documents

Purpose:

Track uploaded/generated documents.

---

Columns

```sql
id UUID

user_id UUID

title TEXT

document_type TEXT

storage_url TEXT

created_at TIMESTAMP
```

---

Examples

```text
Proof Of Funds

Pitch Deck

Visa Application
```

---

# USER INSIGHTS

## insights

Purpose:

Store generated insights.

---

Columns

```sql
id UUID

user_id UUID

title TEXT

description TEXT

importance INTEGER

created_at TIMESTAMP
```

---

Examples

```text
Spending Increased

Flight Price Dropped

Mom Birthday Approaching
```

---

# GRAPHITI SCHEMA

Graphiti stores relationship-rich memory.

---

# ENTITY

Examples

```text
User

Mom

Investor

Spotify

YC
```

---

Properties

```json
{
  "name": "",
  "type": "",
  "importance": 0
}
```

---

# MEMORY NODES

Examples

```text
Mom Likes Lilies

Prefers Aisle Seat

Uses Grab Standard
```

---

# RELATIONSHIPS

Examples

```text
USER
  PREFERS
     AISLE SEAT

USER
  KNOWS
     MOM

MOM
  LIKES
     LILIES
```

---

# GOAL GRAPH

```text
Raise Funding
    ↑
Investor Meeting

Raise Funding
    ↑
Pitch Deck
```

Goals connect related memories.

---

# COMMITMENT GRAPH

```text
Investor
     ↓
Waiting For Deck
```

Commitments become connected entities.

---

# MEMORY GRAPH

Stores:

Preferences

Goals

Relationships

Patterns

Experiences

Commitments

Watches

All connected through relationships.

---

# Retrieval Layer

Most workflows do not query raw tables.

Instead:

```text
Workflow
↓
Context Assembly
↓
Retrieval Layer
↓
Postgres + Graphiti
↓
Context Package
```

The retrieval layer hides storage complexity.

---

# Database Principles

The database should be:

Reliable

Auditable

Replayable

Explainable

Observable

Extensible

---

# Long-Term Vision

Postgres stores facts.

Graphiti stores meaning.

The User Model emerges from both.

As Donna learns:

* more preferences
* more relationships
* more goals
* more patterns

the database becomes a living representation of the user's life.

The database is not simply persistence.

It is the foundation of Donna's understanding.

Every workflow.

Every watch.

Every memory.

Every recommendation.

Eventually traces back to this schema.
