# Yellow Pages Scraping Documentation

## Overview
Yellow Pages (yellowpages.com) is a well-established business directory with detailed business profiles, reviews, and contact information. The site has a relatively clean HTML structure that's straightforward to scrape.

## URL Patterns

### Search Results Page
```
https://www.yellowpages.com/search?search_terms={business_type}&geo_location_terms={city}%2C+{state}
```

**Examples:**
- `https://www.yellowpages.com/search?search_terms=plumbers&geo_location_terms=Austin%2C+TX`
- `https://www.yellowpages.com/search?search_terms=dentists&geo_location_terms=Miami%2C+FL`
- `https://www.yellowpages.com/search?search_terms=pest+control&geo_location_terms=Denver%2C+CO`

**Pagination:**
```
https://www.yellowpages.com/search?search_terms={business_type}&geo_location_terms={city}%2C+{state}&page={page_number}
```

### Business Detail Page
```
https://www.yellowpages.com/{city}-{state}/mip/{business-name-slug}-{business_id}?lid={listing_id}
```

**Example:**
- `https://www.yellowpages.com/austin-tx/mip/clarke-kent-plumbing-10674347?lid=1002194068759`

---

## Page Structure Analysis

### Search Results Page

The search results page contains two sections:
1. **Sponsored/Ad Listings** - At the top with "Ad" badge
2. **Organic Listings** - Numbered results (1, 2, 3, etc.)

Each listing card contains:
- Business name with link to detail page
- Categories/services
- Star rating and review count
- Phone number
- Address
- Website link
- Years in business badge
- BBB rating badge (if applicable)
- Hours status (open now, closed, etc.)
- Business description snippet
- User review quotes

### Business Detail Page

The detail page contains:
- Full business name
- Claimed status badge
- Categories
- Overall rating and review count
- Hours of operation table
- Years in business
- Phone number
- Website URL
- Full address
- Email (if available)
- General business info/description
- Services/Products list
- Payment methods
- Languages spoken
- Social media links
- Photo gallery
- Full reviews with individual ratings

---

## CSS Selectors Reference

### Search Results Page Selectors

| Data Field | CSS Selector | Notes |
|------------|--------------|-------|
| Results container | `div.search-results` or `div.organic` | Main organic results section |
| Business listing | `div.result` or `div.v-card` | Each business card |
| Business name | `h2 a.business-name` or `heading[level=2] link` | Link text is name |
| Business URL | `h2 a.business-name[href]` | Link to detail page |
| Listing ID | URL parameter `lid=` or data attribute | Extract from href |
| Categories | `.categories a` | Multiple category links |
| Rating stars | `.ratings .result-rating` or img with stars | Count filled stars |
| Review count | `a.rating-count` or `link` containing `(X)` | Text like "(15)" |
| Phone number | `.phones.phone.primary` or `.phone` | Phone text |
| Address - Street | `.street-address` or `.adr` | Street line |
| Address - City/State | `.locality` | City, State ZIP |
| Website link | `a.track-visit-website[href]` | External URL |
| Years in business | `.years-in-business strong` | "40 Years" text |
| BBB badge | `.bbb-rating` or img with "BBB" | BBB accreditation |
| Open/Closed status | `.open-status` | "open now", "closed" |
| Business description | `.snippet` or paragraph with "From Business:" | Truncated description |
| Review quote | `.review-snippet` or paragraph with quote | User review excerpt |
| Ad/Sponsored marker | `.ad-label` or text "Ad" | Identifies paid listings |

### Business Detail Page Selectors

