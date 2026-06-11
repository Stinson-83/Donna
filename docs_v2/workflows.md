# Workflows.md

# Purpose

The Workflow System is the execution layer of Donna.

The Event System answers:

> What happened?

The User Model answers:

> Who is this person?

The Memory System answers:

> What do we know?

The Workflow System answers:

> What should happen next?

Every meaningful action inside Donna is executed through a workflow.

Workflows transform events into outcomes.

---

# Core Principle

Workflows handle process.

Agents handle reasoning.

This distinction is critical.

Bad Architecture:

```text
Event
↓
Agent
↓
Everything
```

This creates:

* expensive reasoning
* unpredictable behavior
* poor reliability

Good Architecture:

```text
Event
↓
Workflow
↓
Context Assembly
↓
Agent
↓
Decision
↓
Workflow Continues
```

The workflow controls the process.

The agent controls the intelligence.

---

# High Level Flow

```text
Event
↓
Workflow Selection
↓
Context Assembly
↓
Agent Reasoning
↓
Decision
↓
Action
↓
Memory Update
↓
Dashboard Update
```

Every workflow follows this pattern.

---

# Workflow Architecture

Each workflow contains:

## Trigger

What started the workflow?

---

## Context

What information is needed?

---

## Reasoning

What should Claude determine?

---

## Decision

What should happen?

---

## Actions

What tools should execute?

---

## Memory Updates

What should be remembered?

---

## Dashboard Updates

What should be visible?

---

# Workflow Categories

Donna contains several major workflow families.

---

# Communication Workflows

Purpose:

Manage communication.

Examples:

* email
* messages
* calls
* voicemails

---

# Scheduling Workflows

Purpose:

Manage time.

Examples:

* booking
* rescheduling
* conflict resolution
* meeting preparation

---

# Travel Workflows

Purpose:

Manage movement.

Examples:

* flights
* hotels
* ride booking
* delays

---

# Relationship Workflows

Purpose:

Manage people.

Examples:

* birthdays
* anniversaries
* follow-ups
* reminders

---

# Health Workflows

Purpose:

Manage wellbeing.

Examples:

* meals
* workouts
* sleep
* habits

---

# Finance Workflows

Purpose:

Manage money.

Examples:

* bills
* subscriptions
* balances
* payments

---

# Goal Workflows

Purpose:

Support goals.

Examples:

* YC application
* fundraising
* weight loss
* learning

---

# Memory Workflows

Purpose:

Convert experiences into understanding.

Examples:

* preference extraction
* relationship updates
* pattern learning

---

# Email Workflow

## Trigger

New email event.

---

## Context Assembly

Retrieve:

* sender
* email content
* relationship
* commitments
* goals

---

## Agent Questions

Ask:

* Is this important?
* Does this require action?
* Is a commitment created?
* Should a watch be created?

---

## Possible Outcomes

```text
Notify
Ignore
Create Watch
Create Commitment
Draft Reply
Schedule Follow-Up
```

---

## Example

Investor Email

↓

Importance High

↓

Notify User

↓

Create Reply Commitment

↓

Create Watch

---

# Message Workflow

## Trigger

Incoming message.

---

## Context

Retrieve:

* sender
* relationship
* recent conversations
* commitments

---

## Outcomes

```text
Notify
Ignore
Create Reminder
Create Follow-Up
Create Memory
```

---

# Scheduling Workflow

Purpose:

Manage time intelligently.

---

## Trigger

Schedule request.

Examples:

* meeting
* dinner
* dentist
* flight

---

## Process

```text
Request
↓
Availability Check
↓
Conflict Check
↓
Preference Check
↓
Alternative Generation
↓
Approval
↓
Schedule
```

---

## Output

Scheduled event.

Watcher created.

Dashboard updated.

---

# Conflict Resolution Workflow

Purpose:

Prevent bad scheduling.

---

## Trigger

Potential conflict.

---

## Retrieve

Calendar

Commitments

Travel

Priorities

Preferences

---

## Agent Decision

Determine:

* severity
* alternatives
* recommendation

---

## Example

Dentist

vs

Investor Meeting

↓

Recommend Moving Dentist

---

# Travel Workflow

Purpose:

Manage trips.

---

## Trigger Examples

Flight booked.

Flight delayed.

Gate changed.

Price changed.

---

## Context

Retrieve:

* travel plans
* calendar
* pickup arrangements
* commitments

---

## Outcomes

```text
Notify
Rebook
Adjust Pickup
Create Watch
```

---

## Example

Flight Delayed

↓

Airport Pickup Exists

↓

Adjust Pickup Recommendation

↓

Notify User

---

# Relationship Workflow

Purpose:

Manage important people.

---

## Trigger Examples

Birthday approaching.

Anniversary approaching.

Long time since contact.

---

## Retrieve

Relationship graph.

Preferences.

History.

Importance.

---

## Outcomes

```text
Reminder
Gift Suggestion
Call Suggestion
Action Proposal
```

---

## Example

Mom Birthday

↓

Likes Lilies

↓

Dinner Scheduled

↓

Recommend Flowers Friday

---

