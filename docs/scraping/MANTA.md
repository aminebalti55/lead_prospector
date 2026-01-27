# Manta Scraping Documentation

## Overview

Manta is a business directory with over 20 years of data, containing 794+ plumbing businesses in Austin, TX alone. It provides comprehensive business information including contact details, business hours, employee count, opening date, and SIC codes.

## URL Patterns

### Search Results Page
```
https://www.manta.com/search?search={business_type}&context=unknown&search_source=nav&country=United%20States&state={state}&city={city}&device=desktop&screenResolution=1536x960&page_size={per_page}
```

**Examples:**
- Plumbers in Austin, TX: `https://www.manta.com/search?search=plumbers&context=unknown&search_source=nav&country=United%20States&state=Texas&city=Austin&device=desktop&screenResolution=1536x960&page_size=10`
- Dentists in Houston, TX: `https://www.manta.com/search?search=dentists&context=unknown&search_source=nav&country=United%20States&state=Texas&city=Houston&device=desktop&screenResolution=1536x960&page_size=25`

### Pagination
```
&pg={page_number}
```
- Page numbers start at 1 (default, no param needed)
- Example page 2: `&pg=2`

### Business Detail Page
```
https://www.manta.com/c/{manta_id}/{slug}
```

**Examples:**
- `https://www.manta.com/c/mhp47lq/best-plumbers-near-me`
- `https://www.manta.com/c/mbyk20c/brad-b-plumbing-services-llc`

### Results Per Page Options
- 10 (default)
- 25

### Distance Filter Options
- Within 1 mile
- Within 5 miles
- Within 10 miles (default)
- Within 20 miles

---

## Search Results Page Structure

### Results Summary
- Shows: "Showing X of Y results matching "{query}" near {City}, {State}."
- Example: "Showing 10 of 794 results matching "plumbers" near Austin, Texas."

### Search Result Card Elements

| Data Field | Selector Pattern | Notes |
|------------|------------------|-------|
| Business Name | `link[href^="/c/"]` inside card | Links to detail page `/c/{id}/{slug}` |
| Address Street | Second-level generic under address section | e.g., "600 North Lamar Boulevard Service Road" |
| City, State | Third-level generic under address section | e.g., "Austin, TX" |
| Phone | Generic containing phone pattern | e.g., "(888) 388-6407" |
| Website Link | `link[text="Visit Website"]` | Uses `/urlverify?redirect=` wrapper |
| Claimed Badge | Generic with text "CLAIMED" | Indicates verified listing |
| Category | Generic with "Categorized under" text | May show "undefined" for some listings |
| Services | Generic elements listing services | Comma-separated service keywords |
| Description | Large text block after card info | Business description paragraph |

### Sponsored/Ad Listing Detection

Manta uses a special icon character for certain listings:
- Look for `` character in listing header
- These appear to be highlighted/promoted listings
- First few results often have this icon

**Non-claimed listings:**
- Missing "CLAIMED" badge
- May indicate less verified information

---

## Business Detail Page Structure

### Page Sections
1. **Header** - Business name, claimed badge, breadcrumb navigation
2. **Contact Info** - Address, phone, website, email
3. **Navigation Tabs** - About, Services, Contact, Details, Reviews
4. **About Section** - Business description
5. **Services Section** - List of services offered
6. **Contact Section** - Map, address, phone, website, email, hours
7. **Similar Businesses** - Related businesses sidebar
8. **Reviews Section** - Customer reviews (if any)
9. **Detailed Information** - Business metadata

### Header Elements

| Data Field | Selector Pattern | Notes |
|------------|------------------|-------|
| Business Name | `link[href^="/c/"]` in header | Main business name link |
| Claimed Badge | Generic with "CLAIMED" text | Green checkmark style |
| Breadcrumbs | Links in breadcrumb nav | Category hierarchy |

### Contact Information

| Data Field | Selector Pattern | Notes |
|------------|------------------|-------|
| Full Address | `link[href^="https://maps.google.com"]` | Links to Google Maps |
| Street | First listitem under address | e.g., "2701 Exposition Blvd" |
| City, State, ZIP | Second/third listitems | e.g., "austin, TX 78703" |
| Phone | `link[href^="tel:"]` | Clickable phone link |
| Website | Link with "Visit Website" text | Wrapped through `/urlverify?redirect=` |
| Email | `link[href^="mailto:"]` | Direct email address |