| Data Field | CSS Selector | Notes |
|------------|--------------|-------|
| Business name | `h1` | Main heading |
| Claimed status | `.claim-status` or text "Claimed" | Verified badge |
| Categories | `.categories a` | Service category links |
| Rating | `.rating-stars` | Star rating element |
| Review count | `a` containing `(X)` pattern | "(15)" format |
| Hours table | `table` within Hours section | Day/time rows |
| Years in business | `strong` near "Years in Business" | "40 Years" |
| Phone | `a[href^="tel:"]` | Tel link |
| Website | `a` with "Visit Website" text | External URL |
| Address | `.address` or Map & Directions section | Full address |
| Email | `a[href^="mailto:"]` | Email link |
| General Info | `dd` after "General Info" term | Business description |
| Services/Products | `dd` after "Services/Products" term | Service list |
| Payment methods | `dd` after "Payment method" term | Accepted payments |
| Languages | `dd` after "Languages" term | Languages spoken |
| Social links | Links to facebook.com, twitter.com, etc. | Social profiles |
| Reviews container | `.reviews-section` or `article` elements | Review list |
| Individual review | `article` within reviews | Each review |
| Reviewer name | `a` within review header | Reviewer link |
| Review date | `paragraph` with date format | MM/DD/YYYY |
| Review rating | Star list within review | Individual rating |
| Review text | `paragraph` within review article | Review content |

---

## Sponsored Listing Detection

### Identifying Paid/Sponsored Listings

Yellow Pages clearly marks sponsored listings:

```python
def is_sponsored_listing(listing_element):
    """Check if a listing is a paid advertisement."""
    
    # Method 1: Look for "Ad" text marker
    ad_marker = listing_element.find('.ad-label')
    if ad_marker:
        return True
    
    # Method 2: Check for "Ad" text in any element
    text_content = listing_element.text_content()
    if 'Ad' in text_content.split():  # Standalone "Ad" word
        return True
    
    # Method 3: Check listing container class
    classes = listing_element.get('class', '')
    if 'ad' in classes.lower() or 'sponsored' in classes.lower():
        return True
    
    # Method 4: Sponsored listings appear at top without numbering
    # Organic listings have numbers like "1.", "2.", etc.
    heading = listing_element.find('h2')
    if heading:
        text = heading.text_content().strip()
        if not text[0].isdigit():  # No number prefix = sponsored
            # Check if it's in the sponsored section
            parent = listing_element.parent
            if parent and 'sponsored' in str(parent.get('class', '')).lower():
                return True
    
    return False
```

---

## Data Extraction Code

### Search Results Extraction

