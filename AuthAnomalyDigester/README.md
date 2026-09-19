# AuthAnomalyDigester

Read-only **authentication log anomaly digester** CLI for portfolio / IR hygiene demos.

It parses Linux `auth.log` / `secure`-style SSH & sudo lines and exported Windows Security events (4624/4625), then flags likely anomalies: brute-force bursts, odd-hour successes, and new source IPs.

```
========================================================================
  READ-ONLY ANALYSIS OF FILES YOU PROVIDE  |  AUTHORIZED USE ONLY
  No live network attacks. No credential guessing. Portfolio / IR hygiene.
========================================================================
```

**Author:** Zach Telford ([ztel42](https://github.com/ztel42))

---

## Disclaimer

- Use only on **log files you own or are explicitly authorized** to analyze.
- This tool is **read-only by design**. It does **not** connect to hosts, attempt logons, or modify logs.
- Findings are heuristic review signals, not a full SIEM or incident-response conclusion.
- Binary `.evtx` is **not** parsed directly — export to CSV or XML text first (Event Viewer, `wevtutil`, or `Get-WinEvent`).

---

## Features

| Detector | Default | What it flags |
| --- | --- | --- |
| **Brute force** | 10 failures / 10 minutes | Many failures from the same source IP **or** against the same account within a sliding window |
| **Odd hours** | outside 07:00–21:00 | Successful logons outside a configurable local-hour window |
| **New source IP** | `--baseline` or first-seen | Successful logon from an IP not in a baseline file; without baseline, each distinct success IP is noted as first-seen-in-file |

### Outputs

- Console summary (banner + counts + top findings)
- `--json PATH` full report
- `--csv PATH` findings table

---

## Formats supported

1. **Linux auth / syslog-style** — SSH failed/accepted password or publickey; sudo failure/success (`auth.log`, `secure`, and similar exports).
2. **Windows Security exports** — CSV and simple XML / EVTX-export text with Event IDs **4624** (success) and **4625** (failure). Prefer CSV/XML fixtures for tests and demos.

Auto-detect with `--format auto` (default), or force `--format linux` / `--format windows`.

---

## Requirements

- Python 3.10+ (stdlib only for the digester; `pytest` for tests)

---

## Usage

```bash
# From the project directory
python -m auth_anomaly_digester /var/log/auth.log

# Windows CSV export + reports
python -m auth_anomaly_digester security_export.csv --format windows \
  --json report.json --csv findings.csv

# Baseline of known-good IPs (one per line)
python -m auth_anomaly_digester auth.log --baseline known_ips.txt

# Tune detectors
python -m auth_anomaly_digester auth.log \
  --bf-threshold 10 --bf-window 10 \
  --odd-start 7 --odd-end 21
```

### Fixture demo

```bash
python -m auth_anomaly_digester tests/fixtures/auth.log \
  --baseline tests/fixtures/baseline_ips.txt \
  --json /tmp/aad.json --csv /tmp/aad.csv
```

---

## Tests

```bash
pip install -r requirements.txt
python -m pytest
```

Tests are offline and use snippets under `tests/fixtures/` (SSH failures, sudo, Windows 4625/4624 CSV/XML).

---

## Layout

```
AuthAnomalyDigester/
  auth_anomaly_digester/
    parsers/          # linux_auth, windows_security
    detectors/        # brute_force, odd_hours, new_source
    report.py
    cli.py
    models.py
  tests/
    fixtures/
  README.md
  requirements.txt
```

---

## License

For portfolio demonstration. Use only with authorized log files.
