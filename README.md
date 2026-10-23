# SHELTERLINK X

**AI-Driven Disaster Shelter Intelligence, Capacity Forecasting and Smart Survivor Allocation Platform**

> A comprehensive, full-stack B.Tech Computer Science & Engineering capstone project demonstrating **Data Engineering**, **Cloud Engineering**, **AI Engineering**, and **Security Engineering** for disaster emergency management.

---

## 1. Project Overview & Motivation

During natural disasters (cyclones, floods, earthquakes), emergency relief coordinators face severe informational bottlenecks:
- Which shelters currently have verified available bed capacity?
- Which shelters are approaching critical overcrowding?
- How many displaced survivors are predicted to arrive in the next 1, 3, 6, or 12 hours?
- Which shelter best fits a displaced family based on proximity, wheelchair accessibility, medical needs, and family quarters?
- How can allocations be confirmed safely without double-booking beds or separating families?

**SHELTERLINK X** resolves these challenges with a centralized intelligence platform combining real-time capacity telemetry, machine learning demand forecasting, explainable multi-criteria shelter matching, and security controls.

> **Advisory Disclaimer:** SHELTERLINK X is a decision-support and coordination system. It is designed to assist emergency managers and coordinators, not to replace emergency services, rescue teams, or human judgment.

---

## 2. Four Engineering Disciplines Demonstrated

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SHELTERLINK X ARCHITECTURE                      │
├───────────────────┬───────────────────┬───────────────────┬────────────┤
│ Data Engineering  │ Cloud Engineering │  AI Engineering   │  Security  │
│                   │                   │                   │Engineering │
│ • CSV Ingestion   │ • Dockerfile      │ • Scikit-Learn RF │ • RBAC     │
│ • Schema Validator│ • docker-compose  │ • Multi-Horizon   │ • CSRF Prot│
│ • Duplicate Check │ • Health /health  │ • Overcrowd Radar │ • Audit Log│
│ • Quality Audits  │ • Env Configs     │ • Time-Aware Eval │ • Data Min │
│ • Export Pipeline │ • DB Agnostic     │ • Smart Match Alg │ • Pwd Hash │
└───────────────────┴───────────────────┴───────────────────┴────────────┘
```

### A. Data Engineering
- **Multi-Format CSV Ingestion Pipeline:** Automated ingestion for shelter inventory and hourly telemetry observations with batch header and schema verification.
- **Robust Validation Engine:** Strict numeric bounds (capacity > 0, occupancy &ge; 0), location coordinate validation (-90..90, -180..180), and status normalization.
- **Duplicate & Anomaly Detection:** Detects duplicate codes in files and rejects inconsistent states (e.g. occupancy + reserved > total capacity).
- **Line-by-Line Diagnostics:** Never silently discards data; displays total received rows, valid rows, duplicate count, and an itemized table of rejected rows with exact line numbers and reasons.
- **Data Quality Dashboard:** Computes real-time telemetry health scores (0-100), coordinate completeness rates, and overbooking anomalies.
- **Export Engine:** Downloadable CSV exports for shelters, telemetry history, survivor requests, and audit logs.

### B. Cloud Engineering
- **Production-Ready Configuration:** Decoupled environment settings via `.env` and `config.py` (Development, Testing, Production).
- **Containerization:** Multi-stage production `Dockerfile` with non-root security user, built-in health checks, and `docker-compose.yml`.
- **Cloud Health Endpoint:** Standardized `/health` endpoint returning JSON operational diagnostics (database connectivity, model readiness, telemetry volume) for container orchestrators and load balancers.
- **Structured Logging:** Centralized logging with `RotatingFileHandler` writing to `logs/shelterlink.log` and console streams.
- **Database Independence:** Runs seamlessly on SQLite locally and supports PostgreSQL in production via standard `DATABASE_URL` connection strings.

### C. AI Engineering
- **Multi-Horizon Demand Forecasting:** Trains a Scikit-Learn `RandomForestRegressor` against historical lag features (`rolling_incoming_3h_mean`, `occupancy_ratio`, `hour_of_day`, `day_of_week`, `is_weekend`) across configurable future horizons: **1h, 3h, 6h, and 12h**.
- **Overcrowding Risk Radar:** Computes future projected occupancy ($$\text{Projected} = \text{Current} + \text{Forecasted Incoming} - \text{Estimated Departures}$$) and classifies risk into 4 understandable tiers:
  - **Low Risk:** Projected utilization < 70%
  - **Moderate Pressure:** Projected utilization 70% – 85%
  - **High Pressure:** Projected utilization 85% – 95%
  - **Critical Risk:** Projected utilization &ge; 95% or capacity breach
- **Scientific Model Evaluation:** Dedicated benchmark view comparing the Random Forest Regressor against a Historical Naive Baseline using a strict **time-aware chronological 80/20 train/test split** (never shuffled!). Computes live MAE, RMSE, and R² scores with Gini feature importances.
- **Smart Survivor Allocation Engine:** Multi-criteria weighted scoring algorithm ($$35\%$$ Distance, $$25\%$$ Capacity Buffer, $$20\%$$ Facility Surplus, $$20\%$$ Pressure Stability) that matches requests against hard constraints (accessibility ramps, medical aid, family rooms).
- **Family Preservation Rule:** Never automatically splits a household due to space shortage. Always flags such cases for coordinator review.

### D. Security Engineering
- **Secure Password Hashing:** Uses Werkzeug's secure hashing (PBKDF2/scrypt with salt) for all stored credentials.
- **Server-Side Role-Based Access Control (RBAC):** Strict `@login_required` and `@role_required` enforcement on backend routes.
- **CSRF Protection:** Integrated Flask-WTF CSRF tokens on all state-mutating POST requests and forms.
- **Data Minimization:** Collects only anonymous/pseudonymous household references (`Household Alpha-1`) and family counts without storing identity cards or sensitive personal records.
- **Immutable Audit Trail:** Comprehensive `AuditLog` table capturing logins, shelter edits, occupancy modifications, allocation confirmations, overrides, and CSV imports with IP addresses.
- **Safe Error Pages:** Custom error handlers for 400, 403, 404, and 500 that log technical diagnostics server-side without leaking stack traces or internal environment variables to users.

---

## 3. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.11 / 3.13, Flask 3.1, Flask-SQLAlchemy, Flask-WTF, Werkzeug |
| **Frontend** | HTML5, CSS3, JavaScript, Bootstrap 5.3, Bootstrap Icons |
| **Visualizations** | Chart.js 4.4, Leaflet.js 1.9 (OpenStreetMap — 100% free, no API keys) |
| **Data & ML** | Pandas 2.3, NumPy 2.2, Scikit-Learn 1.7, Joblib |
| **Testing** | Pytest 9.1 |
| **Database** | SQLite (development/testing), PostgreSQL (production-ready) |
| **Deployment** | Gunicorn WSGI, Docker, Docker Compose |

---

## 4. Fictional Demonstration Accounts

The platform includes pre-seeded demonstration accounts for evaluating each user role:

| Username | Password | Role | Permissions |
| :--- | :--- | :--- | :--- |
| `admin` | `Admin@12345` | **Administrator** | Full system administration, audit logs, shelters, requests, and allocations. |
| `coordinator` | `Coord@12345` | **Disaster Coordinator** | Review forecasts, intake requests, run smart allocation, confirm placements, CSV import. |
| `manager` | `Manager@12345` | **Shelter Manager** | Update shelter capacity, arrivals/departures, check-in progression, facilities. |
| `viewer` | `Viewer@12345` | **Read-Only Viewer** | View authorized capacity dashboard, radar maps, and summary statistics. |

> **Pro Tip:** The login page features **one-click role fill buttons** for rapid evaluation during viva / demonstration sessions.

---

## 5. Local Setup & Quickstart Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.11 and 3.13)
- Git (optional)

### Step 1: Clone or Navigate to Directory
```powershell
cd "d:\SHELTERLINK X"
```

### Step 2: Create and Activate Virtual Environment (Recommended)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Environment Configuration
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

### Step 5: Initialize Database & Seed Demonstration Data
```powershell
python run.py seed
```
This idempotently initializes the database schema, demonstration accounts, 7 emergency shelters across 7 sectors, 14 days of hourly telemetry (over 300 observations), sample survivor requests, and operational alerts.

### Step 6: Start the Application
```powershell
python run.py
```
Open your browser and navigate to:
**`http://127.0.0.1:5000`**

