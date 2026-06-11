# User_Model.md

# Purpose

The User Model is the core asset of Donna.

Everything Donna does exists to improve, maintain, and leverage the User Model.

The User Model is not a profile.

The User Model is not a settings page.

The User Model is a continuously evolving representation of how a person operates.

The quality of Donna is directly proportional to the quality of the User Model.

A user with one day of Donna history should receive useful assistance.

A user with three years of Donna history should feel impossible to replace.

The User Model is the primary moat of the product.

---

# Fundamental Principle

Most assistants understand requests.

Donna must understand people.

Traditional AI:

```text
User Request
↓
Answer
```

Donna:

```text
User
↓
Understand User
↓
Interpret Request
↓
Answer
```

Every event, task, decision, recommendation, reminder, and action must be evaluated through the User Model.

---

# User Model Architecture

The User Model is composed of multiple layers.

```text
Goals
↓
Relationships
↓
Preferences
↓
Patterns
↓
Commitments
↓
Decision Style
↓
Life Context
↓
Identity Model
```

Each layer contributes context.

Together they create understanding.

---

# Layer 1: Goals

## Purpose

Goals explain why things matter.

Without goals:

everything appears equally important.

With goals:

Donna can prioritize correctly.

---

## Examples

Career:

* Get into YC
* Raise funding
* Get promoted
* Graduate

Health:

* Lose 5 kg
* Build muscle
* Improve sleep

Relationships:

* Spend more time with parents
* Maintain friendships

Financial:

* Save money
* Reduce expenses

Personal:

* Travel more
* Learn a language

---

## Goal Attributes

Each goal should store:

```json
{
  "goal_id": "",
  "title": "",
  "category": "",
  "priority": 0,
  "confidence": 0,
  "created_at": "",
  "status": ""
}
```

---

## How Goals Are Learned

Goals can come from:

Explicit statements

Example:

> I want to get into YC.

---

Repeated behavior

Example:

* Constant startup activity
* Investor conversations
* Fundraising documents

Donna infers:

> Fundraising is likely a major goal.

---

## Why Goals Matter

Goals determine importance.

Example:

YC interview email.

If YC is a goal:

Priority = Extremely High

If YC is not a goal:

Priority = Normal

---

# Layer 2: Relationships

## Purpose

Not all people matter equally.

Donna must understand who matters.

---

## Relationship Graph

People become entities.

Examples:

Mom

Dad

Co-founder

Investor

Friend

Professor

Recruiter

---

## Relationship Attributes

```json
{
  "person": "",
  "importance": 0,
  "interaction_frequency": 0,
  "last_contact": "",
  "relationship_type": ""
}
```

---

## Stored Information

For each person:

Preferences

Examples:

* Mom likes lilies
* Investor prefers concise emails

Patterns

Examples:

* Call mom on birthdays
* Weekly check-in with co-founder

Shared history

Open commitments

Future obligations

---

## Relationship Importance

Example:

Mom = 100

Co-founder = 95

Investor = 90

Recruiter = 20

Newsletter sender = 0

---

## Why Relationships Matter

The same event changes meaning.

Message from Mom:

Interrupt immediately.

Message from newsletter:

Ignore.

---

# Layer 3: Preferences

## Purpose

Preferences describe what users choose.

---

## Examples

Travel

* Aisle seat
* Economy
* Direct flights

Transportation

* Grab Standard
* Uber Comfort

Music

* Apple Music

Food

* Thai food
* Vegetarian

Communication

* Concise messages
* Bullet points

Scheduling

* Morning meetings

---

## Preference Schema

```json
{
  "preference": "",
  "confidence": 0,
  "source": "",
  "last_confirmed": ""
}
```

---

## Learning Preferences

Explicit:

> I prefer aisle seats.

Implicit:

Repeatedly choosing aisle seats.

Behavior is stronger than statements.

---

## Confidence

Every preference has confidence.

Example:

```json
{
  "preference": "Aisle Seat",
  "confidence": 0.96
}
```

Confidence increases through repeated observation.

---

# Layer 4: Patterns

## Purpose

