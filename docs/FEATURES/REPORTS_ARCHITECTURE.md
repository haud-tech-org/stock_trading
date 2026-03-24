# Reports Directory Separation: Visual Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     STOCK TRADING ALERTER SYSTEM                     │
└─────────────────────────────────────────────────────────────────────┘

                          Configuration Layer
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
         DEBUG_REPLAY_START_TIME             Other Settings
            ▼ (Control Point)                   ▼
         ┌──────────────────────┐            ┌──────┐
         │  None = LIVE MODE    │            │ MODE │
         │  Set = REPLAY MODE   │            │ etc. │
         └──────────┬───────────┘            └──────┘
                    │
                    ▼
      ┌─────────────────────────────┐
      │ get_reports_directory_name()│  ◄─── NEW UTILITY FUNCTION
      │                             │
      │ Returns: "reports" or       │
      │          "reports_replay"   │
      └────────────┬────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
      "reports/"        "reports_replay/"
      (LIVE MODE)       (REPLAY MODE)
         │                   │
         ├─ VN30/           ├─ VN30/
         │  ├─ deployment/  │  ├─ deployment/
         │  │  ├─ vra/      │  │  ├─ vra/
         │  │  └─ ...       │  │  └─ ...
         │  └─ dev/         │  └─ dev/
         │                  │
         └─ VN30F1M/        └─ VN30F1M/
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         ALERT NOTIFICATION FLOW                       │
└──────────────────────────────────────────────────────────────────────┘

1. ALERT GENERATION
   ────────────────
   SymbolAlerter._run_deployment_mode()
           │
           ▼
   TimeSimulator created
   Check: DEBUG_REPLAY_START_TIME
   │
   ├─ None          ├─ "2026-01-08..."
   │  (LIVE)        │  (REPLAY)
   └─────┬──────────┴─────┐
         │                │
         ▼                ▼
   _perform_monitoring_session()
           │
           ▼
   executor.run() → AlertResult
           │
   ┌───────┴───────┐
   ▼               ▼
LIVE MODE      REPLAY MODE
│               │
├─ Real-time    ├─ Historical
├─ Live API     ├─ Live API (simulated time)
└─ Continuous   └─ Time window


2. ALERT ENRICHMENT
   ────────────────
   NotificationManager.process_and_notify(result, symbol)
           │
           ├─ Extract latest alert
           ├─ Check duplicates
           ├─ Enrich with prices
           └─ Send notifications


3. REPORT PERSISTENCE
   ───────────────────
   save_alert_report(result, symbol, date_str)
           │
           ▼
   ┌──────────────────────┐
   │ get_reports_directory│
   │ _name()              │  ◄─── CHECKS DEBUG_REPLAY_START_TIME
   └──────────┬───────────┘
              │
      ┌───────┴───────┐
      │               │
      ▼               ▼
   reports/      reports_replay/
   (LIVE)        (REPLAY)
      │               │
      ▼               ▼
   {symbol}/     {symbol}/
   {mode}/       {mode}/
   {approach}/   {approach}/
      │               │
      └───────┬───────┘
              ▼
   alert_notification_{date}.json
   (Different directories)
```

---

## Function Call Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│         TOP-LEVEL FUNCTIONS (Using New Logic)               │
└─────────────────────────────────────────────────────────────┘
            │
    ┌───────┼───────┬──────────────┐
    │       │       │              │
    ▼       ▼       ▼              ▼
save_alert_ update_ save_prof     get_consol.
report()    summary() itability    _scenario_
                    _report()      directory()
    │       │       │              │
    └───────┼───────┼──────────────┘
            │
    ┌───────▼────────────────────────────┐
    │  get_reports_directory_name()      │  ◄─── NEW CORE FUNCTION
    │                                    │
    │  Checks: settings.                 │
    │          DEBUG_REPLAY_START_TIME   │
    │                                    │
    │  Returns: "reports"     (LIVE)     │
    │        or "reports_replay" (REPLAY)│
    └────────────────────────────────────┘
```

---

## Mode Selection Logic

```
┌──────────────────────────────────────────────────────────────┐
│              CONFIGURATION-DRIVEN MODE SELECTION              │
└──────────────────────────────────────────────────────────────┘

START
  │
  ▼
Read settings.DEBUG_REPLAY_START_TIME
  │
  ├─────────────┬──────────────────────────────┐
  │             │                              │
  ▼             ▼                              ▼
None         "2026-01-08 09:05:00"          Other values
  │             │                              │
  ▼             ▼                              ▼
LIVE MODE   REPLAY MODE                    REPLAY MODE
  │             │                              │
  ├─────────────┴──────────────────────────────┤
  │                                            │
  ▼                                            ▼
"reports" directory            "reports_replay" directory
  │                                            │
  ├─ Live API fetch          ├─ Live API with
  ├─ Real-time monitoring    │  simulated time
  ├- Continuous operation    ├─ Backtesting
  └─ Production use          └─ Strategy validation
```

---

## Quick Navigation

| Document | Purpose | Location |
|----------|---------|----------|
| **This Document** | Visual Architecture & Diagrams | REPORTS_ARCHITECTURE.md |
| **Detailed Guide** | Complete Implementation Details | REPORTS_DIRECTORY_SEPARATION.md |
| **Quick Reference** | At-a-glance Usage Guide | REPORTS_SEPARATION_QUICK_REFERENCE.md |
| **Summary** | Implementation Completion Report | IMPLEMENTATION_COMPLETE.md |

---

**Version**: 1.0  
**Date**: March 24, 2026  
**Status**: ✅ Complete  
**Next Step**: Ready for deployment
