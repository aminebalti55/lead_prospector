# Yelp Scraping Documentation

## Overview

Yelp is an excellent secondary data source for lead prospection. It provides:
- Business name, address, phone, website
- Ratings and review counts
- Response times and quality indicators
- Service area coverage
- License verification status
- Customer reviews

**Difficulty Level:** MEDIUM-HIGH (Yelp has anti-bot measures but less aggressive than Google)

---

## URL Patterns

### Search Results URL
```
https://www.yelp.com/search?find_desc={query}&find_loc={location}
```

**Examples:**
- `https://www.yelp.com/search?find_desc=plumbers&find_loc=Austin%2C+TX`
- `https://www.yelp.com/search?find_desc=dentists&find_loc=Miami%2C+FL`
- `https://www.yelp.com/search?find_desc=pest+control&find_loc=Phoenix%2C+AZ`

### Pagination
```
https://www.yelp.com/search?find_desc=plumbers&find_loc=Austin%2C+TX&start=10
https://www.yelp.com/search?find_desc=plumbers&find_loc=Austin%2C+TX&start=20
```
- `start` parameter increments by 10 for each page

### Business Detail URL
```
https://www.yelp.com/biz/{business-slug}
```

**Example:**
- `https://www.yelp.com/biz/brad-b-plumbing-services-austin`

---

## Page Structure Analysis

### Search Results Page

#### Main Container
| Element | Selector | Description |
|---------|----------|-------------|
| Main content | `main` | Contains all search results |
| Results list | `list` (within main) | Contains business listing items |

#### Business Listing Card
Each listing is a `listitem` containing a `generic` container with the business info.

#### Sponsored Detection
```
Sponsored listings can be identified by:
- URL contains "/adredir?" (ad redirect)
- Contains heading "Sponsored Results" 
- Contains "Sponsored" text in the card
- Links go through /aclk? or /adredir? patterns
```

#### Data Fields in Listing

| Field | Selector Pattern | Example |
|-------|-----------------|---------|
| Business name | `heading[level=3] > link` | "Brad B Plumbing Services" |
| Rating image | `img[alt*="star rating"]` | "4.9 star rating" |
| Rating value | Text before "(X reviews)" | "4.9" |
| Review count | Text "(X reviews)" | "(520 reviews)" |
| Categories | `button` elements with category names | "Plumbing", "Water Heater Installation/Repair" |
| Address | `paragraph` after category | "Serving Austin and the Surrounding Area" or "12205 Antoinette Pl" |
| Neighborhood | Text like "Milwood", "Barton Hills" | Neighborhood name |
| Detail URL | `link` href | "/biz/business-name-city" |

#### Trust Badges
| Badge | Selector | Description |
|-------|----------|-------------|
| Yelp Guaranteed | `button` "Yelp Guaranteed" + icon | Covered up to $2,500 |
| Verified License | `button` "Verified License" | License verified |
| Locally Owned | Icon with "Locally owned & operated" | Local business |
| Free Estimates | Icon with "Free estimates" | Offers free estimates |
| 24/7 Availability | Icon with "24/7 Availability" | Available 24/7 |

#### Response Metrics
| Field | Location | Example |
|-------|----------|---------|
| Response time | `paragraph` with "response time" | "10 mins" |
| Response quality | `img[alt*="response quality"]` | "Excellent response quality" |
| Request count | `paragraph` with "locals recently requested" | "58 locals recently requested a quote" |

#### Review Snippet
| Field | Location | Description |
|-------|----------|-------------|
| Quote | `paragraph` with quotes | "\"Great service...\"" |
| More link | `link` "more" | Link to full review |

---

### Business Detail Page Structure

Visit `/biz/{slug}` for complete business info:

| Field | Location | Description |
|-------|----------|-------------|
| Business name | `h1` | Full business name |
| Address | Address section | Full address with city, state, zip |
| Phone | Phone section | Phone number |
| Website | Website section | Business website URL |
| Hours | Hours section | Daily operating hours |
| Price range | Price indicator | $, $$, $$$ |
| Categories | Category links | All business categories |
| Rating | Star rating + count | 4.5 stars, 500 reviews |
| Photos | Photo gallery | Business photos |
| Reviews | Review section | All customer reviews |

---

## Data Extraction Examples