Patterns describe recurring behavior.

Patterns are more powerful than preferences.

Patterns describe reality.

---

## Examples

Productivity

* Works best 9 AM - 12 PM

Communication

* Replies quickly to investors

Health

* Skips gym on Fridays

Family

* Calls mom around noon

Travel

* Arrives early for flights

---

## Pattern Schema

```json
{
  "pattern": "",
  "confidence": 0,
  "evidence_count": 0
}
```

---

## Why Patterns Matter

Example:

User repeatedly moves meetings away from 2 PM.

Donna learns:

> User performs poorly at 2 PM.

Future scheduling should avoid that time.

---

# Layer 5: Commitments

## Purpose

Track obligations.

Many commitments never enter calendars.

Donna must track them.

---

## Examples

Reply to investor.

Send deck.

RSVP wedding.

Submit application.

Follow up with professor.

---

## Commitment Schema

```json
{
  "commitment": "",
  "owner": "",
  "deadline": "",
  "status": ""
}
```

---

## Sources

Emails

Messages

Meetings

Voice conversations

Tasks

Documents

---

## Why Commitments Matter

A commitment often matters more than a calendar event.

Example:

Investor waiting for response.

This should remain visible even if not scheduled.

---

# Layer 6: Decision Style

## Purpose

Understand how the user makes decisions.

---

## Examples

Speed vs Accuracy

Risk Tolerance

Delegation Preference

Budget Sensitivity

Planning Horizon

Communication Style

---

## Examples

User consistently chooses:

* faster option
* more expensive option

Inference:

> Values time over money.

---

User repeatedly chooses:

* cheapest option

Inference:

> Cost conscious.

---

## Why Decision Style Matters

Donna should recommend actions aligned with user behavior.

Not generic recommendations.

---

# Layer 7: Life Context

## Purpose

Understand the user's current season of life.

People change.

The User Model must adapt.

---

## Examples

Student

Founder

Fundraising

Job Search

Traveling

Exam Period

Family Emergency

Moving Cities

---

## Why Context Matters

The same person behaves differently across life stages.

Donna should understand the current context.

---

# Layer 8: Identity Model

## Purpose

The highest level of abstraction.

Answer:

How does this person operate?

---

## Examples

Founder

Builder

Researcher

Planner

Creative

Operator

Student

---

## Identity Examples

"This user values progress over perfection."

"This user hates unnecessary meetings."

"This user prefers preparation."

"This user is highly relationship oriented."

---

## Why Identity Matters

Identity influences every decision.

It becomes the foundation for long-term personalization.

---

# Learning Pipeline

Every event enters:

```text
Event
↓
Memory Extraction
↓
User Model Update
```

---

## Example

Event:

User books aisle seat.

Update:

Preference:
Aisle Seat +1 confidence

---

Event:

Calls Mom on birthday.

Update:

Pattern:
Birthday Call +1 confidence

---

Event:

Replies to investor in 5 minutes.

Update:

Pattern:
Investor Priority +1 confidence

---

# Confidence System

Nothing should be absolute.

Every belief has confidence.

Example:

```json
{
  "belief": "Prefers Apple Music",
  "confidence": 0.87
}
```

Confidence rises through repeated evidence.

Confidence falls when contradicted.

---

# Retrieval Strategy

When an event occurs:

Donna retrieves:

Relevant Goals

Relevant Relationships

Relevant Preferences

Relevant Patterns

Relevant Commitments

Relevant Decision Traits

Only relevant context should be injected.

Never retrieve the entire User Model.

---

# Evolution

The User Model is never finished.

It continuously evolves.

Every:

* click
* booking
* message
* email
* conversation
* approval
* rejection

teaches Donna something.

The system should become more accurate every day.

---

# Success Metric

The quality of the User Model can be measured by:

How often Donna predicts correctly.

Examples:

* Correct recommendations
* Correct reminders
* Correct prioritization
* Correct preparation
* Correct actions

The best User Model eventually produces a feeling:

> Donna knows how I operate.

That feeling is the product.

The User Model is the most important asset in the entire system.

Everything else exists to improve it.
