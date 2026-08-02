# ISP-Monitor

Dual-ISP uptime and latency monitor with SMS/email alerting. Built for home labs and small offices running failover setups.

---

## The setup it's designed for

```
          ┌─────────────┐
          │   Router    │
          └──────┬──────┘
         ┌───────┴────────┐
    ISP-1 (Primary)    ISP-2 (Backup)
    Jio Fiber          Airtel 4G
    100 Mbps           40 Mbps
```

ISP-Monitor pings both uplinks every 30 seconds, logs latency, and fires an alert the moment either one drops — before your users notice.

---

## What it monitors

- **Uptime** — per-ISP availability percentage (daily, weekly, monthly)
- **Latency** — rolling average, P95, spike detection
- **Failover events** — timestamp, duration, which ISP went down
- **SLA tracking** — how many 9s is each ISP actually delivering?

---

## Alerts

Configure once in `config.json`:

```json
{
  "alert_email": "you@example.com",
  "alert_sms": "+91-XXXXXXXXXX",
  "smtp_host": "smtp.gmail.com",
  "down_threshold_ms": 500,
  "alert_cooldown_minutes": 5
}
```

Alert fires when:
- ISP goes down (ping loss > 90% over 60s)
- Latency spikes above threshold
- ISP comes back up (recovery notification)

---

## Run it

```bash
git clone https://github.com/SRINIVASAN55/ISP-Monitor
cd ISP-Monitor
pip install -r requirements.txt
cp config.sample.json config.json   # edit with your settings

python isp_monitor.py               # starts monitoring both ISPs
python isp_monitor.py --report      # shows uptime stats for last 30 days
python isp_monitor.py --dashboard   # live terminal view
```

---

## Terminal output

```
ISP Monitor  |  2024-01-15 14:23:01
─────────────────────────────────────────────
ISP-1  Jio Fiber    ● UP    12ms   99.97% (30d)
ISP-2  Airtel 4G   ● UP    38ms   98.41% (30d)

Last failover: 2024-01-12 03:14 → 03:19 (5 min) — ISP-1 outage
```

---

**Author:** S. Srinivasan · [GitHub](https://github.com/SRINIVASAN55) · [LinkedIn](https://linkedin.com/in/srinivasan132)
