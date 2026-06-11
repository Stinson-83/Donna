# Engines.md

# Purpose

Engines are the intelligence modules of Donna.

Events detect change.

Workflows manage execution.

Memory stores understanding.

The User Model represents the user.

Engines are responsible for decision-making.

They transform information into intelligence.

Without engines:

Donna becomes an automation platform.

With engines:

Donna becomes a Chief of Staff.

---

# Core Principle

Every engine should answer a specific question.

Examples:

Importance Engine

> Does this matter?

Relationship Engine

> Who matters?

Goal Engine

> Why does this matter?

Preparation Engine

> What will be needed next?

Conflict Engine

> Is there a better way?

Keeping engines focused makes reasoning modular, explainable, and scalable.

---

# Engine Architecture

Every engine follows:

```text
Input
↓
Analysis
↓
Decision
↓
Output
```

Outputs become inputs for other engines.

---

# Engine Hierarchy

```text
Context Assembly Engine
        ↓
Relationship Engine
Goal Engine
Preference Engine
Pattern Engine
        ↓
Importance Engine
        ↓
Cross-Connection Engine
        ↓
Preparation Engine
Conflict Engine
Safety Engine
        ↓
Decision Engine
```

This is the intelligence stack.

---

# Context Assembly Engine

## Purpose

Build the context package given to Claude.

Without this engine:

Claude receives raw events.

With this engine:

Claude receives understanding.

---

## Inputs

Event

User Model

Memory

Active Watches

Commitments

Current Context

---

## Outputs

Relevant Context Package

---

## Example

Event:

Investor Email

Retrieve:

* investor relationship
* fundraising goal
* open commitments
* active watches

Package all context.

Send to Claude.

---

# Goal Engine

## Purpose

Understand what the user is trying to achieve.

Goals provide meaning.

Without goals:

Everything appears equally important.

---

## Responsibilities

Track:

* career goals
* health goals
* relationship goals
* financial goals
* personal goals

---

## Questions

Does this event support a goal?

Does this event threaten a goal?

Does this event accelerate a goal?

---

## Example

Goal:

Raise Funding

Event:

Investor Email

Result:

Priority Increased.

---

# Relationship Engine

## Purpose

Understand people.

Not contacts.

Relationships.

---

## Responsibilities

Maintain:

* importance
* trust
* interaction history
* commitments
* preferences

---

## Questions

Who is involved?

How important are they?

What is the relationship context?

---

## Example

Message received.

From:

Mom

Importance:

100

Interrupt immediately.

---

# Preference Engine

## Purpose

Understand what users tend to choose.

---

## Responsibilities

Track:

* travel preferences
* communication preferences
* scheduling preferences
* product preferences

---

## Questions

What would the user likely choose?

What has the user chosen historically?

---

## Example

Ride Booking

History:

Grab Standard 95%

Recommendation:

Grab Standard

---

# Pattern Engine

## Purpose

Learn recurring behaviors.

Patterns represent reality.

---

## Responsibilities

Detect:

* routines
* habits
* recurring decisions
* productivity cycles

---

## Questions

What behavior repeats?

What happens consistently?

---

## Example

Repeatedly moves meetings away from 2 PM.

Pattern:

Low productivity period.

Future scheduling should avoid it.

---

# Commitment Engine

## Purpose

Track obligations.

Many commitments are not tasks.

Many commitments are not calendar events.

Donna must still track them.

---

## Examples

Send Deck

Reply To Investor

RSVP Event

Submit Application

---

## Questions

What is the user responsible for?

Who is waiting on the user?

What remains unresolved?

---

## Output

Commitment Graph

---

# Watch Engine

## Purpose

Create and manage active monitoring.

---

## Responsibilities

Create Watches

Update Watches

Evaluate Watches

Retire Watches

---

## Examples

Waiting For Investor Reply

Tokyo Flight Watch

AWS Bill Watch

Birthday Watch

---

## Questions

Should this situation be monitored?

How often should it be checked?

When should it expire?

---

# Dynamic Check Engine

## Purpose

Determine when watches should wake up.

Avoid unnecessary polling.

---

## Inputs

Importance

Urgency

Deadline

Recent Change Rate

---

## Output

next_check

---

## Example

Trip In 6 Months

Check:

Daily

---

Trip Tomorrow

Check:

Every 15 Minutes

---

# Importance Engine

## Purpose

Determine what deserves attention.

This is one of the most important engines in Donna.

---

## Responsibilities

Prevent notification spam.

Prioritize correctly.

---

## Inputs

Goals

Relationships

Deadlines

Risk

Financial Impact

Commitments

Current Context

---

## Questions

Should the user care?

Should the user be interrupted?

How important is this?

---

## Outputs

Critical

High

Medium

Low

Ignore

---

## Example

Investor Email

High

---

Newsletter

Ignore

---

# Cross-Connection Engine