### Extract from Search Results

```python
async def extract_yelp_listing(listing_element):
    """Extract business info from Yelp search result."""
    
    # Check if sponsored (skip if needed)
    listing_html = await listing_element.inner_html()
    is_sponsored = '/adredir?' in listing_html or 'Sponsored' in listing_html
    
    # Business name
    name_link = await listing_element.query_selector('h3 a')
    name = await name_link.inner_text() if name_link else None
    
    # Detail URL
    detail_url = await name_link.get_attribute('href') if name_link else None
    if detail_url and detail_url.startswith('/biz/'):
        detail_url = f"https://www.yelp.com{detail_url}"
    
    # Rating
    rating_img = await listing_element.query_selector('img[alt*="star rating"]')
    rating_alt = await rating_img.get_attribute('alt') if rating_img else ""
    rating_match = re.search(r'(\d+\.?\d*)', rating_alt)
    rating = float(rating_match.group(1)) if rating_match else None
    
    # Review count
    reviews_text = await listing_element.inner_text()
    reviews_match = re.search(r'\((\d+)\s*reviews?\)', reviews_text)
    review_count = int(reviews_match.group(1)) if reviews_match else 0
    
    # Categories
    category_buttons = await listing_element.query_selector_all('button')
    categories = []
    for btn in category_buttons:
        text = await btn.inner_text()
        if text not in ['Get pricing', 'Yelp Guaranteed', 'Verified License']:
            categories.append(text)
    
    # Response time
    response_match = re.search(r'(\d+\s*(?:mins?|hrs?|days?))\s*response time', reviews_text)
    response_time = response_match.group(1) if response_match else None
    
    # Badges
    has_yelp_guaranteed = 'Yelp Guaranteed' in reviews_text
    has_verified_license = 'Verified License' in reviews_text
    
    return {
        'name': name,
        'rating': rating,
        'review_count': review_count,
        'categories': categories,
        'detail_url': detail_url,
        'response_time': response_time,
        'yelp_guaranteed': has_yelp_guaranteed,
        'verified_license': has_verified_license,
        'is_sponsored': is_sponsored
    }
```

### Extract from Detail Page

```python
async def extract_yelp_detail(page):
    """Extract complete info from Yelp business detail page."""
    
    # Wait for page load
    await page.wait_for_selector('h1')
    
    # Business name
    name = await page.inner_text('h1')
    
    # Rating and reviews
    rating_section = await page.query_selector('[aria-label*="star rating"]')
    # Parse rating from aria-label
    
    # Address - look for address section
    address_section = await page.query_selector('address')
    address = await address_section.inner_text() if address_section else None
    
    # Phone
    phone_link = await page.query_selector('a[href^="tel:"]')
    phone = await phone_link.inner_text() if phone_link else None
    
    # Website
    website_link = await page.query_selector('a[href*="biz_redir"]')
    website = await website_link.get_attribute('href') if website_link else None
    # Note: Yelp uses redirect URLs, extract actual URL from the redirect
    
    # Hours
    hours_section = await page.query_selector('[class*="hours"]')
    hours = await hours_section.inner_text() if hours_section else None
    
    return {
        'name': name,
        'address': address,
        'phone': phone,
        'website': website,
        'hours': hours
    }
```

### Pagination Handler

```python
async def scrape_yelp_search(query: str, location: str, max_pages: int = 5):
    """Scrape Yelp search results with pagination."""
    
    all_results = []
    
    for page_num in range(max_pages):
        start = page_num * 10
        url = f"https://www.yelp.com/search?find_desc={query}&find_loc={location}&start={start}"
        
        await page.goto(url)
        await page.wait_for_selector('main')
        
        # Get all listings
        listings = await page.query_selector_all('main li')
        
        for listing in listings:
            data = await extract_yelp_listing(listing)
            if data['name'] and not data['is_sponsored']:
                all_results.append(data)
        
        # Check if more pages
        next_link = await page.query_selector('a[aria-label="Next"]')
        if not next_link:
            break
        
        await asyncio.sleep(random.uniform(2, 4))
    
    return all_results
```

---

## Scraping Strategy

### Recommended Approach