### Business Hours

| Day | Selector Pattern | Example Values |
|-----|------------------|----------------|
| Hours List | `list` under "Current Hours" | Each day as listitem |
| Day Name | First generic in listitem | "Sun", "Mon", "Tue", etc. |
| Hours | Second generic in listitem | "24 Hours", "9:00 AM - 5:00 PM", "Closed" |

### Services Section

| Data Field | Selector Pattern | Notes |
|------------|------------------|-------|
| Service 1 | First generic under Services | Service category with icon |
| Service 2 | Second generic under Services | Additional services |
| Service List | Multiple generics with checkmark icon | Bullet-style service list |

### Detailed Information Section

| Data Field | Selector Pattern | Notes |
|------------|------------------|-------|
| Location Type | Generic after "Location Type" | "Branch", "Headquarters", "Single Location" |
| Opening Date | Generic after "Opening Date" | Year business was established (e.g., "2012") |
| Annual Revenue | Generic after "Annual Revenue Estimate" | Often "Unknown" |
| SIC Code | Generic after "SIC Code" (requires click "show") | e.g., "8711, Engineering Services" |
| Employees | Generic after "Employees" | Range like "10 to 19", "1 to 4", etc. |
| Contacts | Generic after "Contacts" (requires click "show") | Contact name e.g., "Stewart Underwood" |

**Note:** SIC Code and Contacts require clicking "show" button to reveal.

### Reviews Section

| Data Field | Selector Pattern | Notes |
|------------|------------------|-------|
| Reviews Header | Generic with "Reviews" text | Section title |
| No Reviews | Generic with "There are no reviews yet" | When empty |
| Write Review Link | Link with "Write a Review" text | Requires login |

---

## Pain Signal Detection

### Signals from Search Results

| Signal | Detection Method | Lead Score Impact |
|--------|------------------|-------------------|
| Not Claimed | Missing "CLAIMED" badge | -10 points |
| No Website | Missing "Visit Website" link | -15 points |
| Generic Description | Very short or templated text | -5 points |
| Undefined Category | "Categorized under undefined" | -5 points |

### Signals from Detail Page

| Signal | Detection Method | Lead Score Impact |
|--------|------------------|-------------------|
| New Business | Opening Date < 3 years | +5 points (opportunity) |
| Very New Business | Opening Date < 1 year | +10 points (high opportunity) |
| Small Team | Employees "1 to 4" | +5 points (decision maker accessible) |
| No Reviews | "There are no reviews yet" | -5 points |
| 24/7 Hours | All days show "24 Hours" | Neutral (may be placeholder) |
| Unknown Revenue | Annual Revenue "Unknown" | Neutral |
| No Email | Missing email contact | -5 points |

---

## Extraction Code

### Data Classes

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class MantaSearchResult:
    """Data from Manta search results page"""
    manta_id: str  # e.g., "mhp47lq"
    name: str
    street_address: Optional[str]
    city: str
    state: str
    phone: Optional[str]
    website_url: Optional[str]  # Unwrapped from urlverify
    is_claimed: bool
    category: Optional[str]
    services: List[str]
    description: Optional[str]
    detail_url: str
    is_promoted: bool  # Has special icon

@dataclass 
class MantaBusinessProfile:
    """Full data from Manta business detail page"""
    manta_id: str
    name: str
    is_claimed: bool
    
    # Contact Info
    street_address: Optional[str]
    city: str
    state: str
    zip_code: Optional[str]
    phone: Optional[str]
    website_url: Optional[str]
    email: Optional[str]
    
    # Business Details
    location_type: Optional[str]  # Branch, Headquarters, Single Location
    opening_date: Optional[str]  # Year established
    annual_revenue: Optional[str]
    sic_code: Optional[str]
    sic_description: Optional[str]
    employees: Optional[str]  # Range like "10 to 19"
    contact_name: Optional[str]
    
    # Hours
    hours: dict  # {"Sun": "24 Hours", "Mon": "9:00 AM - 5:00 PM", ...}
    
    # Services & Description
    services: List[str]
    description: Optional[str]
    
    # Reviews
    review_count: int
    
    # Categories (from breadcrumbs)
    categories: List[str]
```

### Search Results Extraction

```python
import re
from playwright.async_api import Page
from urllib.parse import unquote, parse_qs, urlparse

