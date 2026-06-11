# Moment_Mapping.md

# Purpose

This document maps every major Donna demo moment to the actual architecture.

The goal is to answer:

For each moment:

* What triggered it?
* Which workflows ran?
* Which engines participated?
* Which memories were retrieved?
* Which tools were used?
* Which watches were created?
* Which User Model components were involved?

This document serves as the bridge between:

```text
Vision.md
```

and

```text
Implementation
```

---

# Architectural Flow

Every moment follows:

```text
Reality
↓
Event
↓
Event Bus
↓
Workflow
↓
Context Assembly
↓
User Model Retrieval
↓
Claude Reasoning
↓
Engines
↓
Decision
↓
Action
↓
Memory Update
↓
Dashboard Update
```

The specific components vary per moment.

---

# Moment 1

## Donna Dashboard

### User Experience

User opens Donna.

Donna immediately presents:

* Watching
* Scheduled
* Logistics
* Holding
* Done

Instead of a chat screen.

---

## Why This Matters

The dashboard communicates:

> Donna is actively working.

Not waiting.

---

## Components

### Workflows

Dashboard Workflow

Watch Evaluation Workflow

---

### Engines

Dashboard Engine

Importance Engine

Watch Engine

---

### Memory

Active Watches

Current Commitments

Current Goals

Upcoming Events

---

### Data Sources

Calendar

Email

Messages

Travel

Finance

Watchers

---

### Output

Live dashboard state.

---

# Moment 2

## Important Email

Example:

Investor Email

Sequoia Email

Deadline Email

---

## Trigger

New Email Event

---

## Event Flow

```text
Gmail
↓
New Email Trigger
↓
Event Bus
↓
Email Workflow
```

---

## Context Retrieved

Relationship

Goal Relevance

Open Commitments

Previous Conversations

Active Watches

---

## Engines

Relationship Engine

Goal Engine

Importance Engine

Commitment Engine

---

## Claude Determines

* Is this important?
* Does this require action?
* Does this create a commitment?

---

## Outcomes

Notify User

Create Commitment

Create Watch

Update Dashboard

---

# Moment 3

## AWS Bill Warning

### User Experience

Donna notices:

AWS payment due.

Balance insufficient.

Potential issue ahead.

---

## Trigger

Upcoming Bill Event

or

Finance Watch Event

---

## Workflow

Finance Workflow

---

## Context Retrieved

Bank Balance

Upcoming Payments

Financial Preferences

Existing Commitments

---

## Engines

Finance Engine

Risk Engine

Importance Engine

Safety Engine

---

## Claude Determines

Can payment succeed?

Is intervention required?

---

## Outcome

Notify User

Recommend Transfer

Create Watch

Update Dashboard

---

# Moment 4

## Nutrition Tracking

### User Experience

Donna asks:

What did you eat?

Then provides insight.

---

## Trigger

Scheduled Health Event

---

## Workflow

Health Workflow

---

## Context Retrieved

Health Goals

Past Meals

Nutrition History

Patterns

---

## Engines

Goal Engine

Pattern Engine

Health Engine

---

## Claude Determines

Progress

Trends

Recommendations

---

## Outcomes

Store Meal

Generate Insight

Update Health Memory

Update Dashboard

---

# Moment 5

## Restaurant Recommendation

### User Experience

User asks:

Where should we eat?

Donna recalls:

Friend recommendation.

Past discussions.

Preferences.

---

## Trigger

User Query

---

## Workflow

Relationship Workflow

Memory Retrieval Workflow

Recommendation Workflow

---

## Context Retrieved

Restaurant Memories

Relationship Graph

Past Conversations

Food Preferences

---

## Engines

Relationship Engine

Preference Engine

Cross-Connection Engine

Recommendation Engine

---

## Outcome

Recommendation

Reservation Option

Memory Reinforcement

---

# Moment 6

## Live Tab Ride Booking

### User Experience

User asks:

Book me a ride.

Donna handles everything.

---

## Trigger

User Request

---

## Workflow

Live Tab Workflow

Scheduling Workflow

---

## Context Retrieved

Transportation Preferences

Travel Plans

Calendar

Existing Rides

---

## Engines

Preference Engine

Scheduling Engine

Consent Engine

Decision Engine

---

## Integrations

Grab

Uber

Calendar

---

## Outcome

Book Ride

Create Travel Watch

Update Dashboard

---

# Moment 7

## Mom's Birthday

### User Experience

Donna notices:

Birthday approaching.

No gift ordered.

Calendar busy.

Suggests solution.

---

## Trigger

Relationship Watch Event

---

## Workflow

Relationship Workflow

Preparation Workflow

---

## Context Retrieved

Birthday

Relationship Importance

Gift Preferences

Calendar

Travel

---

## Engines

Relationship Engine

Cross-Connection Engine

Preparation Engine

Importance Engine

---