# Finance Workflow

Purpose:

Protect financial health.

---

## Trigger Examples

Bill due.

Low balance.

Renewal approaching.

---

## Retrieve

Balances.

Upcoming payments.

Preferences.

Goals.

---

## Outcomes

```text
Notify
Recommend Transfer
Cancel Subscription
Create Watch
```

---

## Example

AWS Bill

↓

Balance Low

↓

Notify User

↓

Recommend Transfer

---

# Subscription Workflow

Purpose:

Manage recurring services.

---

## Trigger Examples

Renewal approaching.

Usage changed.

Price changed.

---

## Retrieve

Usage history.

Alternatives.

Preferences.

---

## Outcomes

```text
Keep
Cancel
Downgrade
Recommend Alternative
```

---

## Example

Spotify Renewal

↓

Low Usage

↓

Apple Music Preferred

↓

Recommend Cancellation

---

# Health Workflow

Purpose:

Support wellbeing.

---

## Trigger Examples

Lunch check.

Workout missed.

Sleep update.

---

## Retrieve

Goals.

Patterns.

History.

---

## Outcomes

```text
Log
Coach
Recommend
Encourage
```

---

## Example

Lunch Logged

↓

Calorie Target Exceeded

↓

Generate Insight

---

# Goal Workflow

Purpose:

Support major objectives.

---

## Trigger Examples

Goal created.

Goal milestone reached.

Goal-related event detected.

---

## Retrieve

Goal graph.

Relevant commitments.

Relevant watches.

---

## Outcomes

```text
Prioritize
Prepare
Recommend
Notify
```

---

## Example

YC Goal

↓

Interview Email Arrives

↓

Priority Maximum

---

# Watch Creation Workflow

Purpose:

Create long-running monitoring tasks.

---

## Trigger Examples

Waiting for reply.

Flight threshold.

Bill due.

Application status.

---

## Process

```text
Detect Situation
↓
Create Watch
↓
Assign Importance
↓
Assign Check Strategy
↓
Store
```

---

## Example

Investor:

"We'll get back by Friday."

↓

Create Watch

↓

Waiting For Investor Reply

---

# Watch Evaluation Workflow

Purpose:

Monitor active situations.

---

## Trigger

Watch reaches next_check.

---

## Process

```text
Check State
↓
Has Something Changed?
↓
If No:
    Recalculate next_check

If Yes:
    Emit Event
```

---

## Output

New event generated.

---

# Preparation Workflow

Purpose:

Anticipate future needs.

This is one of Donna's most important workflows.

---

## Trigger Examples

Meeting tomorrow.

Flight tomorrow.

Birthday tomorrow.

Deadline approaching.

---

## Retrieve

Context.

Documents.

History.

Relationships.

Goals.

---

## Outcomes

Prepare resources before requested.

---

## Example

Investor Meeting Tomorrow

↓

Gather:

Emails

Deck

Notes

Action Items

↓

Create Briefing

---

# Memory Extraction Workflow

Purpose:

Turn events into understanding.

---

## Trigger

Important event.

---

## Process

```text
Event
↓
Extract Insights
↓
Classify
↓
Store Memory
↓
Update User Model
```

---

## Example

Repeated Aisle Seat Booking

↓

Preference Extracted

↓

User Model Updated

---

# Dashboard Workflow

Purpose:

Maintain live system state.

---

## Trigger

Any significant update.

---

## Update Sections

Watching

Scheduled

Logistics

Holding

Done

---

# Notification Workflow

Purpose:

Control interruptions.

---

## Trigger

Potential notification.

---

## Process

```text
Event
↓
Importance Score
↓
Relationship Context
↓
Goal Context
↓
Notify?
```

---

## Outcomes

```text
Notify Now
Delay
Ignore
Bundle
```

---

# Live Tab Workflow

Purpose:

Real-time execution.

---

## Trigger

User request.

---

## Process

```text
Request
↓
Need Tool?
↓
Need Permission?
↓
OAuth
↓
Execute
↓
Present Options
↓
Complete
```

---

## Example

Book Ride

↓

Need Grab Access

↓

Connect Account

↓

Show Ride Options

↓

Book

---

# Workflow State

Every workflow should maintain state.

States:

```text
Pending

Running

Waiting

Completed

Failed

Cancelled
```

This enables recovery and reliability.

---

# Workflow Chaining

One workflow can start another.

Example:

New Email

↓

Email Workflow

↓

Commitment Created

↓

Watch Created

↓

Dashboard Updated

↓

Notification Sent

Multiple workflows.

One event.

---

# Workflow Success Criteria

A workflow is successful when:

* correct context was retrieved
* correct decision was made
* correct action executed
* memory updated
* dashboard updated

Every workflow should improve the User Model.

---

# Relationship To Donna

Workflows are the operational machinery of Donna.

Events create workflows.

Workflows retrieve context.

Context powers reasoning.

Reasoning creates decisions.

Decisions create actions.

Actions create memories.

Memories improve the User Model.

The User Model improves future workflows.

This loop is how Donna becomes more valuable over time.

The Workflow System is the execution engine that transforms awareness into action.
