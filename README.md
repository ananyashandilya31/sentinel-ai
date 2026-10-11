 🛡️ SentinelAI — AI-Powered Security Operations Center (SOC)

> A real-time cybersecurity platform that ingests server/network logs, detects known attacks with rule-based logic, finds unknown/unusual behaviour with machine learning, enriches suspicious IPs with threat intelligence, and uses an LLM to explain incidents to security analysts.

**Status:** 🚧 In development — Phase 4: ML Anomaly Detection Completed ✅ (30-day build plan)
**Type:** Full-stack + Machine Learning + Generative AI project

---

## 📑 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Objectives](#3-objectives)
4. [Key Features](#4-key-features)
5. [System Architecture](#5-system-architecture)
6. [Tech Stack and Why I Chose It](#6-tech-stack-and-why-i-chose-it)
7. [Log Ingestion and Dataset](#7-log-ingestion-and-dataset)
8. [Rule-Based Detection Engine](#8-rule-based-detection-engine)
9. [ML Anomaly Detection](#9-ml-anomaly-detection)
10. [Threat Intelligence Enrichment](#10-threat-intelligence-enrichment)
11. [AI Incident Investigation (GenAI)](#11-ai-incident-investigation-genai)
12. [Real-Time Alerting](#12-real-time-alerting)
13. [Frontend / SOC Dashboard](#13-frontend--soc-dashboard)
14. [Database Design](#14-database-design)
15. [API Design](#15-api-design)
16. [Project Structure](#16-project-structure)
17. [Setup and Installation](#17-setup-and-installation)
18. [Testing Strategy](#18-testing-strategy)
19. [Security of the Platform Itself](#19-security-of-the-platform-itself)
20. [Development Roadmap](#20-development-roadmap-30-days)
21. [Challenges and Limitations](#21-challenges-and-limitations)
22. [Future Scope](#22-future-scope)
23. [Resume Bullet Points](#23-resume-bullet-points)
24. [Interview Questions I Should Be Ready For](#24-interview-questions-i-should-be-ready-for)
25. [Conclusion](#25-conclusion)

---

## 1. Project Overview

SentinelAI is my take on a mini **Security Operations Center (SOC)**. In a real company, a SOC team watches thousands of logs every day (logins, network connections, file transfers) and tries to spot attacks before they cause damage. Doing this by hand is impossible, so tools are needed.

SentinelAI does four things together:

1. **Collects** security logs (login attempts, data transfers, port connections, etc.)
2. **Detects** attacks using two methods:
   - **Rules** for known attack patterns (brute force, port scan, data exfiltration)
   - **Machine Learning** (Isolation Forest) for unusual behaviour that no rule covers
3. **Enriches** suspicious IPs with reputation, location and risk score
4. **Explains** each incident in plain English using an LLM, so an analyst can act quickly

The most important design decision: **the AI is an analyst assistant, not the detector.** Detection is done by rules + ML. The LLM only receives structured evidence and writes the explanation. This keeps the system reliable and explainable.

---

## 2. Problem Statement

Security teams face three real problems:

- **Alert overload** — thousands of logs and alerts, most of them harmless.
- **Unknown attacks** — rules only catch what someone already thought of. New or subtle attacks slip through.
- **Slow investigation** — an analyst has to manually collect evidence from many places before understanding what happened.

**SentinelAI tackles this** by combining rules (precision on known attacks), ML (coverage of unknown behaviour) and GenAI (faster understanding of incidents).

---

## 3. Objectives

- Build a complete log → detection → incident → explanation pipeline.
- Implement at least 5 rule-based detections.
- Train and evaluate an unsupervised ML model for anomaly detection.
- Add threat intelligence enrichment for suspicious IPs.
- Use an LLM to generate incident summaries and recommended investigation steps.
- Build a real-time SOC dashboard with live alerts.
- Containerise and deploy the whole system.
- Document it well enough to explain every design choice in an interview.

---

## 4. Key Features

| Feature | Description |
|---|---|
| Log ingestion | API + file/CSV ingestion, validation and storage |
| Rule engine | Brute force, port scan, data exfiltration, account compromise, privilege escalation |
| ML anomaly detection | Isolation Forest with anomaly score 0–1 per event/user window |
| Threat intelligence | IP reputation, geolocation, risk score |
| AI investigation | LLM-generated incident summary, evidence list, recommended actions |
| Real-time alerts | WebSocket push to the dashboard instantly |
| SOC dashboard | Incident counts, live feed, charts, filters, incident detail view |
| Authentication | JWT login with role-based access (admin / analyst) |
| Analytics | Attack trends, most targeted users and IPs, anomaly timeline |
| Deployment | Dockerised, runs with one `docker-compose up` |

---

## 5. System Architecture

```text
┌───────────────┐      ┌────────────────────────────────────────────────┐
│  Log Sources  │      │                 FastAPI Backend                │
│ (generated /  │ ───► │                                                │
│  CSV / API)   │      │  Ingestion ─► Validation ─► PostgreSQL         │
└───────────────┘      │                   │                            │
                       │                   ▼                            │
                       │        ┌─────────────────────┐                 │
                       │        │  Detection Layer    │                 │
                       │        │  • Rule Engine      │                 │
                       │        │  • ML (Isolation    │                 │
                       │        │    Forest)          │                 │
                       │        └─────────┬───────────┘                 │
                       │                  ▼                             │
                       │        Incident Builder                        │
                       │                  │                             │
                       │      ┌───────────┼─────────────┐               │
                       │      ▼           ▼             ▼               │
                       │ Threat Intel   LLM        WebSocket Manager    │
                       │ (IP enrich)  (explain)     (live alerts)       │
                       └──────────────────┬─────────────────────────────┘
                                          ▼
                              ┌─────────────────────┐
                              │ React + Vite SOC UI │
                              └─────────────────────┘
```

### Data flow in simple words

1. A log arrives (e.g. `LOGIN_FAILED` for `admin` from `185.23.41.12`).
2. It's validated and saved in PostgreSQL.
3. The rule engine checks it against known attack patterns.
4. The feature builder converts recent activity into numbers, and the ML model scores it.
5. If something is suspicious, an **incident** is created and linked to its evidence.
6. The IP is enriched with threat intelligence.
7. The LLM gets the structured evidence and writes the explanation.
8. A WebSocket message pushes the new incident to every connected dashboard.

---

## 6. Tech Stack and Why I Chose It

| Layer | Technology | Why |
|---|---|---|
| Frontend | **React + Vite** | I already know React, and Vite gives fast setup and hot reload. Next.js would add SSR complexity I don't need for a dashboard. |
| Charts | **Recharts** | Simple, React-native charting for trends and distributions. |
| Backend | **FastAPI** | Fast, async, automatic API docs (Swagger), great Pydantic validation, native WebSocket support. |
| Database | **PostgreSQL** | Relational data (users → logs → incidents → evidence) fits well; strong indexing and time-range queries. |
| ORM | **SQLAlchemy + Alembic** | Clean models and database migrations. |
| ML | **Python + scikit-learn** | Standard, well-documented, perfect for Isolation Forest. |
| Data handling | **pandas, NumPy** | Feature engineering and dataset generation. |
| GenAI | **LLM API** | Turns structured evidence into readable incident reports. |
| Real-time | **WebSockets** | Push alerts instantly instead of polling. |
| Auth | **JWT** | Stateless authentication with roles. |
| Testing | **pytest** | Unit and API tests. |
| DevOps | **Docker + docker-compose** | Reproducible environment, easy deployment. |

---

## 7. Log Ingestion and Dataset

Since I don't have a real company's infrastructure, I'll **generate a realistic synthetic dataset** with normal behaviour plus injected attacks.

### Log schema

| Field | Type | Example |
|---|---|---|
| `id` | UUID | auto |
| `timestamp` | datetime | `2026-10-01 10:31:12` |
| `user` | string | `admin` |
| `ip` | string | `185.23.41.12` |
| `event_type` | enum | `LOGIN_FAILED`, `LOGIN_SUCCESS`, `DATA_TRANSFER`, `PORT_CONNECT`, `PRIVILEGE_CHANGE` |
| `port` | int (nullable) | `22` |
| `bytes_transferred` | bigint (nullable) | `850000000` |
| `country` | string | `RU` |
| `session_id` | string | `s-8841` |

### Example raw logs

```text
2026-10-01 10:31:12 user=admin ip=185.23.41.12 event=LOGIN_FAILED
2026-10-01 10:35:42 user=admin ip=185.23.41.12 event=DATA_TRANSFER bytes=850000000
```

### Dataset generator

A Python script (`data/generate_logs.py`) will create:

- **Normal behaviour:** users logging in during office hours from known IPs, small transfers (~20 MB).
- **Injected attacks:** brute-force bursts, port scans, huge transfers, logins from new countries at odd hours.
- **Labels (hidden from the model):** each injected attack row is tagged so I can *evaluate* the unsupervised model afterwards.

---

## 8. Rule-Based Detection Engine

Rules catch **known** attack patterns. They're fast, precise and easy to explain.

| Rule | Logic | Severity |
|---|---|---|
| **Brute Force** | ≥ 8 `LOGIN_FAILED` for same user + same IP within 2 minutes | HIGH |
| **Port Scan** | 1 IP touching ≥ 20 different ports within 30 seconds | MEDIUM |
| **Data Exfiltration** | Transfer much larger than the user's baseline (e.g. 900 MB vs ~20 MB average) | CRITICAL |
| **Account Compromise** | Many failed logins → successful login → new IP → large transfer | HIGH / CRITICAL |
| **Privilege Escalation** | Normal user suddenly gets admin rights or accesses admin resources | HIGH |

### How it's implemented

- Each rule is a separate class with a common interface: `evaluate(events) -> list[Alert]`.
- A **sliding time window** groups recent events per user/IP.
- Rules are configurable (thresholds in a config file), so they can be tuned without changing code.

---

## 9. ML Anomaly Detection

Rules can't catch what nobody wrote a rule for. That's where ML comes in.

### 9.1 Why Isolation Forest?

- **Unsupervised** — real security data rarely has clean labels, and Isolation Forest doesn't need them.
- Designed for **anomaly detection**: anomalies are "few and different", so they get isolated in fewer random splits.
- Fast, scales well, and works with mixed numeric features.
- Produces a **score**, not just a yes/no, which is great for ranking incidents.

### 9.2 Feature engineering

Raw logs are converted into per-user (or per-IP) time-window features:

| Feature | Meaning |
|---|---|
| `failed_login_count` | Failed logins in the window |
| `login_frequency` | How often the user logs in |
| `login_hour` | Hour of the day (captures odd-hour logins) |
| `unique_ports` | Distinct ports contacted |
| `data_transfer_mb` | Volume of data transferred |
| `new_ip` | 1 if the IP was never seen for this user |
| `new_country` | 1 if the country is new for this user |
| `session_duration` | Length of the session |

### 9.3 Pipeline

```text
Security Events
      ↓
Feature Engineering (per user per time window)
      ↓
Scaling (StandardScaler)
      ↓
Isolation Forest
      ↓
┌─────┴──────┐
Normal     Anomalous
              ↓
        Anomaly Score (0–1)
```

### 9.4 Anomaly score

The raw score from scikit-learn is normalised to 0–1:

```text
Score 0.93  →  HIGHLY ANOMALOUS
Score 0.55  →  SUSPICIOUS
Score 0.20  →  NORMAL
```

### 9.5 Evaluation

Because I know which synthetic rows are real attacks, I can measure:

- Precision, Recall, F1-score
- Confusion matrix
- ROC-AUC / Precision-Recall curve
- Effect of the `contamination` parameter

Reproduce it offline: `python ml/data/eda.py` (EDA report → `ml/data/eda_report.md`) and `python ml/training/evaluate.py` (full evaluation with contamination sweep → `ml/models/evaluation_report.md`).

I'll be honest in the report: results on synthetic data are a **proof of concept**, not a claim about real-world performance.

### 9.6 Model lifecycle

- Train offline → save with `joblib` → load at API startup → score new events in real time.
- Retraining script kept in `ml/training/` (`python ml/training/train.py`).

---

## 10. Threat Intelligence Enrichment

For every suspicious IP, the system adds context:

| Info | Example |
|---|---|
| Reputation | Known malicious / suspicious / clean |
| Geolocation | Country, city |
| ASN / ISP | Hosting provider or residential |
| Past activity | Number of previous incidents involving this IP |
| **Risk score** | 0–100 combined score |

**Approach:** start with a local `ip_reputation` table (seeded data) so the project runs offline, then optionally plug in a real threat-intel API behind a service interface (so the source can be swapped without touching the rest of the code).

---

## 11. AI Incident Investigation (GenAI)

### Principle

> The LLM does **not** detect attacks. It **explains** them.

### Flow

1. The detection layer builds a **structured evidence object** (JSON): events, timeline, ML score, IP reputation.
2. Only this compact evidence is sent to the LLM, not the whole database. This saves cost, protects data and reduces hallucination.
3. The LLM returns a structured report.

### Example input (simplified)

```json
{
  "user": "admin",
  "ip": "185.23.41.12",
  "events": [
    "8 failed logins",
    "successful login",
    "new IP",
    "850 MB transfer"
  ],
  "anomaly_score": 0.93,
  "ip_risk_score": 87
}
```

### Example output

```text
INCIDENT: Possible Account Compromise
Severity: HIGH

Evidence:
• 8 failed authentication attempts
• Successful login from an unfamiliar IP
• 850 MB outbound transfer
• Activity outside normal login hours

Recommended investigation:
• Verify the user's identity
• Review accessed resources
• Investigate the source IP
• Review subsequent network activity
```

### Safety measures

- Strict prompt: "use only the provided evidence, do not invent facts".
- Output validated against a schema.
- Fallback: if the LLM fails, a template-based summary is shown.
- No secrets or unnecessary personal data are sent.

---

## 12. Real-Time Alerting

- FastAPI **WebSocket endpoint** keeps a connection open with each dashboard.
- When a new incident is created, the server **broadcasts** it instantly.
- The React app updates counters, the incident list and shows a notification, with no page refresh.
- Connection handling: authentication on connect, auto-reconnect on the client.

---

## 13. Frontend / SOC Dashboard

Built with **React + Vite**, styled like a real SOC console (dark theme, severity colours).

### Pages

| Page | Contents |
|---|---|
| **Login** | JWT authentication |
| **Dashboard** | Critical/High/Medium counters, total events, active incidents, live activity chart |
| **Events** | All logs with search, filters, time range, pagination |
| **Incidents** | Active incidents with severity, status, assigned analyst |
| **Incident Details** | Timeline, evidence, ML score, IP reputation, AI explanation, status controls |
| **Threat Intelligence** | IP lookup, geographic info, risk score |
| **Analytics** | Attack frequency, attack types, anomaly trends, most targeted users/IPs |

### Dashboard layout

```text
┌──────────────────────────────────────────────┐
│ SENTINELAI                    ● SYSTEM ACTIVE│
├──────────────────────────────────────────────┤
│  CRITICAL     HIGH      MEDIUM      EVENTS   │
│      3          12         37        12,482  │
├──────────────────────────────────────────────┤
│ ACTIVE INCIDENTS                             │
│ 🔴 Account Compromise        HIGH            │
│ 🟠 Port Scan                 MEDIUM          │
│ 🔴 Data Exfiltration         CRITICAL        │
├──────────────────────────────────────────────┤
│ EVENT ACTIVITY                               │
│          📈                                  │
└──────────────────────────────────────────────┘
```

---

## 14. Database Design

```text
users
   │
   ├── logs
   │
   └── incidents
          │
          ├── alerts
          ├── evidence
          └── investigations

ip_reputation
threat_types
ml_predictions
```

### Main tables

| Table | Key columns |
|---|---|
| `users` | id, username, email, password_hash, role |
| `logs` | id, timestamp, user, ip, event_type, port, bytes_transferred, country, session_id |
| `alerts` | id, rule_name, severity, log_id, created_at |
| `incidents` | id, title, type, severity, status, assigned_to, created_at, updated_at |
| `evidence` | id, incident_id, log_id, description |
| `investigations` | id, incident_id, ai_summary, recommended_actions, created_at |
| `ip_reputation` | ip, reputation, country, asn, risk_score, last_seen |
| `threat_types` | id, name, description, default_severity |
| `ml_predictions` | id, log_id/window_id, anomaly_score, label, model_version |

### Design notes

- **Indexes** on `timestamp`, `ip`, `user`, `event_type` for fast filtering.
- Foreign keys keep incidents ↔ evidence ↔ logs consistent.
- Migrations managed with Alembic.
- `model_version` in `ml_predictions` allows comparing model versions later.

---

## 15. API Design

Base path: `/api/v1`

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/login` | Get JWT token |
| POST | `/auth/register` | Create user (admin only) |
| POST | `/logs` | Ingest one log |
| POST | `/logs/bulk` | Ingest many logs |
| GET | `/logs` | List logs (filters, search, pagination) |
| GET | `/incidents` | List incidents |
| GET | `/incidents/{id}` | Incident details with evidence |
| PATCH | `/incidents/{id}` | Update status / assignee |
| POST | `/incidents/{id}/investigate` | Trigger AI explanation |
| GET | `/threat-intel/{ip}` | IP reputation and risk score |
| GET | `/analytics/summary` | Dashboard counters |
| GET | `/analytics/attacks` | Attack frequency and types |
| GET | `/ml/predictions` | Recent anomaly scores |
| WS | `/ws/alerts` | Live incident stream |

FastAPI automatically provides interactive docs at `/docs`.

---

## 16. Project Structure

```text
sentinel-ai/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── dashboard/
│   │   └── services/
│   └── package.json
│
├── backend/
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── detection/
│   └── main.py
│
├── ml/
│   ├── data/
│   ├── preprocessing/
│   ├── training/
│   ├── models/
│   └── inference/
│
├── data/
│   └── security_logs.csv
│
├── docker/
├── tests/
├── README.md
└── docker-compose.yml
```

---

## 17. Setup and Installation

> These are the planned steps. I'll update them as each phase gets completed.

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (or Docker)
- Git
- An LLM API key

### Clone

```bash
git clone https://github.com/<your-username>/sentinel-ai.git
cd sentinel-ai
```

### Environment variables (`.env`)

```env
DATABASE_URL=postgresql://user:password@localhost:5432/sentinel
JWT_SECRET=change_me
JWT_EXPIRE_MINUTES=60
LLM_API_KEY=your_key_here
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

API docs: `http://localhost:8000/docs`

### Generate data and train model

```bash
python data/generate_logs.py
python ml/training/train.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: `http://localhost:5173`

### Run everything with Docker

```bash
docker-compose up --build
```

---

## 18. Testing Strategy

| Type | What | Tool |
|---|---|---|
| Unit tests | Each detection rule with crafted event sequences | pytest |
| ML tests | Feature builder output, model loads and scores correctly | pytest |
| API tests | Auth, ingestion, filters, incident endpoints | pytest + FastAPI TestClient |
| LLM tests | Prompt builder and output parser (LLM mocked) | pytest |
| Frontend | Key components and API service calls | Vitest / React Testing Library |
| Manual / E2E | Inject an attack and watch it appear live on the dashboard | Browser |

**Target:** meaningful coverage of the detection engine, since that's the core of the product.

---

## 19. Security of the Platform Itself

A security tool must be secure too:

- Passwords hashed with bcrypt, never stored in plain text
- JWT with expiry and role-based access control
- Input validation with Pydantic on every endpoint
- Parameterised queries via SQLAlchemy (prevents SQL injection)
- CORS restricted to the frontend origin
- Secrets only in environment variables, never in Git
- Rate limiting on login endpoint
- Minimal data sent to the LLM

---

## 20. Development Roadmap (30 Days)

| Phase | Days | Goal | Deliverable | Status |
|---|---|---|---|---|
| **1. Foundation** | 1–2 | Repo, FastAPI, React+Vite, PostgreSQL, first API | Working skeleton with DB connection | ✅ Completed |
| **2. Security logs** | 3–5 | Schema, log generator, storage, display, search/filter | Events page working | ✅ Completed |
| **3. Detection engine** | 6–10 | Brute force, port scan, exfiltration, account compromise, privilege escalation | Alerts and incidents created automatically | ✅ Completed |
| **4. ML** | 11–15 | Feature engineering, EDA, Isolation Forest, scores, evaluation, save/load | Trained model plus evaluation report | ✅ Completed |
| **5. Threat intelligence** | 16–18 | IP reputation, risk scoring, enrichment | Enriched incidents | ⏱️ Planned |
| **6. GenAI** | 19–21 | Summaries, evidence explanation, investigation assistant | AI explanation on incident page | ⏱️ Planned |
| **7. Real-time SOC** | 22–25 | WebSockets, live alerts, live dashboard, notifications | Live dashboard | ⏱️ Planned |
| **8. Polish** | 26–30 | Auth, tests, Docker, deployment, README, diagrams, screenshots, demo video | Resume-ready project | ⏱️ Planned |

---

## 21. Challenges and Limitations

Being upfront about these makes the project more credible:

- **Synthetic data** — good for learning and demos, but real logs are noisier.
- **False positives** — unsupervised models flag unusual-but-harmless behaviour; thresholds need tuning.
- **Cold start** — "new IP/new country" features need some history per user.
- **LLM reliability** — can hallucinate, so it only gets structured evidence and a strict prompt.
- **Scale** — this is a single-node design. Real SOCs use stream processing (Kafka, etc.).
- **Threat intel** — local/seeded data is limited compared with commercial feeds.

---

## 22. Future Scope

- Real log sources (syslog, Windows event logs, cloud logs)
- Kafka / message queue for high-volume streaming
- Additional models (Autoencoder, LSTM for sequences)
- Automated response (block IP, disable account)
- MITRE ATT&CK mapping for each incident
- Email / Slack / Telegram notifications
- Analyst feedback loop (mark false positive → retrain)
- Multi-tenant support
- RAG over past incidents so the AI can say "this looks like incident #42"

---

## 23. Resume Bullet Points

Pick 3–4 depending on the role:

- Built **SentinelAI**, a full-stack AI-powered Security Operations Center that ingests security logs, detects threats and generates analyst-ready incident reports in real time.
- Implemented a **rule-based detection engine** for brute force, port scanning, data exfiltration, account compromise and privilege escalation using sliding time-window analysis.
- Trained an **Isolation Forest** anomaly detection model on engineered behavioural features (failed logins, login hour, data volume, new IP/country), evaluated with precision/recall/F1 on labelled synthetic attacks.
- Integrated an **LLM** to turn structured incident evidence into severity assessments and recommended investigation steps, reducing manual triage effort.
- Developed a **FastAPI + PostgreSQL** backend with JWT authentication and **WebSocket**-based live alerting to a **React** SOC dashboard.
- Containerised the system with **Docker** and deployed it to the cloud with automated tests covering detection logic and APIs.

---

## 24. Interview Questions I Should Be Ready For

**Why Isolation Forest?**
It's unsupervised, so it doesn't need labelled attack data, it's fast, and it gives a continuous anomaly score that I can use to rank incidents.

**Why both rules and ML?**
Rules are precise for known attacks and easy to explain. ML covers unusual behaviour that no rule anticipates. Together they give better coverage than either alone.

**Why not let the LLM detect attacks?**
LLMs aren't deterministic or reliable enough for detection. I use them where they're strongest: explaining structured evidence in clear language.

**How do you reduce hallucination?**
Send only structured evidence, use a strict prompt, validate the output schema and keep a template fallback.

**How did you evaluate the model?**
I generated data with known injected attacks, held those labels out during training, then measured precision, recall, F1 and ROC-AUC. I also noted that synthetic results aren't a real-world guarantee.

**Why WebSockets instead of polling?**
Alerts need to reach analysts instantly; WebSockets push updates without repeated requests.

**Why PostgreSQL?**
The data is relational (users, logs, incidents, evidence) and I need strong indexing for time-range and filter queries.

**How would this scale?**
Add a message queue like Kafka for ingestion, separate detection workers, partition log tables by time, and cache hot queries.

---

## 25. Conclusion

SentinelAI brings together **software engineering, machine learning and generative AI** in a single practical system. It shows that I can design a data pipeline, implement detection logic, train and evaluate an ML model, integrate an LLM responsibly, build a real-time interface and ship it with Docker.

More importantly, every design choice here is something I can explain and defend: what I built, why I built it that way, and where its limits are.

---

## 📄 License

MIT License (or whichever you choose).

## 👤 Author

**Ananya** — [GitHub](https://github.com/) • [LinkedIn](https://linkedin.com/)