```python
from playwright.async_api import async_playwright
from dataclasses import dataclass
from typing import Optional, List
import re

@dataclass
class YellowPagesListing:
    name: str
    url: str
    listing_id: str
    phone: Optional[str]
    address: Optional[str]
    website: Optional[str]
    categories: List[str]
    rating: Optional[float]
    review_count: Optional[int]
    years_in_business: Optional[int]
    is_bbb_accredited: bool
    is_open_now: Optional[bool]
    description: Optional[str]
    is_sponsored: bool

async def scrape_yellowpages_search(business_type: str, city: str, state: str, max_pages: int = 5):
    """Scrape Yellow Pages search results."""
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        for page_num in range(1, max_pages + 1):
            url = f"https://www.yellowpages.com/search?search_terms={business_type}&geo_location_terms={city}%2C+{state}"
            if page_num > 1:
                url += f"&page={page_num}"
            
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Extract all listing containers
            listings = await page.query_selector_all('div.result, div.v-card')
            
            for listing in listings:
                try:
                    result = await extract_listing_data(listing)
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"Error extracting listing: {e}")
                    continue
            
            # Check if there's a next page
            next_button = await page.query_selector('a.next')
            if not next_button:
                break
            
            await page.wait_for_timeout(1500)  # Rate limiting
        
        await browser.close()
    
    return results

async def extract_listing_data(listing) -> Optional[YellowPagesListing]:
    """Extract data from a single listing element."""
    
    # Business name and URL
    name_elem = await listing.query_selector('h2 a, .business-name a')
    if not name_elem:
        return None
    
    name = await name_elem.inner_text()
    name = re.sub(r'^\d+\.\s*', '', name)  # Remove number prefix
    url = await name_elem.get_attribute('href')
    
    # Extract listing ID from URL
    listing_id = ''
    if url:
        id_match = re.search(r'lid=(\d+)', url)
        if id_match:
            listing_id = id_match.group(1)
        else:
            id_match = re.search(r'-(\d+)(?:\?|$)', url)
            if id_match:
                listing_id = id_match.group(1)
    
    # Phone number
    phone_elem = await listing.query_selector('.phones, .phone')
    phone = await phone_elem.inner_text() if phone_elem else None
    
    # Address
    street_elem = await listing.query_selector('.street-address')
    locality_elem = await listing.query_selector('.locality')
    address_parts = []
    if street_elem:
        address_parts.append(await street_elem.inner_text())
    if locality_elem:
        address_parts.append(await locality_elem.inner_text())
    address = ', '.join(address_parts) if address_parts else None
    
    # Website
    website_elem = await listing.query_selector('a[href*="track-visit-website"], a.website-link')
    website = await website_elem.get_attribute('href') if website_elem else None
    
    # Also check for website in link text
    if not website:
        links = await listing.query_selector_all('a')
        for link in links:
            text = await link.inner_text()
            if 'Website' in text:
                website = await link.get_attribute('href')
                break
    
    # Categories
    category_elems = await listing.query_selector_all('.categories a')
    categories = []
    for cat in category_elems:
        cat_text = await cat.inner_text()
        categories.append(cat_text.strip().rstrip(','))
    
    # Rating and review count
    rating = None
    review_count = None
    
    # Look for review count pattern like "(15)"
    review_elem = await listing.query_selector('a[href*="rating"]')
    if review_elem:
        review_text = await review_elem.inner_text()
        count_match = re.search(r'\((\d+)\)', review_text)
        if count_match:
            review_count = int(count_match.group(1))
    
    # Rating from stars (count filled vs empty)
    rating_elem = await listing.query_selector('.result-rating, .rating-stars')
    if rating_elem:
        classes = await rating_elem.get_attribute('class') or ''
        # Extract rating from class like "rating-4" or count stars
        rating_match = re.search(r'rating-(\d)', classes)
        if rating_match:
            rating = float(rating_match.group(1))
    
    # Years in business
    years_in_business = None
    years_elem = await listing.query_selector('.years-in-business strong, strong')
    if years_elem:
        years_text = await years_elem.inner_text()
        years_match = re.search(r'(\d+)\s*Years?', years_text, re.IGNORECASE)
        if years_match:
            years_in_business = int(years_match.group(1))
    
    # BBB accreditation
    bbb_elem = await listing.query_selector('.bbb-rating, img[alt*="BBB"]')
    is_bbb_accredited = bbb_elem is not None
    
    # Open/closed status
    is_open_now = None
    status_elem = await listing.query_selector('.open-status, [class*="open"]')
    if status_elem:
        status_text = (await status_elem.inner_text()).lower()
        is_open_now = 'open' in status_text and 'closed' not in status_text
    
    # Description snippet
    desc_elem = await listing.query_selector('.snippet, p')
    description = None
    if desc_elem:
        description = await desc_elem.inner_text()
        description = description.replace('From Business:', '').strip()
    
    # Check if sponsored
    is_sponsored = False
    ad_elem = await listing.query_selector('.ad-label, .ad-marker')
    if ad_elem:
        is_sponsored = True
    else:
        listing_text = await listing.inner_text()
        # Check for standalone "Ad" text
        if re.search(r'\bAd\b', listing_text):
            is_sponsored = True
    
    return YellowPagesListing(
        name=name.strip(),
        url=f"https://www.yellowpages.com{url}" if url and url.startswith('/') else url,
        listing_id=listing_id,
        phone=phone,
        address=address,
        website=website,
        categories=categories,
        rating=rating,
        review_count=review_count,
        years_in_business=years_in_business,
        is_bbb_accredited=is_bbb_accredited,
        is_open_now=is_open_now,
        description=description,
        is_sponsored=is_sponsored
    )
```

### Business Detail Page Extraction

