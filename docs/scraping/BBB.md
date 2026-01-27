# BBB (Better Business Bureau) Scraping Documentation

## Overview

BBB provides unique trust signals including accreditation status, letter ratings (A+ to F), and complaint history - data not available from other sources. This makes BBB particularly valuable for lead qualification.

## URL Patterns

### Search Results Page
```
https://www.bbb.org/search?find_country=USA&find_text={query}&find_loc={city}%2C+{state}
```

**Examples:**
- `https://www.bbb.org/search?find_country=USA&find_text=plumbers&find_loc=Austin%2C+TX`
- `https://www.bbb.org/search?find_country=USA&find_text=dentists&find_loc=Houston%2C+TX`

### Pagination
```
https://www.bbb.org/search?find_country=USA&find_loc={city}%2C+{state}&find_text={query}&page={page_number}
```

### Business Profile Page
```
https://www.bbb.org/us/{state}/{city}/profile/{category}/{business-slug}-{bbb_id}
```

**Example:**
- `https://www.bbb.org/us/tx/austin/profile/plumber/my-austin-plumber-llc-0825-1000240476`

### Reviews Page
```
https://www.bbb.org/us/{state}/{city}/profile/{category}/{business-slug}-{bbb_id}/customer-reviews
```

### Complaints Page
```
https://www.bbb.org/us/{state}/{city}/profile/{category}/{business-slug}-{bbb_id}/complaints
```

---

## Search Results Page Structure

### Page Layout
- **Header**: Cookie consent banner, navigation, search bar
- **Filters**: BBB Accredited, Get a Quote, Serving my Area, Distance, Category, BBB Rating
- **Sort**: Best Match (default)
- **Results**: ~15-20 results per page, numbered pagination (5 pages for 71 results)
- **Ads**: Sponsored listings at top with "Ad" label

### CSS Selectors - Search Results

| Data Field | CSS Selector / Pattern | Notes |
|------------|----------------------|-------|
| **Result Container** | Main content area with listing cards | Each business is a clickable card |
| **Business Name** | `heading[level=3] > link` | Links to profile URL |
| **Category** | `paragraph` under heading | "Plumber", "Backflow Testing", etc. |
| **BBB Rating** | `generic[contains("BBB Rating:")]` | Format: "BBB Rating: A+" or "BBB Rating: A-" |
| **Accredited Badge** | `img[alt="Accredited Business"]` | Image presence indicates accreditation |
| **Not Accredited** | `img[alt="not BBB accredited"]` | Image indicates non-accredited |
| **Phone** | `link[href^="tel:"]` | Format: (512) 578-5162 |
| **Address** | `paragraph` after phone link | "Austin, TX 78741-7040" |
| **Service Area Badge** | `generic[contains("Service Area")]` | Icon indicates service area |
| **Get a Quote Link** | `link[contains("Get a Quote")]` | Link to quote page |
| **Profile URL** | `link[href*="/profile/"]` | Full business profile link |
| **Ad Marker** | `link[contains("advertisement:")]` | Sponsored listings |
| **Ad Link Text** | `generic[contains("advertisement:")]` | "advertisement:" prefix |

### Sponsored/Ad Detection

Ads are marked with:
1. **Ad label**: `link` containing "Why are there ads on BBB.org?" before the card
2. **Heading prefix**: `heading` contains `advertisement: {Business Name}`
3. **URL pattern**: Links through `adclick.g.doubleclick.net/pcs/click?...`

```python
def is_sponsored_listing(card_element) -> bool:
    # Check heading for "advertisement:" prefix
    heading = card_element.query_selector("heading[level=3]")
    if heading:
        text = heading.inner_text()
        if text.startswith("advertisement:"):
            return True
    
    # Check for doubleclick ad URLs
    links = card_element.query_selector_all("link")
    for link in links:
        href = link.get_attribute("href") or ""
        if "adclick.g.doubleclick.net" in href:
            return True
    
    return False
```

---

## Business Profile Page Structure