async def extract_search_results(page: Page) -> List[MantaSearchResult]:
    """Extract business listings from Manta search results"""
    results = []
    
    # Wait for results to load
    await page.wait_for_selector('main', timeout=10000)
    
    # Get all result cards - they contain links starting with /c/
    cards = await page.query_selector_all('main >> xpath=//generic[.//link[starts-with(@href, "/c/")]]')
    
    for card in cards:
        try:
            # Extract business name and URL
            name_link = await card.query_selector('link[href^="/c/"]')
            if not name_link:
                continue
                
            name = await name_link.inner_text()
            detail_url = await name_link.get_attribute('href')
            
            # Extract Manta ID from URL
            # URL format: /c/mhp47lq/best-plumbers-near-me
            manta_id = detail_url.split('/')[2] if detail_url else None
            
            # Extract address
            address_section = await card.query_selector('generic:has(img[alt="Map pin"])')
            street = None
            city = None
            state = None
            
            if address_section:
                address_parts = await address_section.query_selector_all('generic')
                if len(address_parts) >= 2:
                    street = await address_parts[0].inner_text()
                    city_state = await address_parts[1].inner_text()
                    # Parse "Austin, TX" format
                    if ',' in city_state:
                        city, state = city_state.split(',', 1)
                        city = city.strip()
                        state = state.strip()
            
            # Extract phone
            phone = None
            phone_elem = await card.query_selector('generic:has-text("(")')
            if phone_elem:
                phone_text = await phone_elem.inner_text()
                phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', phone_text)
                if phone_match:
                    phone = phone_match.group()
            
            # Extract website URL (unwrap from urlverify)
            website_url = None
            website_link = await card.query_selector('link:has-text("Visit Website")')
            if website_link:
                wrapped_url = await website_link.get_attribute('href')
                # Parse: /urlverify?redirect=http%3A%2F%2Fexample.com&s=...
                if 'redirect=' in wrapped_url:
                    parsed = urlparse(wrapped_url)
                    params = parse_qs(parsed.query)
                    if 'redirect' in params:
                        website_url = unquote(params['redirect'][0])
            
            # Check if claimed
            claimed_elem = await card.query_selector('generic:has-text("CLAIMED")')
            is_claimed = claimed_elem is not None
            
            # Extract category
            category = None
            cat_elem = await card.query_selector('generic:has-text("Categorized under")')
            if cat_elem:
                cat_text = await cat_elem.inner_text()
                category = cat_text.replace('Categorized under', '').strip()
                if category == 'undefined':
                    category = None
            
            # Extract services
            services = []
            service_elems = await card.query_selector_all('generic:has-text(",")')
            for svc in service_elems:
                svc_text = await svc.inner_text()
                if not any(skip in svc_text.lower() for skip in ['categorized', 'showing', 'results']):
                    services.extend([s.strip() for s in svc_text.split(',')])
            
            # Extract description (usually the last large text block)
            description = None
            desc_elems = await card.query_selector_all('generic')
            for elem in reversed(desc_elems):
                text = await elem.inner_text()
                if len(text) > 100:  # Description is usually long
                    description = text.strip()
                    break
            
            # Check for promoted listing (special icon character)
            is_promoted = False
            full_text = await card.inner_text()
            if '' in full_text:
                is_promoted = True
            
            results.append(MantaSearchResult(
                manta_id=manta_id,
                name=name.strip(),
                street_address=street,
                city=city or '',
                state=state or '',
                phone=phone,
                website_url=website_url,
                is_claimed=is_claimed,
                category=category,
                services=services,
                description=description,
                detail_url=f"https://www.manta.com{detail_url}",
                is_promoted=is_promoted
            ))
            
        except Exception as e:
            print(f"Error extracting card: {e}")
            continue
    
    return results