```python
@dataclass
class YellowPagesBusinessDetail:
    name: str
    claimed: bool
    phone: Optional[str]
    website: Optional[str]
    email: Optional[str]
    address: Optional[str]
    categories: List[str]
    rating: Optional[float]
    review_count: Optional[int]
    years_in_business: Optional[int]
    general_info: Optional[str]
    services: Optional[str]
    payment_methods: List[str]
    languages: List[str]
    social_links: dict
    hours: dict
    reviews: List[dict]

async def scrape_yellowpages_detail(url: str) -> Optional[YellowPagesBusinessDetail]:
    """Scrape a Yellow Pages business detail page."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        await page.goto(url, wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # Business name
        name_elem = await page.query_selector('h1')
        name = await name_elem.inner_text() if name_elem else None
        
        # Claimed status
        claimed = False
        claimed_elem = await page.query_selector('[class*="claim"], :text("Claimed")')
        if claimed_elem:
            claimed = True
        
        # Phone
        phone_elem = await page.query_selector('a[href^="tel:"]')
        phone = None
        if phone_elem:
            phone = await phone_elem.inner_text()
        
        # Website
        website = None
        website_elem = await page.query_selector('a:has-text("Visit Website")')
        if website_elem:
            website = await website_elem.get_attribute('href')
        
        # Email
        email = None
        email_elem = await page.query_selector('a[href^="mailto:"]')
        if email_elem:
            href = await email_elem.get_attribute('href')
            email = href.replace('mailto:', '') if href else None
        
        # Address
        address = None
        addr_elem = await page.query_selector('a:has-text("Map & Directions")')
        if addr_elem:
            addr_text = await addr_elem.inner_text()
            address = addr_text.replace('Map & Directions', '').strip()
        
        # Categories
        categories = []
        cat_elems = await page.query_selector_all('.categories a, a[href*="/plumbers"], a[href*="/dentists"]')
        for cat in cat_elems[:5]:  # Limit to first 5
            text = await cat.inner_text()
            if text.strip():
                categories.append(text.strip().rstrip(','))
        
        # Rating and review count
        rating = None
        review_count = None
        review_link = await page.query_selector('a[href*="rating"]')
        if review_link:
            text = await review_link.inner_text()
            match = re.search(r'\((\d+)\)', text)
            if match:
                review_count = int(match.group(1))
        
        # Years in business
        years_in_business = None
        years_elem = await page.query_selector('strong:has-text("Years")')
        if years_elem:
            text = await years_elem.inner_text()
            match = re.search(r'(\d+)', text)
            if match:
                years_in_business = int(match.group(1))
        
        # General info / description
        general_info = None
        info_elem = await page.query_selector('dt:has-text("General Info") + dd')
        if info_elem:
            general_info = await info_elem.inner_text()
        
        # Services/Products
        services = None
        services_elem = await page.query_selector('dt:has-text("Services/Products") + dd')
        if services_elem:
            services = await services_elem.inner_text()
        
        # Payment methods
        payment_methods = []
        payment_elem = await page.query_selector('dt:has-text("Payment method") + dd')
        if payment_elem:
            text = await payment_elem.inner_text()
            payment_methods = [p.strip() for p in text.split(',')]
        
        # Languages
        languages = []
        lang_elem = await page.query_selector('dt:has-text("Languages") + dd')
        if lang_elem:
            text = await lang_elem.inner_text()
            languages = [l.strip() for l in text.split(',')]
        
        # Social links
        social_links = {}
        social_platforms = ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com']
        for platform in social_platforms:
            link = await page.query_selector(f'a[href*="{platform}"]')
            if link:
                href = await link.get_attribute('href')
                platform_name = platform.split('.')[0]
                social_links[platform_name] = href
        
        # Hours
        hours = {}
        hour_rows = await page.query_selector_all('table tr')
        for row in hour_rows:
            cells = await row.query_selector_all('th, td')
            if len(cells) >= 2:
                day = await cells[0].inner_text()
                time = await cells[1].inner_text()
                hours[day.strip()] = time.strip()
        
        # Reviews
        reviews = []
        review_articles = await page.query_selector_all('article')
        for article in review_articles[:10]:  # Limit to 10 reviews
            try:
                reviewer_elem = await article.query_selector('a[href*="/user/"]')
                reviewer = await reviewer_elem.inner_text() if reviewer_elem else 'Anonymous'
                
                date_elem = await article.query_selector('paragraph, [class*="date"]')
                date = await date_elem.inner_text() if date_elem else None
                
                # Get review text (usually the longest paragraph)
                paragraphs = await article.query_selector_all('p, paragraph')
                review_text = ''
                for p in paragraphs:
                    text = await p.inner_text()
                    if len(text) > len(review_text):
                        review_text = text
                
                if review_text:
                    reviews.append({
                        'reviewer': reviewer.strip(),
                        'date': date.strip() if date else None,
                        'text': review_text.strip()
                    })
            except:
                continue
        
        await browser.close()
        
        return YellowPagesBusinessDetail(
            name=name,
            claimed=claimed,
            phone=phone,
            website=website,
            email=email,
            address=address,
            categories=categories,
            rating=rating,
            review_count=review_count,
            years_in_business=years_in_business,
            general_info=general_info,
            services=services,
            payment_methods=payment_methods,
            languages=languages,
            social_links=social_links,
            hours=hours,
            reviews=reviews
        )
```