### Page Layout
- **Header**: Business name, category, accreditation seal, BBB rating
- **Quick Actions**: Visit Website, Phone, Write a Review
- **Navigation Tabs**: Main, Get a Quote, Reviews, Complaints
- **Content Sections**: Overview, BBB Accreditation & Rating, About This Business, Business Details

### CSS Selectors - Business Profile

| Data Field | CSS Selector / Pattern | Notes |
|------------|----------------------|-------|
| **Business Name** | `generic` after "Business Profile" | Large text element |
| **Category** | `paragraph` in header area | "Plumber" |
| **BBB Rating** | `link[contains("Rated by BBB")] > generic` | "A", "A+", "A-", "B", etc. |
| **Accredited Status** | `img[alt="BBB accredited business seal"]` | Presence = accredited |
| **Website** | `link[contains("Visit Website")]` | External website URL |
| **Phone** | `link[href^="tel:"]` | Phone number link |
| **Address** | `paragraph` in Overview section | Full address |
| **BBB Accredited Since** | `paragraph > strong[contains("BBB Accredited Since:")]` | Following text = date |
| **Years in Business** | `paragraph > strong[contains("Years in Business:")]` | Following text = number |
| **Local BBB** | `definition > link` after "Local BBB:" | BBB office name |
| **BBB File Opened** | `definition` after "BBB File Opened:" | Date |
| **Business Started** | `definition` after "Business Started:" | Date |
| **Business Incorporated** | `definition` after "Business Incorporated:" | Date |
| **Type of Entity** | `definition` after "Type of Entity:" | LLC, Corporation, etc. |
| **Business Management** | `definition` after "Business Management:" | Owner name and title |
| **Categories** | `definition > link` after "Business Categories:" | Multiple category links |
| **Rating Reasons** | `list` under "Reasons for rating" | List items with rating factors |

### Business Details Section

BBB provides rich structured data:

```python
@dataclass
class BBBBusinessDetails:
    local_bbb: str                    # "BBB serving the Heart of Texas"
    bbb_file_opened: str              # "8/7/2025"
    business_started: str             # "6/30/2023"
    business_incorporated: str         # "6/30/2023"
    entity_type: str                  # "Limited Liability Company (LLC)"
    management: str                   # "Mr. Thomas Johnson, Owner/Operator"
    principal_contacts: str           # Contact name
    customer_contacts: str            # Customer service contact
    email_types: List[str]            # ["Sales", "Technical Support", "Customer Service"]
```

---

## Reviews Page Structure

### CSS Selectors - Reviews

| Data Field | CSS Selector / Pattern | Notes |
|------------|----------------------|-------|
| **Review Count** | `paragraph[contains("This business has")]` | "This business has 0 reviews" |
| **Review Cards** | Review container elements | When reviews exist |
| **Review Rating** | Star rating element | 1-5 stars |
| **Review Date** | Date element | When review was posted |
| **Review Text** | Review content paragraph | Customer review text |
| **Business Response** | Response container | If business responded |

---

## Complaints Page Structure

### CSS Selectors - Complaints

| Data Field | CSS Selector / Pattern | Notes |
|------------|----------------------|-------|
| **Complaint Count** | `paragraph[contains("This business has")]` | "This business has 0 complaints" |
| **Submit Complaint** | `link[contains("Submit a Complaint")]` | URL to file complaint |
| **Complaint Cards** | Complaint container elements | When complaints exist |
| **Complaint Type** | Complaint category | Type of issue |
| **Complaint Date** | Date element | When filed |
| **Complaint Status** | Status indicator | Resolved, Answered, etc. |
| **Business Response** | Response container | If business responded |

---

## BBB Rating System

BBB uses letter grades from A+ (best) to F (worst):

| Rating | Interpretation | Lead Score Adjustment |
|--------|---------------|----------------------|
| A+ | Excellent | +15 |
| A | Very Good | +12 |
| A- | Good | +10 |
| B+ | Good | +8 |
| B | Average | +5 |
| B- | Below Average | +2 |
| C+ | Below Average | 0 |
| C | Poor | -5 |
| C- | Poor | -8 |
| D+ | Very Poor | -10 |
| D | Very Poor | -12 |
| D- | Very Poor | -15 |
| F | Failing | -20 |
| NR | Not Rated | 0 |