## Claude Determines

What should happen?

When should it happen?

---

## Outcome

Gift Recommendation

Flower Recommendation

Reminder

Potential Auto Action

---

# Moment 8

## Subscription Cancellation

### User Experience

Donna notices:

Spotify renewing tomorrow.

Barely used.

Apple Music preferred.

Recommends cancellation.

---

## Trigger

Subscription Renewal Event

---

## Workflow

Subscription Workflow

---

## Context Retrieved

Usage

Preferences

Costs

Alternatives

---

## Engines

Preference Engine

Importance Engine

Recommendation Engine

Finance Engine

---

## Claude Determines

Is this still valuable?

---

## Outcome

Keep

Cancel

Downgrade

Switch

---

# Moment 9

## Daily Summary

### User Experience

Donna summarizes:

What happened.

What changed.

What matters.

---

## Trigger

Scheduled Summary Event

---

## Workflow

Summary Workflow

Dashboard Workflow

---

## Context Retrieved

Events

Tasks

Watches

Commitments

Goals

---

## Engines

Importance Engine

Dashboard Engine

Pattern Engine

---

## Outcome

Summary Generated

Dashboard Updated

Insights Generated

---

# Screenshot Moment

## Flight Delay + Pickup Adjustment

### User Experience

Flight delayed.

Donna notices.

Donna realizes:

Someone is picking user up.

Donna suggests a better plan.

---

## Trigger

Flight Delay Event

---

## Workflow

Travel Workflow

Conflict Workflow

Relationship Workflow

---

## Context Retrieved

Flight

Pickup Plan

Calendar

Relationship

Travel History

---

## Engines

Travel Engine

Cross-Connection Engine

Relationship Engine

Preparation Engine

---

## Claude Determines

What secondary effects exist?

---

## Outcome

Updated Pickup Plan

Message Draft

Travel Update

---

# Screenshot Moment

## Study Permit / Visa Tracking

### User Experience

Donna notices:

Permit status changed.

Action needed.

Provides next steps.

---

## Trigger

Portal Watch Event

---

## Workflow

Application Workflow

Document Workflow

---

## Context Retrieved

Application History

Deadlines

Documents

Requirements

---

## Engines

Preparation Engine

Risk Engine

Opportunity Engine

---

## Outcome

Action Card

Reminder

Document Preparation

---

# Screenshot Moment

## Proof of Funds Generation

### User Experience

User uploads document.

Donna prepares application package.

---

## Trigger

Document Upload

---

## Workflow

Document Workflow

Preparation Workflow

---

## Context Retrieved

Application

Requirements

Financial Documents

Deadlines

---

## Engines

Preparation Engine

Safety Engine

Document Engine

---

## Outcome

Generated Document

Stored File

Application Progress Updated

---

# Screenshot Moment

## Voice Call

### User Experience

User talks naturally.

Donna reasons continuously.

---

## Trigger

Voice Session Start

---

## Workflow

Voice Workflow

Live Tab Workflow

---

## Context Retrieved

Current Conversation

User Model

Relevant Memories

---

## Engines

Context Assembly Engine

Decision Engine

Importance Engine

Recommendation Engine

---

## Outcome

Conversation

Actions

Cards

Tool Execution

Memory Updates

---

# Active Watch System Mapping

Most proactive moments originate from watches.

Examples:

Waiting For Investor Reply

AWS Bill Due

Mom Birthday

Flight Watch

Visa Application

Permit Approval

Subscription Renewal

---

## Watch Lifecycle

```text
Event
↓
Watch Created
↓
Watch Evaluated
↓
State Changes
↓
New Event Generated
↓
Workflow Starts
```

This loop powers most proactive behavior.

---

# User Model Mapping

Every moment should update the User Model.

Examples:

Restaurant Choice

↓

Food Preference

---

Flight Choice

↓

Travel Preference

---

Gift Selection

↓

Relationship Understanding

---

Ride Selection

↓

Transportation Preference

---

Subscription Decision

↓

Value Preference

---

Every moment teaches Donna something.

---

# System-Level View

The demo appears to show many separate features.

In reality:

Every moment is produced by the same architecture.

```text
Event System
↓
Workflow System
↓
Memory System
↓
User Model
↓
Engine Layer
↓
Integrations
↓
Action
```

The differences are only:

* trigger
* workflow
* retrieved context
* engines involved
* final action

The underlying architecture remains identical.

---

# Long-Term Goal

Eventually every moment in Donna should be explainable through this mapping.

When a new feature is proposed, the team should be able to answer:

* Which event triggers it?
* Which workflow handles it?
* Which memories are required?
* Which engines reason about it?
* Which integrations execute it?
* How does it improve the User Model?

If those questions cannot be answered, the feature is not fully designed.

Moment Mapping ensures that product experiences remain grounded in the architecture and that the architecture remains aligned with the vision.