---

## Pain Signal Detection

Yellow Pages provides several data points useful for identifying businesses with pain signals:

### Negative Indicators (Good Leads)
```python
def calculate_pain_score(listing: YellowPagesListing, detail: YellowPagesBusinessDetail = None) -> dict:
    """Calculate pain signals from Yellow Pages data."""
    
    signals = {
        'score': 0,
        'reasons': []
    }
    
    # 1. Low/no rating
    if listing.rating is not None:
        if listing.rating < 3.0:
            signals['score'] += 30
            signals['reasons'].append(f"Low rating: {listing.rating}/5 stars")
        elif listing.rating < 4.0:
            signals['score'] += 15
            signals['reasons'].append(f"Below average rating: {listing.rating}/5")
    
    # 2. Few reviews (low visibility)
    if listing.review_count is not None:
        if listing.review_count < 5:
            signals['score'] += 25
            signals['reasons'].append(f"Very few reviews: {listing.review_count}")
        elif listing.review_count < 15:
            signals['score'] += 10
            signals['reasons'].append(f"Limited reviews: {listing.review_count}")
    
    # 3. No website
    if not listing.website:
        signals['score'] += 35
        signals['reasons'].append("No website listed")
    
    # 4. Not claimed (not actively managing listing)
    if detail and not detail.claimed:
        signals['score'] += 20
        signals['reasons'].append("Unclaimed listing - not actively managed")
    
    # 5. No BBB accreditation
    if not listing.is_bbb_accredited:
        signals['score'] += 5
        signals['reasons'].append("Not BBB accredited")
    
    # 6. Older business with few reviews (stagnant)
    if listing.years_in_business and listing.review_count:
        reviews_per_year = listing.review_count / listing.years_in_business
        if reviews_per_year < 1:
            signals['score'] += 15
            signals['reasons'].append(f"Low engagement: {reviews_per_year:.1f} reviews/year over {listing.years_in_business} years")
    
    # 7. No social media presence
    if detail and not detail.social_links:
        signals['score'] += 10
        signals['reasons'].append("No social media links")
    
    # 8. Limited payment options
    if detail and detail.payment_methods:
        if len(detail.payment_methods) < 3:
            signals['score'] += 5
            signals['reasons'].append("Limited payment options")
    
    # 9. Analyze review sentiment
    if detail and detail.reviews:
        negative_keywords = ['terrible', 'awful', 'worst', 'never', 'avoid', 'rude', 
                           'unprofessional', 'overpriced', 'scam', 'disappointed']
        negative_count = 0
        for review in detail.reviews:
            text_lower = review.get('text', '').lower()
            if any(kw in text_lower for kw in negative_keywords):
                negative_count += 1
        
        if negative_count >= 3:
            signals['score'] += 25
            signals['reasons'].append(f"{negative_count} reviews with negative sentiment")
        elif negative_count >= 1:
            signals['score'] += 10
            signals['reasons'].append(f"{negative_count} review(s) with concerning keywords")
    
    return signals
```

