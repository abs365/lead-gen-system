# Lead Generation System

Dual-sided lead generation for plumbing services in London.

## What it does

**Buyer side (Plumbers):** Finds London-based plumbing businesses via Google Places API. These are potential *clients* who might pay to receive demand-side leads.

**Demand side (Demand Prospects):** Finds restaurants, cafes, pubs, hotels, and takeaways via UK Food Standards Agency open data. These are businesses likely to need plumbing services.

The system:
1. Collects both sides from public APIs
2. Enriches records with emails and phone numbers from business websites
3. Scores demand prospects (0–100) by likelihood of needing plumbing work
4. Matches demand prospects to nearby plumbers by area and business type
5. Displays everything in a dashboard with filters and CSV export

---

## Buyer vs Demand: Key Distinction

| Side | Who they are | What they do |
|------|-------------|--------------|
| **Buyer (Plumber)** | Plumbing companies in London | May *pay* for leads |
| **Demand (Prospect)** | Restaurants, hotels, pubs etc. | May *need* a plumber |

The plumbers are your paying clients. The demand prospects are the leads you sell to them.

---

## Phase 1 — Local Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm or pnpm
- A Google Places API key (optional but recommended)

### 1. Clone / extract the project

```
lead-gen-system/
  apps/
    api/     ← FastAPI backend
    web/     ← Next.js frontend
  .env.example
```

### 2. Set up the backend

```bash
cd apps/api

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create your .env file
cp ../../.env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 3. Run the backend

```bash
# From apps/api/
uvicorn main:app --reload --port 8000
```

API will be at: http://localhost:8000
Docs at: http://localhost:8000/docs

### 4. Set up the frontend

```bash
cd apps/web
npm install
```

Create `apps/web/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 5. Run the frontend

```bash
# From apps/web/
npm run dev
```

Dashboard at: http://localhost:3000

---

## End-to-End Test (Phase 1)

With both servers running:

### Step 1: Collect plumbers

```bash
curl -X POST http://localhost:8000/collect/plumbers \
  -H "Content-Type: application/json" \
  -d '{"keyword": "plumbers in London", "location": "London, UK"}'
```

Or click **Collect Plumbers** on the dashboard.

### Step 2: Collect demand prospects (no API key needed)

```bash
curl -X POST http://localhost:8000/collect/demand \
  -H "Content-Type: application/json" \
  -d '{"location": "London", "category": "restaurant", "page": 1}'
```

Or click **Collect Demand** on the dashboard.

### Step 3: Enrich websites

```bash
curl -X POST http://localhost:8000/enrich/plumbers -H "Content-Type: application/json" -d '{}'
curl -X POST http://localhost:8000/enrich/demand   -H "Content-Type: application/json" -d '{}'
```

### Step 4: Run matching

```bash
curl -X POST http://localhost:8000/match \
  -H "Content-Type: application/json" \
  -d '{"max_matches_per_prospect": 3}'
```

### Step 5: View in dashboard

Open http://localhost:3000 — navigate to Plumbers, Demand Prospects, Matches.

### Step 6: Export CSV

```
http://localhost:8000/export/plumbers
http://localhost:8000/export/demand
http://localhost:8000/export/matches
```

Or click the **Export CSV** buttons in the dashboard.

---

## API Reference (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| POST | /collect/plumbers | Collect plumbers from Google Places |
| POST | /collect/demand | Collect demand prospects from FSA |
| POST | /enrich/plumbers | Enrich plumber websites |
| POST | /enrich/demand | Enrich demand prospect websites |
| POST | /match | Run matching algorithm |
| GET | /plumbers | List plumbers (paginated, filterable) |
| GET | /demand | List demand prospects (paginated, filterable) |
| GET | /matches | List matches with nested data |
| PATCH | /plumbers/{id}/status | Update CRM status for a plumber |
| GET | /export/plumbers | Download plumbers CSV |
| GET | /export/demand | Download demand prospects CSV |
| GET | /export/matches | Download matches CSV |
| GET | /logs | Recent job logs |
| GET | /health | Liveness probe |

Full interactive docs: http://localhost:8000/docs

---

## What each API key is for

| Variable | Used for | Required? |
|----------|----------|-----------|
| `GOOGLE_API_KEY` | Finding plumbers via Google Places Text Search + Details | Yes for plumber collection |
| `FOOD_DATA_API_KEY` | FSA Open Data — not actually needed (public) | No |
| `COMPANIES_HOUSE_API_KEY` | Phase 2: find newly formed hospitality companies | Phase 2 only |
| `PLANNING_DATA_API_KEY` | Phase 2: planning application signals | Phase 2 only |
| `ELEVENLABS_API_KEY` | Phase 2 optional: outreach audio generation | Phase 2 optional |

---

## Demand Scoring Explained

Scores are **estimates** — not certainty. A score of 80 means "this type of business typically has plumbing-intensive infrastructure." It does not mean they have a plumbing problem right now.

| Component | Max points |
|-----------|-----------|
| Category (hotel > restaurant > pub > cafe > takeaway) | 50 |
| Recent FSA inspection (within 12 months) | 15 |
| Commercial keyword in business name | 15 |
| Contact signals (email + phone + website) | 20 |

---

## Matching Logic

Matches are based on area, not distance. A prospect and plumber match if:
- Same London borough (+50 points)
- Same postcode district, e.g. SW1 (+20 points)
- Commercial plumber + hospitality venue (+20 points)
- Plumber has phone/email (+5 each)

Top 3 plumbers per demand prospect are saved as matches.

---

## Known Limitations

1. **Demand score is an estimate.** It reflects the *type* of business and data freshness — not a live signal of immediate plumbing need.

2. **Landlord/property detection is business-focused.** The system identifies property management companies, facilities operators, and serviced accommodation businesses via Companies House (Phase 2). It does not attempt to identify every individual private landlord.

3. **Contact extraction depends on website availability.** Many small businesses don't have websites, or hide contact info behind JavaScript. Email/phone enrichment will return null for these.

4. **Google Places coverage is not exhaustive.** Some smaller plumbers may not appear in Google Places or may lack website/phone data in the API.

5. **FSA data is inspections-based.** Some newly opened venues may not appear until their first hygiene inspection.

6. **Phase 1 is single-process.** Enrichment runs synchronously. For large datasets (1000+ records), collection and enrichment may be slow. Phase 2 solves this with Celery background workers.

---

## Phase 2 Upgrade Path

Phase 2 adds:
- PostgreSQL (swap `DATABASE_URL`)
- Celery + Redis for background/scheduled jobs
- Companies House API for property/landlord leads
- Planning data API for refurbishment signals
- Docker Compose for easy deployment
- Stronger scoring breakdown fields
- Scheduled nightly refresh jobs
- ElevenLabs voice generation (optional)

To upgrade from Phase 1 to Phase 2:
1. Provision PostgreSQL and Redis
2. Update `DATABASE_URL` and `REDIS_URL` in `.env`
3. Run Alembic migration (provided in Phase 2 branch)
4. Start the Celery worker: `celery -A worker.app worker`
5. Enable scheduled jobs via Celery Beat

Phase 1 code is fully compatible — all Phase 2 work is additive.
