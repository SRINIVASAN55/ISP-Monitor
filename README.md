<div align="center">

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   📡  I S P - M O N I T O R                         ║
║   Dual ISP Uptime & Latency Monitor                  ║
║                                                      ║
║   ● ISP-1 (Primary)   UP    ▲▲▲▲▲▲▲▲▲▲  12ms       ║
║   ● ISP-2 (Backup)    DOWN  ▲▲▲~~▼▼▼▼▲  ---         ║
║                                                      ║
║   [CRITICAL] ISP-2 is DOWN — Email sent to IT team  ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

[![Python](https://img.shields.io/badge/Python-stdlib_only-brightgreen?style=flat-square&logo=python&logoColor=white)]()
[![Platform](https://img.shields.io/badge/Linux_%7C_Windows_%7C_macOS-blue?style=flat-square)]()
[![Alerts](https://img.shields.io/badge/Email_Alerts-HTML_%2B_Plain-red?style=flat-square)]()
[![Threads](https://img.shields.io/badge/Multithreaded-One_per_ISP-orange?style=flat-square)]()

</div>

---

## 💡 The Problem It Solves

You have two ISPs for redundancy. One goes down at 3am. Nobody knows until users call. By then it's been down 2 hours.

**ISP-Monitor** fixes that — it watches both links 24/7, detects failures within 90 seconds, and fires an HTML email to your whole IT team automatically.

---

## ⚡ Quickstart

```bash
git clone https://github.com/SRINIVASAN55/ISP-Monitor
cd ISP-Monitor

# Run instantly — monitors 8.8.8.8 and 1.1.1.1 by default
python isp_monitor.py

# Your actual ISP gateways
python isp_monitor.py --isp1 192.168.1.1 --isp2 10.0.0.1

# With email alerts (Gmail app password)
python isp_monitor.py \
  --isp1 192.168.1.1 --isp2 10.0.0.1 \
  --smtp-host smtp.gmail.com \
  --smtp-user alerts@yourdomain.com \
  --smtp-pass YOUR_APP_PASSWORD \
  --recipients it@company.com noc@company.com

# Generate and customize config file
python isp_monitor.py --generate-config
python isp_monitor.py --config config.json
```

---

## 📺 Live Dashboard

```
  Last Update: 2024-01-15 10:34:01
  ────────────────────────────────────────────────────────
  ISP-1 (Primary)       ● UP          12.3 ms    0% loss
    History: ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

  ISP-2 (Backup)        ✖ DOWN  (DOWN 00h:02m:14s)
    History: ▲▲▲▲▲▲▲▲~~▼▼▼▼▼▼▼▼▼▼

  Check interval: 30s  |  Email alerts: ON
```

---

## 📧 Alert Email (HTML)

Three alert types are sent automatically:

| Trigger | Level | Subject |
|---|---|---|
| Link goes down | 🔴 CRITICAL | `ISP-1 (Primary) is DOWN — No connectivity` |
| Latency spike / packet loss | 🟡 WARNING | `ISP-2 DEGRADED — High latency / Packet loss` |
| Link comes back | 🟢 RECOVERY | `ISP-1 RECOVERED — Link is back UP (downtime: 2m14s)` |

---

## ⚙️ Smart Features

- **Flap prevention** — requires N consecutive failures before changing state (no false alarms)  
- **Alert cooldown** — won't spam your inbox; configurable cooldown per alert type  
- **Backup host fallback** — if primary gateway is unreachable, tries backup IPs before declaring DOWN  
- **Sparkline history** — visual ▲▼~ history per ISP in the terminal dashboard  
- **Structured JSON logs** — every check event written to `isp_events.json`

---

<p align="center">
Built by <a href="https://github.com/SRINIVASAN55">SRINIVASAN55</a> ·
<a href="https://linkedin.com/in/srinivasan132">LinkedIn</a>
</p>