---

## Anti-Detection Measures

### Request Headers
```python
YELLOWPAGES_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}
```

### Playwright Configuration
```python
async def create_yellowpages_browser():
    """Create a configured browser for Yellow Pages scraping."""
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ]
    )
    
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='en-US',
        timezone_id='America/Chicago',
    )
    
    # Remove webdriver flag
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    return playwright, browser, context
```

---

## Rate Limiting Recommendations

Yellow Pages has moderate anti-bot protection. Follow these guidelines:

| Action | Delay | Notes |
|--------|-------|-------|
| Between search pages | 2-4 seconds | Random delay recommended |
| Between detail pages | 3-5 seconds | Higher delay for detail pages |
| Between sessions | 10-30 minutes | If doing large batches |
| Requests per hour | 100-150 | Conservative limit |
| Max concurrent | 1 | Single-threaded recommended |

### Rate Limiter Implementation
```python
import asyncio
import random

class YellowPagesRateLimiter:
    def __init__(self):
        self.last_request = 0
        self.request_count = 0
        self.hour_start = time.time()
    
    async def wait(self, is_detail_page: bool = False):
        """Wait appropriate time before next request."""
        
        # Check hourly limit
        if time.time() - self.hour_start > 3600:
            self.request_count = 0
            self.hour_start = time.time()
        
        if self.request_count >= 120:
            wait_time = 3600 - (time.time() - self.hour_start)
            print(f"Hourly limit reached, waiting {wait_time:.0f}s")
            await asyncio.sleep(wait_time + 60)
            self.request_count = 0
            self.hour_start = time.time()
        
        # Delay between requests
        min_delay = 3 if is_detail_page else 2
        max_delay = 5 if is_detail_page else 4
        delay = random.uniform(min_delay, max_delay)
        
        elapsed = time.time() - self.last_request
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        
        self.last_request = time.time()
        self.request_count += 1
```

---

## Error Handling

```python
class YellowPagesScraperError(Exception):
    pass

async def safe_scrape_yellowpages(url: str, max_retries: int = 3):
    """Scrape with retry logic and error handling."""
    
    for attempt in range(max_retries):
        try:
            if '/search' in url:
                return await scrape_yellowpages_search_page(url)
            else:
                return await scrape_yellowpages_detail(url)
        
        except Exception as e:
            if 'blocked' in str(e).lower() or '403' in str(e):
                wait_time = (attempt + 1) * 60
                print(f"Possibly blocked, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            elif 'timeout' in str(e).lower():
                await asyncio.sleep(10)
            else:
                raise YellowPagesScraperError(f"Scrape failed: {e}")
    
    raise YellowPagesScraperError(f"Max retries exceeded for {url}")
```

---

## Key Observations

### Advantages of Yellow Pages
1. **Clean HTML structure** - Well-organized semantic HTML
2. **Detailed business info** - Hours, services, payment methods
3. **Review content available** - Full review text accessible
4. **Years in business data** - Useful for lead qualification
5. **BBB accreditation shown** - Trust indicator
6. **Email addresses** - Sometimes available on detail pages
7. **Claimed status** - Shows if business actively manages listing

### Challenges
1. **Cloudflare protection** - May trigger challenges on aggressive scraping
2. **30 results per page** - Many pages for comprehensive scraping
3. **Variable selectors** - Some class names may change
4. **Review pagination** - Only 10 reviews per page on detail
5. **Rate limiting** - Need conservative approach

### Data Quality Notes
- Business names are reliable and clean
- Phone numbers are well-formatted
- Addresses are structured (street, city/state separate)
- Review dates use MM/DD/YYYY format
- Years in business is self-reported by business