### Rating Factors (from BBB)
- Length of time business has been operating
- Complaint history and resolution
- Type of business
- Licensing status
- Advertising practices

---

## Python Extraction Code

```python
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import re


@dataclass
class BBBSearchResult:
    """Business listing from BBB search results"""
    name: str
    profile_url: str
    category: str
    bbb_rating: Optional[str] = None        # A+, A, A-, B+, B, B-, C, D, F, NR
    is_accredited: bool = False
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    has_service_area: bool = False
    has_quote_form: bool = False
    is_sponsored: bool = False
    bbb_id: Optional[str] = None            # Extracted from URL


@dataclass
class BBBBusinessProfile:
    """Full business profile from BBB detail page"""
    name: str
    profile_url: str
    category: str
    
    # BBB Specific Data
    bbb_rating: Optional[str] = None
    is_accredited: bool = False
    accredited_since: Optional[str] = None
    years_in_business: Optional[int] = None
    bbb_file_opened: Optional[str] = None
    local_bbb: Optional[str] = None
    rating_reasons: List[str] = field(default_factory=list)
    
    # Contact Info
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    
    # Business Details
    business_started: Optional[str] = None
    business_incorporated: Optional[str] = None
    entity_type: Optional[str] = None       # LLC, Corporation, etc.
    management: Optional[str] = None        # Owner name and title
    principal_contacts: Optional[str] = None
    
    # Categories
    categories: List[str] = field(default_factory=list)
    
    # Reviews & Complaints
    review_count: int = 0
    complaint_count: int = 0
    
    # Metadata
    bbb_id: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)


def extract_bbb_id_from_url(url: str) -> Optional[str]:
    """Extract BBB ID from profile URL"""
    # Pattern: /business-slug-{bbb_id}
    # Example: my-austin-plumber-llc-0825-1000240476
    match = re.search(r'-(\d{4}-\d+)$', url)
    if match:
        return match.group(1)
    return None


def parse_bbb_rating(rating_text: str) -> Optional[str]:
    """Parse BBB rating from text"""
    # "BBB Rating: A+" -> "A+"
    if not rating_text:
        return None
    
    match = re.search(r'BBB Rating:\s*([A-F][+-]?|NR)', rating_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Direct rating text
    if re.match(r'^[A-F][+-]?$', rating_text.strip(), re.IGNORECASE):
        return rating_text.strip().upper()
    
    return None


def parse_years_in_business(text: str) -> Optional[int]:
    """Extract years in business from text"""
    match = re.search(r'Years in Business:\s*(\d+)', text)
    if match:
        return int(match.group(1))
    
    # Direct number
    if text.strip().isdigit():
        return int(text.strip())
    
    return None


async def extract_search_result(page, card_element) -> BBBSearchResult:
    """Extract data from a single search result card"""
    
    # Business name and URL
    name_link = await card_element.query_selector("heading[level=3] link, h3 a")
    name = ""
    profile_url = ""
    
    if name_link:
        name = await name_link.inner_text()
        profile_url = await name_link.get_attribute("href") or ""
        
        # Remove "advertisement:" prefix
        name = re.sub(r'^advertisement:\s*', '', name, flags=re.IGNORECASE).strip()
    
    # Check if sponsored
    is_sponsored = False
    heading = await card_element.query_selector("heading[level=3]")
    if heading:
        heading_text = await heading.inner_text()
        is_sponsored = "advertisement:" in heading_text.lower()
    
    # Also check for doubleclick URLs
    if not is_sponsored:
        links = await card_element.query_selector_all("a")
        for link in links:
            href = await link.get_attribute("href") or ""
            if "adclick.g.doubleclick.net" in href:
                is_sponsored = True
                break
    
    # Category
    category_elem = await card_element.query_selector("paragraph, p")
    category = ""
    if category_elem:
        category = await category_elem.inner_text()
    
    # BBB Rating
    rating_elem = await card_element.query_selector("[class*='rating'], *:has-text('BBB Rating:')")
    bbb_rating = None
    if rating_elem:
        rating_text = await rating_elem.inner_text()
        bbb_rating = parse_bbb_rating(rating_text)
    
    # Accreditation status
    accredited_badge = await card_element.query_selector("img[alt='Accredited Business']")
    not_accredited_badge = await card_element.query_selector("img[alt='not BBB accredited']")
    is_accredited = accredited_badge is not None and not_accredited_badge is None
    
    # Phone
    phone_link = await card_element.query_selector("a[href^='tel:']")
    phone = None
    if phone_link:
        phone = await phone_link.inner_text()
    
    # Address
    address_elem = await card_element.query_selector("paragraph:last-of-type, p:last-of-type")
    address = None
    city = None
    state = None
    if address_elem:
        address = await address_elem.inner_text()
        # Parse city, state from address
        match = re.search(r'([^,]+),\s*([A-Z]{2})\s*\d{5}', address)
        if match:
            city = match.group(1).strip()
            state = match.group(2)
    
    # Service area indicator
    service_area = await card_element.query_selector("*:has-text('Service Area')")
    has_service_area = service_area is not None
    
    # Quote form
    quote_link = await card_element.query_selector("a:has-text('Get a Quote')")
    has_quote_form = quote_link is not None
    
    # Extract BBB ID
    bbb_id = extract_bbb_id_from_url(profile_url)
    
    return BBBSearchResult(
        name=name,
        profile_url=profile_url,
        category=category,
        bbb_rating=bbb_rating,
        is_accredited=is_accredited,
        phone=phone,
        address=address,
        city=city,
        state=state,
        has_service_area=has_service_area,
        has_quote_form=has_quote_form,
        is_sponsored=is_sponsored,
        bbb_id=bbb_id
    )


async def extract_business_profile(page) -> BBBBusinessProfile:
    """Extract full business profile from detail page"""
    
    # Business name
    name_elem = await page.query_selector("main generic:has-text('Business Profile') + * + generic")
    name = ""
    if name_elem:
        name = await name_elem.inner_text()
    
    # Category
    category_elem = await page.query_selector("main paragraph")
    category = ""
    if category_elem:
        category = await category_elem.inner_text()
    
    # BBB Rating
    rating_elem = await page.query_selector("a:has-text('Rated by BBB') generic:first-child")
    bbb_rating = None
    if rating_elem:
        rating_text = await rating_elem.inner_text()
        bbb_rating = parse_bbb_rating(rating_text) or rating_text.strip()
    
    # Accreditation
    accredited_seal = await page.query_selector("img[alt='BBB accredited business seal']")
    is_accredited = accredited_seal is not None
    
    # Accredited Since
    accredited_since_elem = await page.query_selector("*:has-text('BBB Accredited Since:')")
    accredited_since = None
    if accredited_since_elem:
        text = await accredited_since_elem.inner_text()
        match = re.search(r'BBB Accredited Since:\s*(\d{1,2}/\d{1,2}/\d{4})', text)
        if match:
            accredited_since = match.group(1)
    
    # Years in Business
    years_elem = await page.query_selector("*:has-text('Years in Business:')")
    years_in_business = None
    if years_elem:
        text = await years_elem.inner_text()
        years_in_business = parse_years_in_business(text)
    
    # Website
    website_link = await page.query_selector("a:has-text('Visit Website')")
    website = None
    if website_link:
        website = await website_link.get_attribute("href")
    
    # Phone
    phone_link = await page.query_selector("main a[href^='tel:']")
    phone = None
    if phone_link:
        phone = await phone_link.inner_text()
    
    # Address from Overview section
    address_elem = await page.query_selector("heading:has-text('Overview') + * paragraph")
    address = None
    city = None
    state = None
    zip_code = None
    if address_elem:
        address = await address_elem.inner_text()
        match = re.search(r'([^,]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)', address)
        if match:
            city = match.group(1).strip().split('\n')[-1]  # Last line before city
            state = match.group(2)
            zip_code = match.group(3)
    
    # Business Details
    business_started = await extract_definition(page, "Business Started:")
    business_incorporated = await extract_definition(page, "Business Incorporated:")
    entity_type = await extract_definition(page, "Type of Entity:")
    management = await extract_definition(page, "Business Management:")
    local_bbb = await extract_definition(page, "Local BBB:")
    bbb_file_opened = await extract_definition(page, "BBB File Opened:")
    
    # Categories
    categories = []
    category_links = await page.query_selector_all("*:has-text('Business Categories') + * a")
    for cat_link in category_links:
        cat_text = await cat_link.inner_text()
        if cat_text.strip():
            categories.append(cat_text.strip())
    
    # Rating reasons
    rating_reasons = []
    reason_items = await page.query_selector_all("*:has-text('Reasons for rating') + list listitem")
    for item in reason_items:
        reason = await item.inner_text()
        if reason.strip():
            rating_reasons.append(reason.strip())
    
    # Extract BBB ID from URL
    current_url = page.url
    bbb_id = extract_bbb_id_from_url(current_url)
    
    return BBBBusinessProfile(
        name=name,
        profile_url=current_url,
        category=category,
        bbb_rating=bbb_rating,
        is_accredited=is_accredited,
        accredited_since=accredited_since,
        years_in_business=years_in_business,
        bbb_file_opened=bbb_file_opened,
        local_bbb=local_bbb,
        rating_reasons=rating_reasons,
        phone=phone,
        website=website,
        address=address,
        city=city,
        state=state,
        zip_code=zip_code,
        business_started=business_started,
        business_incorporated=business_incorporated,
        entity_type=entity_type,
        management=management,
        categories=categories,
        bbb_id=bbb_id
    )


async def extract_definition(page, term: str) -> Optional[str]:
    """Extract definition value for a given term"""
    term_elem = await page.query_selector(f"*:has-text('{term}')")
    if term_elem:
        parent = await term_elem.evaluate_handle("el => el.parentElement")
        definition = await parent.query_selector("definition, dd")
        if definition:
            return (await definition.inner_text()).strip()
    return None


async def get_review_count(page) -> int:
    """Extract review count from reviews page"""
    count_elem = await page.query_selector("*:has-text('This business has') *:has-text('reviews')")
    if count_elem:
        text = await count_elem.inner_text()
        match = re.search(r'(\d+)\s*reviews?', text)
        if match:
            return int(match.group(1))
    return 0


async def get_complaint_count(page) -> int:
    """Extract complaint count from complaints page"""
    count_elem = await page.query_selector("*:has-text('This business has') *:has-text('complaints')")
    if count_elem:
        text = await count_elem.inner_text()
        match = re.search(r'(\d+)\s*complaints?', text)
        if match:
            return int(match.group(1))
    return 0
```