```

### Business Detail Extraction

```python
async def extract_business_profile(page: Page) -> MantaBusinessProfile:
    """Extract full business profile from Manta detail page"""
    
    await page.wait_for_selector('main', timeout=10000)
    
    # Extract Manta ID from URL
    url = page.url
    manta_id = url.split('/c/')[1].split('/')[0] if '/c/' in url else None
    
    # Extract business name
    name_elem = await page.query_selector('main link[href^="/c/"]:first-of-type')
    name = await name_elem.inner_text() if name_elem else ''
    
    # Check if claimed
    claimed_elem = await page.query_selector('generic:has-text("CLAIMED")')
    is_claimed = claimed_elem is not None
    
    # Extract contact info
    address_link = await page.query_selector('link[href^="https://maps.google.com"]')
    street_address = None
    city = ''
    state = ''
    zip_code = None
    
    if address_link:
        addr_text = await address_link.inner_text()
        # Parse address parts
        parts = addr_text.split('\n')
        if len(parts) >= 1:
            # Find business name and remove it
            for i, part in enumerate(parts):
                if part.strip() == name.strip():
                    parts = parts[i+1:]
                    break
        
        if len(parts) >= 2:
            street_address = parts[0].strip()
            city_state_zip = parts[1].strip()
            # Parse "austin, TX 78703"
            match = re.match(r'([^,]+),\s*(\w{2})\s*(\d{5})?', city_state_zip)
            if match:
                city = match.group(1).strip()
                state = match.group(2).strip()
                zip_code = match.group(3)
    
    # Extract phone
    phone = None
    phone_link = await page.query_selector('link[href^="tel:"]')
    if phone_link:
        phone = await phone_link.inner_text()
    
    # Extract website (unwrap urlverify)
    website_url = None
    website_link = await page.query_selector('link:has-text("Visit Website")')
    if website_link:
        wrapped = await website_link.get_attribute('href')
        if 'redirect=' in wrapped:
            parsed = urlparse(wrapped)
            params = parse_qs(parsed.query)
            if 'redirect' in params:
                website_url = unquote(params['redirect'][0])
    
    # Extract email
    email = None
    email_link = await page.query_selector('link[href^="mailto:"]')
    if email_link:
        email = await email_link.inner_text()
    
    # Extract business details - need to click "show" buttons first
    show_buttons = await page.query_selector_all('generic:has-text("show")')
    for btn in show_buttons:
        try:
            await btn.click()
            await page.wait_for_timeout(500)
        except:
            pass
    
    # Location Type
    location_type = await extract_detail_value(page, 'Location Type')
    
    # Opening Date
    opening_date = await extract_detail_value(page, 'Opening Date')
    
    # Annual Revenue
    annual_revenue = await extract_detail_value(page, 'Annual Revenue Estimate')
    
    # SIC Code
    sic_code = None
    sic_description = None
    sic_text = await extract_detail_value(page, 'SIC Code')
    if sic_text and sic_text != 'show':
        if ',' in sic_text:
            parts = sic_text.split(',', 1)
            sic_code = parts[0].strip()
            sic_description = parts[1].strip() if len(parts) > 1 else None
    
    # Employees
    employees = await extract_detail_value(page, 'Employees')
    
    # Contacts
    contact_name = await extract_detail_value(page, 'Contact')
    if contact_name == 'show':
        contact_name = None
    
    # Extract hours
    hours = {}
    hours_list = await page.query_selector('list:below(:text("Current Hours"))')
    if hours_list:
        hour_items = await hours_list.query_selector_all('listitem')
        for item in hour_items:
            day_elem = await item.query_selector('generic:first-child')
            time_elem = await item.query_selector('generic:last-child')
            if day_elem and time_elem:
                day = await day_elem.inner_text()
                time = await time_elem.inner_text()
                hours[day.strip()] = time.strip()
    
    # Extract services
    services = []
    services_section = await page.query_selector('generic:has-text("Services"):has(generic)')
    if services_section:
        svc_items = await services_section.query_selector_all('generic:has-text(",")')
        for svc in svc_items:
            svc_text = await svc.inner_text()
            services.extend([s.strip() for s in svc_text.split(',')])
    
    # Extract description
    description = None
    about_section = await page.query_selector('generic:below(:text("About"))')
    if about_section:
        paragraphs = await about_section.query_selector_all('paragraph')
        texts = []
        for p in paragraphs:
            texts.append(await p.inner_text())
        description = '\n'.join(texts)
    
    # Extract review count
    review_count = 0
    no_reviews = await page.query_selector('generic:has-text("There are no reviews yet")')
    if not no_reviews:
        # Try to find review count
        review_header = await page.query_selector('generic:has-text("Reviews")')
        if review_header:
            # Look for count in nearby elements
            pass  # Usually 0 for most businesses
    
    # Extract categories from breadcrumbs
    categories = []
    breadcrumbs = await page.query_selector_all('main >> link[href^="/mb_"]')
    for bc in breadcrumbs:
        cat = await bc.inner_text()
        if cat and cat not in ['U.S.']:
            categories.append(cat.strip().replace(' ', ''))
    
    return MantaBusinessProfile(
        manta_id=manta_id,
        name=name.strip(),
        is_claimed=is_claimed,
        street_address=street_address,
        city=city,
        state=state,
        zip_code=zip_code,
        phone=phone,
        website_url=website_url,
        email=email,
        location_type=location_type,
        opening_date=opening_date,
        annual_revenue=annual_revenue,
        sic_code=sic_code,
        sic_description=sic_description,
        employees=employees,
        contact_name=contact_name,
        hours=hours,
        services=services,
        description=description,
        review_count=review_count,
        categories=categories
    )