```python
from playwright.async_api import async_playwright
import random
import asyncio

async def scrape_yelp(query: str, location: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # Add random delays
        await page.goto(f"https://www.yelp.com/search?find_desc={query}&find_loc={location}")
        
        # Wait for content
        await page.wait_for_selector('main', timeout=10000)
        
        # May hit verification - wait and retry
        verification = await page.query_selector('text=Device verification')
        if verification:
            await page.wait_for_timeout(5000)  # Wait for verification to complete
        
        # Extract listings
        results = await extract_listings(page)
        
        await browser.close()
        return results
```

### Anti-Detection Measures

1. **Device Verification**: Yelp may show CAPTCHA-like verification
   - Wait 3-5 seconds for auto-completion
   - If persistent, rotate IP/browser profile

2. **Rate Limiting**:
   - Max 10 requests per minute
   - Wait 2-4 seconds between page loads
   - Rotate sessions after 50 requests

3. **Headers**: Use realistic browser headers
   ```python
   headers = {
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Language': 'en-US,en;q=0.9',
       'Accept-Encoding': 'gzip, deflate, br',
       'Connection': 'keep-alive',
   }
   ```

---

## Pain Signal Detection

### Rating-Based Signals
| Rating | Pain Level | Notes |
|--------|------------|-------|
| < 3.5 | High | Significant issues |
| 3.5 - 4.0 | Medium-High | Multiple problems |
| 4.0 - 4.5 | Medium | Some issues |
| > 4.5 | Low | Generally satisfied |

### Response Metrics Signals
| Metric | Good | Warning |
|--------|------|---------|
| Response time | < 1 hour | > 4 hours |
| Response quality | "Excellent" | Missing |
| Request count | High | Low (< 10/month) |

### Trust Badge Analysis
- **Missing Yelp Guaranteed**: May indicate newer or less vetted business
- **Missing Verified License**: Potential compliance issue
- **No Response Metrics**: Not actively managing leads

### Review Keyword Signals
Look for patterns in review text:
- "slow response", "never called back"
- "overpriced", "expensive"  
- "rude", "unprofessional"
- "wouldn't recommend"
- "filed complaint"

---

## Output Schema

```python
@dataclass
class YelpLead:
    # Basic Info
    name: str
    address: str
    city: str
    state: str
    phone: str
    website: str
    
    # Yelp-specific
    yelp_url: str
    yelp_biz_id: str
    
    # Ratings
    rating: float
    review_count: int
    price_range: str  # $, $$, $$$
    
    # Categories
    categories: List[str]
    
    # Response Metrics
    response_time: str
    response_quality: str
    quote_request_count: int
    
    # Trust Signals
    yelp_guaranteed: bool
    verified_license: bool
    locally_owned: bool
    years_in_business: int
    
    # Metadata
    is_sponsored: bool
    scraped_at: datetime
```

---

## API Alternative (For Reference)

Yelp has an official Fusion API (paid for high volume):
```
https://api.yelp.com/v3/businesses/search
```

The API provides structured data but has usage limits. Scraping is needed for:
- Higher volume data collection
- Review text extraction (API limited)
- Response time metrics (not in API)
- Cost savings for lead prospection

---

## Rate Limiting & Best Practices

### Recommended Delays
| Action | Delay |
|--------|-------|
| Between searches | 3-5 seconds |
| Between detail pages | 2-4 seconds |
| After verification | 5-10 seconds |
| Between pagination | 2-3 seconds |

### Session Limits
- Max 100 pages per session
- Rotate IP after 50 requests
- Clear cookies between major batches

### Error Handling
| Error | Solution |
|-------|----------|
| Device verification | Wait 5s, retry once |
| 403 Forbidden | Rotate IP, new session |
| Rate limit | Back off 30-60 seconds |
| Empty results | Check location format |

---

## Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Device verification popup | Wait 5 seconds for auto-pass, or use residential proxy |
| Dynamic loading | Wait for `main` selector, not full page load |
| Sponsored listings mixed in | Check for `/adredir?` in URLs |
| Price range not shown | Only available on some categories |
| Review text truncated | Visit detail page for full reviews |
| Session expiry | Rotate browser contexts regularly |

---

## Files to Create

After documentation is complete, implement:
1. `src/scrapers/yelp.py` - Main Yelp scraper
2. `tests/test_yelp_scraper.py` - Unit tests