## Purpose

Create insights by connecting unrelated information.

This is where magic emerges.

---

## Inputs

Calendar

Goals

Relationships

Preferences

Patterns

Active Watches

---

## Questions

What useful connection exists?

What opportunity exists?

What risk exists?

---

## Example

Mom Birthday Saturday

Dinner Saturday

Mom Likes Lilies

Output:

Order flowers Friday.

---

# Preparation Engine

## Purpose

Anticipate needs before requests occur.

This is the Donna-from-Suits engine.

---

## Questions

What will the user likely need next?

What should already be prepared?

---

## Examples

Investor Meeting Tomorrow

Prepare:

* emails
* notes
* pitch deck
* summaries

---

Flight Tomorrow

Prepare:

* boarding pass
* weather
* traffic
* gate updates

---

# Conflict Engine

## Purpose

Prevent bad decisions.

---

## Inputs

Calendar

Travel

Commitments

Goals

Preferences

Patterns

---

## Questions

Is there a conflict?

Is there a better option?

What should be moved?

---

## Example

Dentist

vs

Investor Meeting

Recommendation:

Move Dentist

---

# Recommendation Engine

## Purpose

Generate suggestions.

---

## Questions

What should the user do?

What option is best?

---

## Examples

Cancel Subscription

Take Earlier Flight

Send Follow-Up

Book Restaurant

---

# Opportunity Engine

## Purpose

Identify opportunities.

Most systems detect problems.

Donna should detect opportunities.

---

## Examples

Flight price drop.

Investor available.

Meeting moved earlier.

Discount available.

Time opened in calendar.

---

## Questions

Can the user's life be improved?

Can time be saved?

Can money be saved?

Can relationships be improved?

---

# Risk Engine

## Purpose

Identify threats.

---

## Examples

Low balance.

Visa deadline.

Missed commitment.

Travel disruption.

---

## Questions

What could go wrong?

How severe is the impact?

How likely is the impact?

---

# Safety Engine

## Purpose

Prevent unsafe actions.

---

## Categories

Low Risk

Medium Risk

High Risk

---

## Examples

Book Restaurant

Low Risk

---

Transfer ₹50,000

High Risk

---

## Output

Auto Execute

Ask User

Block Action

---

# Consent Engine

## Purpose

Manage permissions.

---

## Questions

Do we have access?

Do we have approval?

Do we need confirmation?

---

## Examples

Need Gmail OAuth

Need Bank Permission

Need Calendar Access

---

# Notification Engine

## Purpose

Control interruptions.

---

## Inputs

Importance Score

Relationship Context

Goal Context

Current Activity

---

## Questions

Should we notify now?

Should we wait?

Should we bundle?

Should we ignore?

---

## Outputs

Notify

Delay

Bundle

Ignore

---

# Memory Extraction Engine

## Purpose

Convert experiences into memories.

---

## Questions

What should be remembered?

What might matter later?

---

## Outputs

Preferences

Relationships

Goals

Patterns

Commitments

Experiences

---

## Example

Repeated Aisle Seat Selection

↓

Preference Learned

---

# User Model Engine

## Purpose

Maintain Donna's understanding of the user.

This is the most important engine.

Everything ultimately feeds this engine.

---

## Responsibilities

Update:

* goals
* relationships
* preferences
* patterns
* commitments
* decision style

---

## Questions

What have we learned?

How has the user changed?

What should be updated?

---

## Output

Updated User Operating System

---

# Dashboard Engine

## Purpose

Generate Donna's live state.

---

## Sections

Watching

Scheduled

Logistics

Holding

Done

---

## Inputs

Active Watches

Calendar

Commitments

Tasks

Recent Events

---

## Output

User Interface State

---

# Decision Engine

## Purpose

Produce final actions.

Every workflow eventually reaches this engine.

---

## Inputs

Outputs from all engines.

---

## Final Decisions

```text
NOTIFY_NOW

SCHEDULE

CREATE_WATCH

TAKE_ACTION

PREPARE

IGNORE
```

---

# Engine Interaction Flow

```text
Event
↓
Context Assembly Engine
↓
Relationship Engine
Goal Engine
Preference Engine
Pattern Engine
Commitment Engine
↓
Importance Engine
↓
Cross-Connection Engine
↓
Preparation Engine
Conflict Engine
Risk Engine
Safety Engine
↓
Recommendation Engine
↓
Decision Engine
↓
Action
↓
Memory Extraction Engine
↓
User Model Engine
```

---

# Long-Term Vision

The purpose of the Engine Layer is not automation.

The purpose is judgment.

Events provide awareness.

Memory provides understanding.

The User Model provides identity.

Engines provide intelligence.

The better these engines become, the closer Donna moves from:

> "I know what happened."

to

> "I know what matters."

That transition is the entire product.

The Engine Layer is where Donna becomes Donna.