---

## 6. Running Automated Tests

Run the Pytest test suite:
```powershell
python -m pytest -v
```

### Automated Test Coverage (25 Tests Passing):
- `tests/test_auth.py`: Password hashing, login success, bad credentials, RBAC route restrictions (403 Forbidden).
- `tests/test_shelters.py`: Capacity formula ($$\text{Available} = \text{Total} - \text{Occupancy} - \text{Reserved}$$), negative capacity rejection, overbooking prevention without override, arrivals/departures telemetry logging.
- `tests/test_requests.py`: Household intake validation, priority handling, request cancellation.
- `tests/test_allocation.py`: Mandatory constraint filtering (wheelchair accessibility, medical aid, family units), multi-criteria ranking, family preservation rule, atomic confirmation reservation, check-in lifecycle progression.
- `tests/test_forecasting.py`: Time-aware model evaluation, metric calculations (MAE/RMSE/R²), multi-horizon inference (1h, 3h, 6h, 12h), overcrowding risk classification.
- `tests/test_data_pipeline.py`: CSV batch ingestion, line-by-line invalid row rejection, data quality score calculation, CSV exports.
- `tests/test_api.py`: Cloud health check endpoint (`/health`), GeoJSON map endpoint, Chart.js analytics endpoint.

---

## 7. Database Schema & Architecture

