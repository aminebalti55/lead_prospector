# Lead Prospector

A Python tool to build qualified lead lists of local businesses in plumbing, dental, and pest control niches. It automatically finds businesses, audits their websites for pain signals, analyzes reviews, and prioritizes the best prospects for outreach.

## Features

- **Multi-Source Data Collection**
  - Google Places API integration
  - Yelp Fusion API integration
  - Automatic deduplication across sources

- **Pain Signal Detection**
  - Website audit: SSL, mobile-friendliness, page speed, CTAs, contact forms
  - Review analysis: operational issues, conversion problems, negative feedback
  - Missing online presence detection

- **Smart Scoring & Prioritization**
  - Weighted scoring based on pain signals
  - Priority levels: HOT, WARM, COLD
  - Recommended offer suggestions (Landing Page vs Ops Tool)

- **Export Options**
  - CSV format for quick review
  - Excel format with multiple sheets and formatting
  - Summary statistics and hot leads sheet

## Quick Start

### 1. Install Dependencies

```bash
cd lead_prospector
pip install -r requirements.txt
```

## Web App (React + FastAPI)

This repo also includes a simple web UI on top of the **free scraping mode** (no paid APIs required).

### Backend (FastAPI)

```bash
# from repo root
pip install -r requirements.txt

# required for scraping mode (once per machine)
playwright install chromium

# start API server
python -m uvicorn backend.app:app --reload --port 8000
```

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and run scrapes + manage leads stored in Excel files under `output/`.

### 2. Configure API Keys

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your keys:
- **Google Places API**: Get from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
- **Yelp Fusion API**: Get from [Yelp Developers](https://www.yelp.com/developers/v3/manage_app)

### 3. Run the Tool

```bash
# Search all niches in one location
python main.py --locations "Austin, TX"

# Search multiple locations
python main.py --locations "Austin, TX" "Houston, TX" "Dallas, TX"

# Search specific niches only
python main.py --locations "Miami, FL" --niches plumbing dental

# Fast mode (skip website auditing)
python main.py --locations "Seattle, WA" --skip-audit

# Output CSV only
python main.py --locations "Denver, CO" --output csv
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--locations`, `-l` | Required. One or more locations to search |
| `--niches`, `-n` | Niches to search: plumbing, dental, pest_control (default: all) |
| `--skip-audit` | Skip website auditing (faster but less data) |
| `--skip-reviews` | Skip fetching reviews (faster but less data) |
| `--output`, `-o` | Output format: csv, xlsx, or both (default: both) |

## Output Columns

The exported spreadsheet includes:

| Column | Description |
|--------|-------------|
| Priority | HOT, WARM, or COLD based on score |
| Score | Total pain signal score (higher = better prospect) |
| Recommended_Offer | Suggested service: Landing Page, Ops Tool, or Both |
| Business_Name | Company name |
| Niche | Business category |
| Address, City, State | Location info |
| Phone | Contact number |
| Website | Business website URL |
| Pain_Tags | Detected issues (e.g., "no_booking_cta, ops_issues") |
| Offer_Reasoning | Why this offer is recommended |
| Google_Rating / Yelp_Rating | Star ratings |
| Google_Reviews / Yelp_Reviews | Review counts |
| Has_SSL, Has_Booking_CTA, etc. | Website audit results |
| Ops_Pain_Mentions | Reviews mentioning operational issues |
| Score breakdown columns | Individual component scores |

## Pain Signal Detection

### Website Signals
- **no_website**: No website found
- **no_booking_cta**: No clear booking/quote/appointment button
- **no_contact_form**: No contact form detected
- **no_ssl**: HTTP instead of HTTPS
- **not_mobile_friendly**: Missing viewport meta tag
- **slow_page_load**: Page takes >5 seconds to load
- **website_unreachable**: Website is down or errors

### Review Signals
- **ops_issues**: Reviews mention scheduling, response, or follow-up problems
- **conversion_issues**: Reviews mention website/contact difficulties
- **many_negative_reviews**: 3+ reviews with 1-2 stars
- **low_rating**: Overall rating below 4.0

## Scoring Weights

| Signal | Points |
|--------|--------|
| No website | 25 |
| No booking CTA | 20 |
| Ops pain in reviews | 20 |
| No contact form | 15 |
| Not mobile friendly | 15 |
| Conversion pain in reviews | 15 |
| Slow page speed | 10 |
| No SSL | 10 |
| Low rating (<4.0) | 10 |
| Few reviews (<10) | 5 |

**Priority Thresholds:**
- HOT: Score >= 60
- WARM: Score >= 35
- COLD: Score < 35

## Project Structure

```
lead_prospector/
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment file
├── src/
│   ├── config.py          # Configuration and settings
│   ├── apis/
│   │   ├── google_places.py  # Google Places API client
│   │   └── yelp.py           # Yelp Fusion API client
│   ├── audit/
│   │   └── website_auditor.py  # Website auditing & review analysis
│   ├── scoring/
│   │   └── scorer.py          # Scoring and prioritization
│   └── export/
│       └── exporter.py        # CSV/Excel export
├── data/                   # Cached data (auto-created)
├── output/                 # Output files (auto-created)
└── logs/                   # Log files (auto-created)
```

## API Costs

### Google Places API
- Text Search: ~$32 per 1000 requests
- Place Details: ~$17 per 1000 requests
- Estimated cost per location/niche: ~$0.50-1.00

### Yelp Fusion API
- Free tier: 5,000 calls/day
- Paid plans available for higher volume

## Tips for Best Results

1. **Start small**: Test with one location first to verify API keys work
2. **Use specific locations**: "Austin, TX" works better than "Texas"
3. **Review hot leads first**: These have the strongest pain signals
4. **Check offer reasoning**: Use this for personalized outreach
5. **Export to Excel**: The summary sheet provides quick insights

## Troubleshooting

**"No API keys configured"**
- Make sure `.env` file exists with valid keys
- Check for typos in key names

**"No leads found"**
- Verify the location format is correct
- Check API rate limits haven't been exceeded
- Try a more specific or different location

**Slow performance**
- Use `--skip-audit` for faster runs without website checks
- Use `--skip-reviews` to skip review fetching
- Reduce the number of locations per run

## License

MIT License - Use freely for your lead generation needs.