---

## Pain Signal Detection

### High-Value Signals from BBB

| Signal | Detection Method | Score Impact |
|--------|-----------------|--------------|
| Low BBB Rating (C or below) | `bbb_rating in ['C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']` | +20 (needs help) |
| Multiple Complaints | `complaint_count >= 3` | +15 |
| Not Accredited | `is_accredited == False` | +5 |
| New Business | `years_in_business <= 2` | +10 (may need visibility) |
| No Website | `website is None` | +10 |
| No Quote Form | `has_quote_form == False` | +5 |
| Complaint History | Any complaints in last 3 years | +10 per complaint |

### Pain Signal Scoring

```python
def calculate_bbb_pain_score(profile: BBBBusinessProfile) -> int:
    """Calculate pain signal score from BBB data"""
    score = 0
    
    # BBB Rating analysis
    poor_ratings = ['C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']
    if profile.bbb_rating in poor_ratings:
        score += 20
    elif profile.bbb_rating == 'NR':
        score += 5  # Not rated may indicate new or small business
    
    # Accreditation status
    if not profile.is_accredited:
        score += 5
    
    # Complaint history
    if profile.complaint_count >= 5:
        score += 25
    elif profile.complaint_count >= 3:
        score += 15
    elif profile.complaint_count >= 1:
        score += 10
    
    # Business age (new businesses may need marketing help)
    if profile.years_in_business:
        if profile.years_in_business <= 1:
            score += 15
        elif profile.years_in_business <= 2:
            score += 10
        elif profile.years_in_business <= 3:
            score += 5
    
    # Digital presence gaps
    if not profile.website:
        score += 10
    
    return score


def get_bbb_insights(profile: BBBBusinessProfile) -> List[str]:
    """Generate human-readable insights from BBB data"""
    insights = []
    
    if profile.bbb_rating in ['D+', 'D', 'D-', 'F']:
        insights.append(f"Very poor BBB rating ({profile.bbb_rating}) - reputation issues")
    elif profile.bbb_rating in ['C+', 'C', 'C-']:
        insights.append(f"Below average BBB rating ({profile.bbb_rating}) - room for improvement")
    
    if not profile.is_accredited:
        insights.append("Not BBB accredited - may lack trust signals")
    
    if profile.complaint_count >= 3:
        insights.append(f"{profile.complaint_count} BBB complaints - customer satisfaction issues")
    
    if profile.years_in_business and profile.years_in_business <= 2:
        insights.append(f"New business ({profile.years_in_business} years) - may need visibility")
    
    if not profile.website:
        insights.append("No website listed on BBB - digital presence gap")
    
    return insights
```