```
┌──────────────┐          ┌──────────────────────┐          ┌─────────────────────────┐
│    User      │          │   ShelterHistory     │          │  AllocationRecommendation│
├──────────────┤          ├──────────────────────┤          ├─────────────────────────┤
│ id (PK)      │          │ id (PK)              │          │ id (PK)                 │
│ username     │          │ shelter_id (FK)      │          │ request_id (FK)         │
│ password_hash│          │ timestamp            │          │ shelter_id (FK)         │
│ role         │          │ total_capacity       │          │ total_score             │
│ is_active    │          │ current_occupancy    │          │ distance_score          │
└──────┬───────┘          │ incoming_requests    │          │ capacity_score          │
       │                  │ departures           │          │ explanation             │
       │                  └──────────┬───────────┘          └────────────┬────────────┘
       │                             │                                   │
       │                             │                                   │
       ▼                             ▼                                   ▼
┌────────────────────────────────────────┐          ┌─────────────────────────────────┐
│                Shelter                 │          │         ShelterRequest          │
├────────────────────────────────────────┤          ├─────────────────────────────────┤
│ id (PK)                                │◀─────────┤ id (PK)                         │
│ shelter_code (Unique)                  │          │ request_code (Unique)           │
│ name                                   │          │ household_alias (Pseudonymous)  │
│ location_name / affected_area          │          │ people_count                    │
│ latitude, longitude                    │          │ affected_area                   │
│ total_capacity                         │          │ requires_accessibility          │
│ current_occupancy                      │          │ requires_medical                │
│ reserved_capacity                      │          │ requires_family_room            │
│ status                                 │          │ priority_level                  │
│ has_accessibility_ramps                │          │ status                          │
│ has_drinking_water, has_medical...     │          │ assigned_shelter_id (FK)        │
└──────────────────┬─────────────────────┘          └────────────────┬────────────────┘
                   │                                                 │
                   │               ┌────────────────────────┐        │
                   └──────────────▶│   ConfirmedAllocation  │◀───────┘
                                   ├────────────────────────┤
                                   │ id (PK)                │
                                   │ request_id (FK, Unique)│
                                   │ shelter_id (FK)        │
                                   │ people_count           │
                                   │ confirmed_by_user_id(FK│
                                   │ check_in_status        │
                                   │ is_override            │
                                   └────────────────────────┘
```

---

## 8. Cloud Deployment Guide

### A. Docker Container Deployment
Build and run with Docker Compose:
```bash
docker-compose up --build -d
```
Inspect logs and health:
```bash
docker-compose logs -f
curl http://localhost:5000/health
```

### B. Deploying to Cloud Hosting (Render / Railway / Fly.io / AWS ECS)
1. **Repository Setup:** Push the repository to GitHub.
2. **Environment Variables:**
   - Set `FLASK_ENV=production`
   - Set `SECRET_KEY` to a cryptographically strong 64-character random string.
   - Set `DATABASE_URL` to your production PostgreSQL instance (e.g. `postgresql://user:password@host:5432/shelterlink_db`).
3. **Database Initialization:**
   In your cloud deploy hook or SSH console:
   ```bash
   python run.py seed
   ```
4. **Health Check Configuration:** Set your cloud provider's health check path to `/health` with an HTTP 200 threshold.

---

## 9. Security Safeguards & Compliance

1. **Role-Based Authorization:** Checked server-side on every restricted route. Attempting to bypass the frontend UI generates a 403 Forbidden status and records an audit log entry.
2. **Data Minimization:** No national IDs, full legal names, financial records, or sensitive medical histories are requested or stored.
3. **CSRF Protection:** Every state-modifying action uses a cryptographic CSRF token.
4. **SQL Injection Defense:** All database interactions utilize SQLAlchemy's parameterized queries and Object-Relational Mapping.
5. **Safe Error Handling:** Production configurations suppress internal stack traces to prevent reconnaissance.

---

## 10. Summary of Completed Features

- [x] Functional Flask backend with modular architecture (`models`, `routes`, `services`, `utils`).
- [x] Multi-role authentication & RBAC (`admin`, `coordinator`, `manager`, `viewer`).
- [x] Emergency shelter inventory with dynamic capacity formula: $$\text{Available} = \text{Total} - \text{Occupancy} - \text{Reserved}$$.
- [x] Arrival and departure quick-adjustment form with override authorization.
- [x] Interactive geospatial map powered by Leaflet.js and OpenStreetMap (no paid API keys).
- [x] Survivor request intake with data minimization and constraint tracking.
- [x] Smart Survivor-to-Shelter Allocation Engine with explainable scoring and family preservation rule.
- [x] Scikit-Learn Random Forest Regressor demand forecasting for 1h, 3h, 6h, and 12h horizons.
- [x] Model evaluation dashboard with MAE, RMSE, R², feature importances, and naive baseline comparison.
- [x] CSV Ingestion Pipeline with schema verification, duplicate detection, and line-by-line rejection reports.
- [x] Real-time operational advisory alert generator with coordinator acknowledgement.
- [x] Downloadable CSV reporting hub and security audit trail viewer.
- [x] Cloud-ready configuration, Dockerfile, docker-compose, and `/health` monitoring endpoint.
- [x] Automated test suite (25 tests passing).
- [x] Idempotent demonstration dataset seed command.
