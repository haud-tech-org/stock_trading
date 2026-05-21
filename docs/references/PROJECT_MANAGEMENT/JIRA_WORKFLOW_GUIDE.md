# Jira Workflow Guide — Stock Trading Project

**Status**: ✅ Complete Guide  
**Purpose**: Manage tasks and practice role-based activities using Jira (or compatible frameworks)  
**Audience**: All roles — Product Owner, Manager, BSA, Developer  
**Last Updated**: March 2026

---

## 🎯 Overview

This guide walks you through setting up and using Jira (or any Agile-compatible tool such as Linear, Trello, GitHub Projects, or Azure DevOps Boards) to manage the Stock Trading project. It covers:

- Step-by-step Jira project setup
- Role definitions and responsibilities
- Ticket lifecycle from creation to completion
- Conventions and best practices tailored to this project

---

## 📋 Table of Contents

1. [Supported Tools](#1-supported-tools)
2. [Project Setup in Jira](#2-project-setup-in-jira)
3. [Roles & Responsibilities](#3-roles--responsibilities)
4. [Issue Types & Conventions](#4-issue-types--conventions)
5. [Ticket Lifecycle (Workflow)](#5-ticket-lifecycle-workflow)
6. [Sprint Ceremonies](#6-sprint-ceremonies)
7. [Role-Based Activity Guide](#7-role-based-activity-guide)
   - [Product Owner](#71-product-owner)
   - [Manager / Scrum Master](#72-manager--scrum-master)
   - [BSA (Business System Analyst)](#73-bsa-business-system-analyst)
   - [Developer](#74-developer)
8. [Label & Component Conventions](#8-label--component-conventions)
9. [Linking Jira Tickets to Git Commits](#9-linking-jira-tickets-to-git-commits)
10. [Quick-Start Checklist](#10-quick-start-checklist)

---

## 1. Supported Tools

Any of the following tools implement the same Agile/Scrum workflow described in this guide:

| Tool | Free Tier | URL |
|------|-----------|-----|
| **Jira** (recommended) | Up to 10 users | https://www.atlassian.com/software/jira |
| GitHub Projects | Unlimited | https://github.com/orgs/{org}/projects |
| Linear | Up to 10 users | https://linear.app |
| Trello (Kanban-only) | Free | https://trello.com |
| Azure DevOps Boards | Up to 5 users | https://dev.azure.com |

> **Recommendation**: Use **Jira** for full Scrum support (backlog, sprints, velocity, burndown). Use **GitHub Projects** if you want zero context-switching from the codebase.

---

## 2. Project Setup in Jira

### Step 1 — Create a New Jira Project

1. Log in to Jira → **Projects** → **Create project**
2. Select template: **Scrum** (recommended) or **Kanban**
3. Fill in:
   - **Name**: `StockTrading`
   - **Key**: `ST` (used as prefix for all ticket IDs, e.g., `ST-42`)
   - **Project type**: Software
4. Click **Create**

### Step 2 — Configure the Board

1. Go to **Board Settings** → **Columns**
2. Set up these columns (map to statuses):

   | Column | Statuses Mapped |
   |--------|----------------|
   | **Backlog** | Backlog |
   | **To Do** | Open, To Do |
   | **In Progress** | In Progress |
   | **In Review** | In Review, Code Review |
   | **Testing / QA** | QA, Testing |
   | **Done** | Done, Closed |

3. Enable **Backlog view** (Scrum board setting)

### Step 3 — Set Up Issue Types

Go to **Project Settings** → **Issue types** and ensure these types are enabled:

| Issue Type | Icon | Purpose |
|------------|------|---------|
| **Epic** | 🟣 | Large feature or module (e.g., "CVA Alert Approach") |
| **Story** | 🟢 | User-facing requirement (e.g., "As a trader, I want alerts…") |
| **Task** | 🔵 | Technical work (e.g., "Implement `analyzer.py` for CVA") |
| **Sub-task** | ⚪ | Breakdown of a Story or Task |
| **Bug** | 🔴 | Defect or unexpected behavior |
| **Spike** | 🟡 | Research/investigation ticket |

### Step 4 — Create Components

Go to **Project Settings** → **Components** and add:

```
alert-approaches      # New trading approach implementations
data-pipeline         # HAR extraction, data aggregation
notifications         # Email/Telegram alert delivery
tools                 # CLI tools, simulators, report generators
infrastructure        # Docker, Kubernetes, GCP deployments
documentation         # Docs additions and updates
testing               # Test coverage improvements
```

### Step 5 — Create Labels

Add these labels under **Project Settings** → **Labels**:

```
priority:critical   priority:high   priority:medium   priority:low
type:feature        type:bugfix     type:refactor     type:research
area:backend        area:infra      area:docs
sprint:ready        blocked         needs-clarification
```

### Step 6 — Configure a Version / Fix Version

1. Go to **Project Settings** → **Versions**
2. Create versions matching your milestones, e.g.:
   - `v1.0.0 — Core Alert Approaches`
   - `v1.1.0 — GCP Deployment`
   - `v1.2.0 — Simulation Reports`

---

## 3. Roles & Responsibilities

| Role | Jira Role | Primary Responsibilities |
|------|-----------|--------------------------|
| **Product Owner** | Project Admin | Owns the backlog; prioritizes Epics and Stories; accepts completed work |
| **Manager / Scrum Master** | Project Admin or Member | Facilitates ceremonies; removes blockers; tracks velocity and burndown |
| **BSA** | Member | Writes User Stories and acceptance criteria; bridges business and tech |
| **Developer** | Member | Implements Tasks and Sub-tasks; writes code and tests; raises bugs |

---

## 4. Issue Types & Conventions

### Epic
- Represents a large feature, module, or theme that spans multiple sprints.
- **Title format**: `[EPIC] <Feature Name>` (e.g., `[EPIC] CVA Alert Approach`)
- **Owner**: Product Owner creates; BSA refines
- **Fields to fill**: Summary, Description, Component, Fix Version, Priority, Start Date, Due Date

### Story
- Describes a requirement from the perspective of a user or stakeholder.
- **Title format**: `As a <role>, I want <goal> so that <reason>`
- **Owner**: BSA writes; Product Owner approves
- **Fields to fill**: Summary, Description, Acceptance Criteria, Story Points, Component, Epic Link, Assignee

**Example**:
```
Summary: As a trader, I want to receive a CVA alert when volume is anchored 
         so that I can make a timely trade decision.

Acceptance Criteria:
  - Given market data is streamed
  - When CVA conditions are met
  - Then a notification is sent within 5 seconds
  - And the alert is logged to Cloud Storage
```

### Task
- A concrete unit of technical work.
- **Title format**: Short imperative verb phrase (e.g., `Implement ConsistentVolumeAnchorAnalyzer`)
- **Owner**: Developer self-assigns
- **Fields to fill**: Summary, Description, Story Points (or Time Estimate), Component, Linked Story, Assignee

### Bug
- **Title format**: `[BUG] <Short description of symptom>`
- **Fields to fill**: Summary, Steps to Reproduce, Expected vs Actual, Severity, Assignee

### Spike
- **Title format**: `[SPIKE] <Research question>`
- **Fields to fill**: Summary, Goal, Time-box (story points = research hours), Output (document/decision)

---

## 5. Ticket Lifecycle (Workflow)

```
Backlog → To Do → In Progress → In Review → Testing/QA → Done
                                    ↓
                              (Rework needed)
                              ← In Progress
```

### Status Transitions

| From | To | Who Triggers | Condition |
|------|----|-------------|-----------|
| Backlog | To Do | Scrum Master during Sprint Planning | Ticket is sprint-ready |
| To Do | In Progress | Developer | Work has started |
| In Progress | In Review | Developer | Code pushed, PR opened |
| In Review | Testing/QA | Reviewer / BSA | PR approved, deployed to staging |
| In Review | In Progress | Reviewer | Changes requested |
| Testing/QA | Done | BSA / Product Owner | Acceptance criteria met |
| Testing/QA | In Progress | BSA / Developer | Bug found in QA |
| Any | Blocked | Any | External dependency halts progress |

---

## 6. Sprint Ceremonies

### Sprint Duration: 2 weeks (recommended)

| Ceremony | Who Attends | Duration | Purpose |
|----------|-------------|----------|---------|
| **Sprint Planning** | All roles | 1–2 hours | Select backlog items; define sprint goal; assign tasks |
| **Daily Stand-up** | All roles | 15 minutes | Yesterday / Today / Blockers |
| **Sprint Review** | All roles + stakeholders | 1 hour | Demo completed work; gather feedback |
| **Sprint Retrospective** | All roles | 1 hour | What went well / What to improve |
| **Backlog Refinement** | PO + BSA + 1 Developer | 1 hour | Estimate and clarify upcoming stories |

---

## 7. Role-Based Activity Guide

### 7.1 Product Owner

**Goal**: Ensure the team builds the right things in the right order.

#### Step-by-Step Activities

**Sprint Preparation**
1. Review and prioritize all items in the **Backlog**
2. Move the highest-priority items to the top of the backlog
3. Ensure each item has a clear **Summary** and **Description**
4. Assign items to the relevant **Epic**
5. Set **Fix Version** for items aligned to a release milestone

**Sprint Planning**
1. Present top-priority backlog items to the team
2. Confirm Story acceptance criteria with the BSA
3. Agree on the **Sprint Goal** with the Scrum Master
4. Accept the team's capacity estimate and sprint scope

**Sprint Execution**
1. Be available to answer clarifying questions (respond within same day)
2. Review items that move to **Testing/QA** and provide acceptance
3. Mark stories as **Done** only when all acceptance criteria are satisfied

**Sprint Review**
1. Review the demo presented by the developer
2. Accept or reject completed stories
3. Add feedback as comments on tickets; reopen if needed
4. Update the roadmap based on what was completed vs planned

**Example Jira Actions**
```
- Create Epic: [EPIC] Trending and Summary Report Improvements
- Create Story: ST-101 — As a trader, I want email alerts for STRONG_CANDLE
- Set priority: High
- Set Fix Version: v1.2.0
- Link to Epic: EPIC-Trending
```

---

### 7.2 Manager / Scrum Master

**Goal**: Keep the team unblocked, aligned, and delivering at a sustainable pace.

#### Step-by-Step Activities

**Sprint Setup**
1. Create the sprint in Jira: **Board** → **Create Sprint**
   - Name: `Sprint 1 — <Brief Goal>`
   - Start/End dates: 2-week window
2. Confirm team capacity (account for leaves, meetings)
3. Move agreed backlog items into the sprint
4. Verify each sprint item has an **Assignee** and **Story Points**

**Daily Stand-up Facilitation**
1. Open the sprint board before the stand-up
2. Each team member updates their ticket status live
3. Identify and log **blockers** as comments on tickets; add `blocked` label
4. Follow up on blockers same day

**Progress Monitoring**
1. Check the **Burndown Chart** daily (Board → Reports → Burndown Chart)
2. If pace is behind, flag to the team and consider scope adjustment
3. Track velocity across sprints (Board → Reports → Velocity Chart)

**End-of-Sprint**
1. Facilitate **Sprint Review** and **Retrospective**
2. Close the sprint: **Board** → **Complete Sprint**
   - Unfinished items: move back to Backlog or to next sprint
3. Create the next sprint immediately after closing

**Example Jira Actions**
```
- Create Sprint: "Sprint 3 — Alert Notification Retry"
- Move ST-55, ST-56, ST-57 into Sprint 3
- Set sprint capacity: 30 story points
- Add blocker: ST-58 comment "Blocked: waiting for GCP credentials from DevOps"
```

---

### 7.3 BSA (Business System Analyst)

**Goal**: Bridge the gap between business requirements and technical implementation.

#### Step-by-Step Activities

**Requirements Gathering**
1. Meet with the Product Owner to understand business goals
2. Document requirements as **User Stories** in Jira
3. Write **Acceptance Criteria** using the Given/When/Then (GWT) format:
   ```
   Given [context]
   When  [action]
   Then  [expected outcome]
   And   [additional condition]
   ```
4. Tag stories with the appropriate **Component** and **Label**

**Backlog Refinement**
1. Walk developers through stories during refinement sessions
2. Answer questions; update story descriptions as needed
3. Break large stories into smaller **Sub-tasks** if required
4. Collaborate on story point estimation

**In-Sprint Support**
1. Monitor tickets in **In Progress** — add clarifications as comments
2. When a ticket moves to **In Review**, verify the PR matches the story requirements
3. When a ticket moves to **Testing/QA**, perform functional validation:
   - Test against all acceptance criteria
   - Document findings as comments on the ticket
   - Move to **Done** if passed; move back to **In Progress** with detailed feedback if failed

**Example Jira Actions**
```
Story: ST-112
Summary: As a risk manager, I want a burndown chart in the daily report
         so that I can track sprint progress at a glance.

Acceptance Criteria:
  Given a sprint is active
  When the daily report is generated
  Then a burndown chart section is included
  And the chart shows planned vs actual points by day
  And the report is sent to the configured email recipients

Component: tools
Label: type:feature, priority:medium
Story Points: 5
```

---

### 7.4 Developer

**Goal**: Deliver working, tested, and documented code that meets the story's acceptance criteria.

#### Step-by-Step Activities

**Picking Up a Ticket**
1. Go to **Board** → **To Do** column
2. Select the highest-priority ticket assigned to you (or self-assign an unassigned one)
3. Read the full story description and acceptance criteria
4. Ask clarifying questions as **Jira comments** (tag `@BSA` or `@ProductOwner`)
5. Move ticket to **In Progress**

**Development Workflow**
1. Create a Git branch following the naming convention:
   ```
   <ticket-id>/<short-description>
   # Example:
   git checkout -b ST-42/implement-cva-analyzer
   ```
2. Implement the feature following the project architecture:
   - New alert approach → follow [`CREATING_NEW_APPROACH.md`](../IMPLEMENTATION/CREATING_NEW_APPROACH.md)
   - Code quality → follow [`CODE_QUALITY_STANDARDS.md`](../STANDARDIZATIONS/CODE_QUALITY_STANDARDS.md)
3. Write tests in `tests/` following [`STANDARD_TESTING_CONVENTION.md`](../STANDARDIZATIONS/STANDARD_TESTING_CONVENTION.md)
4. Reference the Jira ticket ID in every commit message:
   ```
   ST-42: Implement ConsistentVolumeAnchorAnalyzer
   ST-42: Add unit tests for CVA anchor detection
   ```
5. Push branch and open a Pull Request (PR):
   - PR title: `ST-42 — Implement CVA Analyzer`
   - PR description: include ticket link and summary of changes

**Code Review**
1. Move ticket to **In Review** when PR is ready
2. Address all review comments with follow-up commits
3. Re-request review after changes; add comment on Jira ticket when PR is updated

**After Merge**
1. Verify the feature works on the staging environment
2. Move ticket to **Testing/QA** and notify the BSA
3. If a bug is found during QA, create a **Bug** ticket linked to the original story and fix it promptly

**Example Jira Actions**
```
1. Assign ST-42 to yourself
2. Move ST-42: To Do → In Progress
3. Git: git checkout -b ST-42/implement-cva-analyzer
4. Commit: "ST-42: Implement ConsistentVolumeAnchorAnalyzer"
5. Open PR titled "ST-42 — CVA Analyzer Implementation"
6. Move ST-42: In Progress → In Review
7. After approval: merge PR
8. Move ST-42: In Review → Testing/QA
```

---

## 8. Label & Component Conventions

### Story Point Scale (Fibonacci)

| Points | Complexity | Estimated Effort |
|--------|-----------|-----------------|
| 1 | Trivial | < 1 hour |
| 2 | Simple | 1–3 hours |
| 3 | Small | half day |
| 5 | Medium | 1 day |
| 8 | Large | 2–3 days |
| 13 | Complex | 1 week |
| 21 | Very large — should be split | > 1 week |

### Priority Mapping

| Priority | Meaning | SLA (In Progress → Done) |
|----------|---------|--------------------------|
| 🔴 Critical | System down / data loss | Same day |
| 🟠 High | Core feature blocked | 1–2 days |
| 🟡 Medium | Normal sprint work | Within sprint |
| 🟢 Low | Nice-to-have / docs | Next sprint |

---

## 9. Linking Jira Tickets to Git Commits

### Commit Message Convention

Every commit must reference the Jira ticket ID:

```
<TICKET-ID>: <Imperative short description>

[Optional body explaining WHY, not WHAT]
```

**Examples**:
```bash
ST-42: Implement ConsistentVolumeAnchorAnalyzer
ST-55: Fix retry logic for failed email notifications
ST-88: Refactor SymbolAlertManager to support dynamic approaches
ST-101: Add unit tests for VolumeThresholdValidator
```

### Branch Naming Convention

```
<ticket-id>/<short-kebab-case-description>

Examples:
  ST-42/implement-cva-analyzer
  ST-55/fix-email-retry-logic
  ST-88/refactor-symbol-alert-manager
  ST-101/add-volume-threshold-tests
```

### Pull Request Naming Convention

```
ST-<number> — <Short descriptive title>

Examples:
  ST-42 — Implement CVA Alert Approach
  ST-55 — Fix Email Notification Retry Logic
```

### GitHub ↔ Jira Integration (Optional)

To automatically update Jira ticket status from GitHub:

1. Go to Jira → **Project Settings** → **GitHub for Jira** (or use the Atlassian Marketplace app)
2. Connect your GitHub organization
3. Once connected, Jira will automatically:
   - Detect commits and PRs containing `ST-<number>`
   - Link them to the matching ticket
   - Update the **Development** panel on the ticket

---

## 10. Quick-Start Checklist

### 🟣 Product Owner
- [ ] Create a Jira project with key `ST`
- [ ] Create at least 3 Epics covering the main project themes
- [ ] Add 10+ Stories to the Backlog with priority and Fix Version set
- [ ] Refine the top 5 Stories with the BSA before Sprint Planning

### 🔵 Manager / Scrum Master
- [ ] Create Sprint 1 in Jira with a clear Sprint Goal
- [ ] Verify all sprint items have Assignees and Story Points
- [ ] Schedule recurring Sprint ceremonies in the team calendar
- [ ] Set up the Burndown Chart as the team's daily health check

### 🟢 BSA
- [ ] Write User Stories using the "As a… I want… so that…" format
- [ ] Add Given/When/Then Acceptance Criteria to every Story
- [ ] Link each Story to its parent Epic
- [ ] Assign the correct Component and Labels to each ticket

### 🔴 Developer
- [ ] Assign yourself to a "To Do" ticket → move it to "In Progress"
- [ ] Create a branch: `ST-<number>/<description>`
- [ ] Reference the ticket ID in every commit message
- [ ] Open a PR titled `ST-<number> — <Description>` and move ticket to "In Review"
- [ ] After merge, move ticket to "Testing/QA" and notify the BSA

---

## 📚 Related Documentation

| Document | Description |
|----------|-------------|
| [`CREATING_NEW_APPROACH.md`](../IMPLEMENTATION/CREATING_NEW_APPROACH.md) | How to implement a new alert trading approach |
| [`CODE_QUALITY_STANDARDS.md`](../STANDARDIZATIONS/CODE_QUALITY_STANDARDS.md) | Code quality rules developers must follow |
| [`STANDARD_TESTING_CONVENTION.md`](../STANDARDIZATIONS/STANDARD_TESTING_CONVENTION.md) | Testing conventions for this project |
| [`DEVELOPER_ONBOARDING_GUIDE.md`](../../ARCHITECTURE/README.md) | Architecture learning path for new developers |
| [`SETUP_AND_RUN_GUIDE.md`](../GUIDE_TO_RUN/SETUP_AND_RUN_GUIDE.md) | Local environment setup and run instructions |

---

**Last Updated**: March 2026  
**Maintained By**: Project Team  
**Status**: ✅ Ready for Use