---

## Anti-Detection Measures

### Request Headers

```python
BBB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}
```

### Playwright Configuration

```python
from playwright.async_api import async_playwright

async def create_bbb_browser():
    """Create browser instance for BBB scraping"""
    playwright = await async_playwright().start()
    
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
        ]
    )
    
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='en-US',
        timezone_id='America/Chicago',
        extra_http_headers=BBB_HEADERS
    )
    
    # Remove webdriver property
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    return browser, context
```

### Cookie Handling

BBB shows a cookie consent banner that must be handled:

```python
async def handle_cookie_consent(page):
    """Accept cookie consent if present"""
    try:
        accept_btn = await page.wait_for_selector(
            "button:has-text('Accept All Cookies')",
            timeout=5000
        )
        if accept_btn:
            await accept_btn.click()
            await page.wait_for_timeout(1000)
    except:
        pass  # Cookie banner not present or already accepted
```

---

## Rate Limiting

BBB can be slow and has anti-bot measures:

| Action | Recommended Delay |
|--------|------------------|
| Between search result pages | 3-5 seconds |
| Between profile page loads | 4-6 seconds |
| Between reviews/complaints pages | 3-4 seconds |
| After cookie consent | 1-2 seconds |
| On timeout/error | 10-30 seconds backoff |