async def extract_detail_value(page: Page, label: str) -> Optional[str]:
    """Extract value from Detailed Information section by label"""
    try:
        label_elem = await page.query_selector(f'generic:has-text("{label}")')
        if label_elem:
            parent = await label_elem.evaluate_handle('el => el.parentElement')
            value_elem = await parent.query_selector('generic:last-child')
            if value_elem:
                return await value_elem.inner_text()
    except:
        pass
    return None
```

---

## Anti-Detection Measures

### Browser Configuration

```python
from playwright.async_api import async_playwright

async def create_manta_browser():
    """Create browser configured for Manta scraping"""
    
    playwright = await async_playwright().start()
    
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
        ]
    )
    
    context = await browser.new_context(
        viewport={'width': 1536, 'height': 960},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='en-US',
        timezone_id='America/Chicago',
        extra_http_headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    )
    
    # Remove webdriver indicator
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    return browser, context
```

### Error Handling

Manta may return these error codes:
- **500 Internal Server Error** - Server issue, retry after delay
- **429 Too Many Requests** - Rate limited, back off significantly
- **403 Forbidden** - May need new session/cookies

```python
import asyncio
from random import uniform

async def safe_navigate(page, url: str, max_retries: int = 3):
    """Navigate with retry logic for Manta"""
    
    for attempt in range(max_retries):
        try:
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            if response.status == 200:
                # Check for error page
                error_heading = await page.query_selector('heading:has-text("500")')
                if error_heading:
                    raise Exception("500 Error Page")
                return True
                
            elif response.status == 429:
                # Rate limited - long backoff
                wait_time = 60 * (attempt + 1)  # 60s, 120s, 180s
                print(f"Rate limited, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                
            elif response.status == 500:
                # Server error - retry with backoff
                wait_time = 10 * (attempt + 1)
                await asyncio.sleep(wait_time)
                
            else:
                print(f"Unexpected status: {response.status}")
                await asyncio.sleep(5)
                
        except Exception as e:
            print(f"Navigation error (attempt {attempt + 1}): {e}")
            await asyncio.sleep(5 * (attempt + 1))
    
    return False
```

---

## Rate Limiting

### Recommended Delays

| Action | Min Delay | Max Delay | Notes |
|--------|-----------|-----------|-------|
| Between searches | 3s | 6s | Manta is sensitive to rapid queries |
| Between detail pages | 2s | 4s | Less restrictive than search |
| After 429 error | 60s | 120s | Back off significantly |
| After 500 error | 10s | 30s | Server may be recovering |
| Per hour limit | ~60 requests | - | Conservative estimate |

### Implementation

```python
import asyncio
from random import uniform
from datetime import datetime, timedelta

class MantaRateLimiter:
    def __init__(self):
        self.last_request = None
        self.request_count = 0
        self.hour_start = datetime.now()
        self.hourly_limit = 60
    
    async def wait_for_search(self):
        """Wait appropriate time before search request"""
        await self._check_hourly_limit()
        await self._wait_since_last(3.0, 6.0)
    
    async def wait_for_detail(self):
        """Wait appropriate time before detail page request"""
        await self._check_hourly_limit()
        await self._wait_since_last(2.0, 4.0)
    
    async def wait_for_retry(self, error_code: int):
        """Wait after error"""
        if error_code == 429:
            wait = uniform(60, 120)
        elif error_code == 500:
            wait = uniform(10, 30)
        else:
            wait = uniform(5, 10)
        
        print(f"Waiting {wait:.1f}s after {error_code} error...")
        await asyncio.sleep(wait)
    
    async def _check_hourly_limit(self):
        """Reset counter or wait if hourly limit reached"""
        now = datetime.now()
        
        if now - self.hour_start > timedelta(hours=1):
            self.hour_start = now
            self.request_count = 0
        
        if self.request_count >= self.hourly_limit:
            wait_time = (self.hour_start + timedelta(hours=1) - now).total_seconds()
            print(f"Hourly limit reached, waiting {wait_time:.0f}s...")
            await asyncio.sleep(wait_time + 1)
            self.hour_start = datetime.now()
            self.request_count = 0
    
    async def _wait_since_last(self, min_delay: float, max_delay: float):
        """Wait minimum time since last request"""
        if self.last_request:
            elapsed = (datetime.now() - self.last_request).total_seconds()
            needed = uniform(min_delay, max_delay)
            if elapsed < needed:
                await asyncio.sleep(needed - elapsed)
        
        self.last_request = datetime.now()
        self.request_count += 1
```

---

## Full Scraper Example

```python
import asyncio
from typing import List
from dataclasses import asdict

async def scrape_manta_businesses(
    business_type: str,
    city: str,
    state: str,
    max_results: int = 50
) -> List[MantaBusinessProfile]:
    """
    Scrape businesses from Manta
    
    Args:
        business_type: Type of business (e.g., "plumbers")
        city: City name (e.g., "Austin")
        state: State name (e.g., "Texas")
        max_results: Maximum businesses to scrape
    
    Returns:
        List of MantaBusinessProfile objects
    """
    
    browser, context = await create_manta_browser()
    rate_limiter = MantaRateLimiter()
    
    try:
        page = await context.new_page()
        
        # First, go to homepage to establish session
        await page.goto('https://www.manta.com/', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        
        # Construct search URL
        search_url = (
            f"https://www.manta.com/search?"
            f"search={business_type}&context=unknown&search_source=nav"
            f"&country=United%20States&state={state}&city={city}"
            f"&device=desktop&screenResolution=1536x960&page_size=25"
        )
        
        all_results = []
        page_num = 1
        
        while len(all_results) < max_results:
            # Rate limit
            await rate_limiter.wait_for_search()
            
            # Navigate to search page
            current_url = search_url if page_num == 1 else f"{search_url}&pg={page_num}"
            
            if not await safe_navigate(page, current_url):
                print(f"Failed to load search page {page_num}")
                break
            
            # Extract search results
            results = await extract_search_results(page)
            
            if not results:
                print("No more results found")
                break
            
            all_results.extend(results)
            print(f"Page {page_num}: Found {len(results)} results (total: {len(all_results)})")
            
            page_num += 1
            
            # Check if we have enough
            if len(all_results) >= max_results:
                all_results = all_results[:max_results]
                break
        
        # Now fetch detail pages for each result
        profiles = []
        
        for i, result in enumerate(all_results):
            print(f"Fetching detail {i+1}/{len(all_results)}: {result.name}")
            
            await rate_limiter.wait_for_detail()
            
            if not await safe_navigate(page, result.detail_url):
                print(f"Failed to load detail page for {result.name}")
                continue
            
            try:
                profile = await extract_business_profile(page)
                profiles.append(profile)
            except Exception as e:
                print(f"Error extracting profile: {e}")
                continue
        
        return profiles
        
    finally:
        await browser.close()


# Usage example
async def main():
    profiles = await scrape_manta_businesses(
        business_type="plumbers",
        city="Austin",
        state="Texas",
        max_results=20
    )
    
    for profile in profiles:
        print(f"\n{profile.name}")
        print(f"  Phone: {profile.phone}")
        print(f"  Website: {profile.website_url}")
        print(f"  Employees: {profile.employees}")
        print(f"  Established: {profile.opening_date}")
        print(f"  SIC: {profile.sic_code} - {profile.sic_description}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Notes

1. **Initial 500 Error**: Direct search URLs may return 500 errors. It's better to navigate from homepage and use the search form, or retry with delays.

2. **urlverify Wrapper**: All external website links go through `/urlverify?redirect=URL` - parse the redirect parameter to get actual URL.

3. **Hidden Fields**: SIC Code and Contacts require clicking "show" buttons to reveal.

4. **Claimed Status**: Not all businesses are claimed - unclaimed listings may have less accurate information.

5. **Promoted Listings**: Some results have a special `` icon - these may be paid placements.

6. **Hours Format**: May show "24 Hours" for all days (could be placeholder) or actual hours like "9:00 AM - 5:00 PM".

7. **Employee Ranges**: Given as ranges like "1 to 4", "10 to 19", "20 to 49", etc.