### Rate Limiting Implementation

```python
import asyncio
import random
from datetime import datetime, timedelta

class BBBRateLimiter:
    def __init__(self):
        self.last_request = datetime.min
        self.request_count = 0
        self.hourly_limit = 60  # Conservative limit
        self.hour_start = datetime.now()
    
    async def wait_before_request(self, request_type: str = "default"):
        """Wait appropriate time before making request"""
        
        # Check hourly limit
        if datetime.now() - self.hour_start > timedelta(hours=1):
            self.hour_start = datetime.now()
            self.request_count = 0
        
        if self.request_count >= self.hourly_limit:
            wait_time = 3600 - (datetime.now() - self.hour_start).seconds
            print(f"Hourly limit reached. Waiting {wait_time}s")
            await asyncio.sleep(wait_time)
            self.hour_start = datetime.now()
            self.request_count = 0
        
        # Per-request delays
        delays = {
            "search": (3, 5),
            "profile": (4, 6),
            "reviews": (3, 4),
            "complaints": (3, 4),
            "default": (3, 5),
        }
        
        min_delay, max_delay = delays.get(request_type, delays["default"])
        delay = random.uniform(min_delay, max_delay)
        
        # Ensure minimum time since last request
        elapsed = (datetime.now() - self.last_request).total_seconds()
        if elapsed < min_delay:
            delay = min_delay - elapsed + random.uniform(0, 1)
        
        await asyncio.sleep(delay)
        self.last_request = datetime.now()
        self.request_count += 1
```

---

## Complete Scraper Example

```python
from playwright.async_api import async_playwright
import asyncio
from typing import List


async def scrape_bbb_search(query: str, city: str, state: str, max_pages: int = 5) -> List[BBBSearchResult]:
    """Scrape BBB search results for a query"""
    
    rate_limiter = BBBRateLimiter()
    results = []
    
    async with async_playwright() as p:
        browser, context = await create_bbb_browser()
        page = await context.new_page()
        
        try:
            # Build search URL
            location = f"{city}, {state}".replace(" ", "+")
            base_url = f"https://www.bbb.org/search?find_country=USA&find_text={query}&find_loc={location}"
            
            for page_num in range(1, max_pages + 1):
                await rate_limiter.wait_before_request("search")
                
                url = f"{base_url}&page={page_num}" if page_num > 1 else base_url
                await page.goto(url, wait_until="networkidle")
                
                # Handle cookie consent on first page
                if page_num == 1:
                    await handle_cookie_consent(page)
                
                # Find all result cards
                cards = await page.query_selector_all("main generic[cursor=pointer]")
                
                if not cards:
                    break  # No more results
                
                for card in cards:
                    try:
                        result = await extract_search_result(page, card)
                        results.append(result)
                    except Exception as e:
                        print(f"Error extracting result: {e}")
                        continue
                
                # Check for next page
                next_link = await page.query_selector("a:has-text('Next')")
                if not next_link:
                    break
        
        finally:
            await browser.close()
    
    return results


async def scrape_bbb_profile(profile_url: str) -> BBBBusinessProfile:
    """Scrape a single BBB business profile"""
    
    rate_limiter = BBBRateLimiter()
    
    async with async_playwright() as p:
        browser, context = await create_bbb_browser()
        page = await context.new_page()
        
        try:
            await rate_limiter.wait_before_request("profile")
            await page.goto(profile_url, wait_until="networkidle")
            await handle_cookie_consent(page)
            
            profile = await extract_business_profile(page)
            
            # Get review count
            reviews_url = profile_url + "/customer-reviews"
            await rate_limiter.wait_before_request("reviews")
            await page.goto(reviews_url, wait_until="networkidle")
            profile.review_count = await get_review_count(page)
            
            # Get complaint count
            complaints_url = profile_url + "/complaints"
            await rate_limiter.wait_before_request("complaints")
            await page.goto(complaints_url, wait_until="networkidle")
            profile.complaint_count = await get_complaint_count(page)
            
            return profile
        
        finally:
            await browser.close()


# Usage example
async def main():
    # Search for plumbers in Austin, TX
    results = await scrape_bbb_search("plumbers", "Austin", "TX", max_pages=3)
    
    print(f"Found {len(results)} results")
    
    # Filter to non-sponsored, accredited businesses
    qualified = [r for r in results if not r.is_sponsored and r.is_accredited]
    
    for result in qualified[:5]:
        print(f"\n{result.name}")
        print(f"  Rating: {result.bbb_rating}")
        print(f"  Phone: {result.phone}")
        print(f"  Accredited: {result.is_accredited}")
        
        # Get full profile
        if result.profile_url:
            profile = await scrape_bbb_profile(result.profile_url)
            print(f"  Years in Business: {profile.years_in_business}")
            print(f"  Complaints: {profile.complaint_count}")
            print(f"  Website: {profile.website}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Data Quality Notes

### Unique BBB Value
- **Accreditation status**: Trust signal unavailable elsewhere
- **Letter ratings**: Standardized quality metric
- **Complaint history**: Customer satisfaction indicator
- **Business details**: Entity type, incorporation date, management

### Limitations
- Some businesses not listed
- Rating may not reflect current quality
- Accreditation requires fee (selection bias)
- Limited review volume compared to Google/Yelp

### Data Freshness
- BBB profiles updated periodically
- Complaint data covers 3-year window
- Recommend weekly scraping for active campaigns
