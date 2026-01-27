# Google Maps Scraping Documentation

## Overview

Google Maps is the highest priority data source for lead prospection. It provides comprehensive business information including:
- Business name, address, phone, website
- Ratings and review counts
- Business hours
- Customer reviews with text
- Business categories

**Difficulty Level:** HIGH (Google has aggressive anti-bot measures)

---

## URL Patterns

### Search Results URL
```
https://www.google.com/maps/search/{query}
```

**Examples:**
- `https://www.google.com/maps/search/plumbers+in+Austin+TX`
- `https://www.google.com/maps/search/dentists+in+Miami+FL`
- `https://www.google.com/maps/search/pest+control+in+Phoenix+AZ`

### Place Detail URL
```
https://www.google.com/maps/place/{business_name_encoded}/data=...
```

The detail URL is obtained from the `a.hfpxzc` link in search results.

---

## Page Structure Analysis

### Search Results Page

#### Container Elements
| Element | Selector | Description |
|---------|----------|-------------|
| Feed container | `div[role="feed"]` | Contains all search results |
| Feed container classes | `.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde.ecceSd` | Alternative class-based selector |

#### Business Listing Card
| Element | Selector | Description |
|---------|----------|-------------|
| Listing container | `article` or `div[role="article"]` | Each business card |
| Listing classes | `.Nv2PK.tH5CWc.THOPZb` | Alternative class selector |
| Listing aria-label | `article[aria-label]` | Contains business name |

#### Data Fields in Listing
| Field | Selector | Example Value |
|-------|----------|---------------|
| Business name | `.qBF1Pd.fontHeadlineSmall` | "Beyond Wow Plumbing & Drains" |
| Rating | `.MW4etd` | "4,8" or "4.8" (locale-dependent) |
| Review count | `.UY7F9` | "(2 171)" |
| Category | Text after rating, before address | "Plombier" / "Plumber" |
| Address snippet | Text with street name | "3432 Greystone Dr" |
| Phone | `.UsdlK` or text with phone pattern | "+1 512-256-4973" |
| Hours status | Text like "Ouvert 24h/24" | "Open 24 hours" |
| Detail page link | `a.hfpxzc` | Full Google Maps URL |
| Website link | `a.lcr4fd` | Direct website URL |

#### Sponsored Detection
```
Check if listing contains:
- heading[level=1] with text "Sponsorisé" (French)
- heading[level=1] with text "Sponsored" (English)
- Text content includes "Annonce" (French) or "Ad" (English)
- URL contains "/aclk?" (Google Ads click tracking)
```

---

### Business Detail Page

#### Main Container
| Element | Selector | Description |
|---------|----------|-------------|
| Main panel | `main[aria-label="{business_name}"]` | Main detail container |
| Close button | `button` with close/X icon | Close detail view |

#### Header Information
| Field | Selector | Example |
|-------|----------|---------|
| Business name | `h1` in main panel | "Beyond Wow Plumbing & Drains" |
| Rating | `img[alt*="étoiles"]` or `img[alt*="stars"]` | "4,8" |
| Review count | `img[alt*="avis"]` or `img[alt*="reviews"]` | "(2 171)" |
| Category | `button` after rating | "Plombier" |

#### Tabs
| Tab | Selector | Content |
|-----|----------|---------|
| Overview | `tab` with "Présentation" / "Overview" | Main info |
| Reviews | `tab` with "Avis" / "Reviews" | Customer reviews |
| About | `tab` with "À propos" / "About" | Business info |

#### Contact Information Region
| Field | Selector Pattern | Example |
|-------|-----------------|---------|
| Address | `button[aria-label*="Adresse"]` or `button[aria-label*="Address"]` | "3432 Greystone Dr, Austin, TX 78731" |
| Phone | `button[aria-label*="téléphone"]` or `button[aria-label*="phone"]` | "+1 512-256-4973" |
| Website | `link[aria-label*="Site Web"]` or `link[aria-label*="Website"]` | URL in href |
| Hours | `button[aria-label*="Horaires"]` or `button[aria-label*="Hours"]` | "Open 24 hours" |
| Plus Code | `button[aria-label*="Plus code"]` | "9752+5P Austin, Texas" |

#### Business Hours Detail
Hours button contains nested elements:
- Status: "Ouvert 24h/24" / "Open 24 hours" or "Ouvert · Ferme à 17:00" / "Open · Closes 5PM"
- Holiday notice: "Horaires susceptibles de varier..." / "Hours might differ..."
- Expandable weekly schedule

#### Reviews Section

##### Review Summary
| Element | Selector | Description |
|---------|----------|-------------|
| Rating breakdown | `table` with star distribution | 5-star to 1-star counts |
| Total rating | Text before star images | "4,8" |
| Total reviews | `button` with review count | "2 171 avis" |

##### Review Topics (Keywords)
| Element | Selector | Example |
|---------|----------|---------|
| Topic buttons | `radiogroup` with filter options | "technicien (139)", "inspection (60)" |
| Topic name | First text in radio button | "technicien" |
| Topic count | Number in parentheses | "139" |

##### Individual Reviews
Each review is in a named `generic` container with reviewer name:

| Field | Location | Description |
|-------|----------|-------------|
| Reviewer name | Container name attribute | "sergio jackson" |
| Reviewer info | `button` with name | "6 avis · 3 photos" |
| Local Guide badge | Text contains "Local Guide" | User is Local Guide |
| Star rating | `img[alt*="étoiles"]` | 5 star icons |
| Review date | Text after stars | "il y a 2 semaines" |
| "New" badge | Text "Nouveau" / "New" | Recent review indicator |
| Review text | Main text block | Full review content |
| "See more" button | `button` with "Voir plus" / "See more" | Expand truncated text |
| Translation toggle | `switch` element | Toggle original/translated |
| Review photos | Photo buttons | User-attached images |
| Owner response | Nested section with "Réponse du propriétaire" | Business owner reply |
| Like button | `button` with "J'aime" / "Like" | User action |
| Share button | `button` with "Partager" / "Share" | Share review |

---

## Scraping Strategy

### Recommended Approach: Playwright with Stealth

```python
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def scrape_google_maps(query: str, max_results: int = 20):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'
        )
        page = await context.new_page()
        await stealth_async(page)
        
        # Navigate to search
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        await page.goto(url, wait_until='networkidle')
        
        # Wait for results
        await page.wait_for_selector('div[role="feed"]', timeout=10000)
        
        # Scroll to load more results
        feed = await page.query_selector('div[role="feed"]')
        for _ in range(5):
            await feed.evaluate('el => el.scrollTop = el.scrollHeight')
            await page.wait_for_timeout(1000)
        
        # Extract listings
        listings = await page.query_selector_all('article, div[role="article"]')
        
        results = []
        for listing in listings[:max_results]:
            # Skip sponsored
            if await listing.inner_text().__contains__('Sponsored') or \
               await listing.inner_text().__contains__('Sponsorisé'):
                continue
            
            # Extract data...
            result = await extract_listing_data(listing)
            results.append(result)
        
        await browser.close()
        return results
```

### Key Anti-Detection Measures

1. **Use Stealth Plugin**: `playwright-stealth` masks automation fingerprints
2. **Realistic Viewport**: 1920x1080 or similar desktop resolution
3. **Random Delays**: Add random waits between actions (1-3 seconds)
4. **Mouse Movements**: Simulate realistic mouse movements before clicks
5. **Scroll Behavior**: Scroll gradually, not instantly
6. **Session Management**: Rotate sessions, don't overuse single browser
7. **Proxy Rotation**: Use residential proxies for production

### Handling Infinite Scroll

The search results use infinite scroll. To load more:

```python
async def scroll_for_results(page, feed_selector, num_scrolls=10):
    feed = await page.query_selector(feed_selector)
    previous_count = 0
    
    for _ in range(num_scrolls):
        # Scroll down
        await feed.evaluate('el => el.scrollTop = el.scrollHeight')
        await page.wait_for_timeout(random.uniform(1000, 2000))
        
        # Check if new results loaded
        current_count = len(await page.query_selector_all('article'))
        if current_count == previous_count:
            break  # No more results
        previous_count = current_count
```

---

## Data Extraction Examples

### Extract from Search Results (Fast)

```python
async def extract_from_listing(article):
    """Extract basic info from search result card."""
    
    # Business name from aria-label or heading
    name = await article.get_attribute('aria-label')
    
    # Rating
    rating_el = await article.query_selector('.MW4etd')
    rating = await rating_el.inner_text() if rating_el else None
    
    # Review count
    reviews_el = await article.query_selector('.UY7F9')
    reviews_text = await reviews_el.inner_text() if reviews_el else "0"
    reviews = int(re.search(r'\d+', reviews_text.replace(',', '')).group())
    
    # Phone
    phone_el = await article.query_selector('.UsdlK')
    phone = await phone_el.inner_text() if phone_el else None
    
    # Website (direct link)
    website_el = await article.query_selector('a.lcr4fd')
    website = await website_el.get_attribute('href') if website_el else None
    
    # Detail page URL
    detail_link = await article.query_selector('a.hfpxzc')
    detail_url = await detail_link.get_attribute('href') if detail_link else None
    
    return {
        'name': name,
        'rating': float(rating.replace(',', '.')) if rating else None,
        'review_count': reviews,
        'phone': phone,
        'website': website,
        'detail_url': detail_url
    }
```

### Extract from Detail Page (Complete)

```python
async def extract_from_detail(page):
    """Extract complete info from business detail page."""
    
    # Wait for main panel
    main = await page.wait_for_selector('main', timeout=5000)
    
    # Business name
    name_el = await page.query_selector('h1')
    name = await name_el.inner_text()
    
    # Address
    address_btn = await page.query_selector(
        'button[aria-label*="Address"], button[aria-label*="Adresse"]'
    )
    address = await address_btn.get_attribute('aria-label')
    address = address.replace('Address:', '').replace('Adresse:', '').strip()
    
    # Phone
    phone_btn = await page.query_selector(
        'button[aria-label*="phone"], button[aria-label*="téléphone"]'
    )
    if phone_btn:
        phone_label = await phone_btn.get_attribute('aria-label')
        phone = re.search(r'[\+\d\s\-\(\)]+', phone_label).group().strip()
    
    # Website
    website_link = await page.query_selector(
        'a[aria-label*="Website"], a[aria-label*="Site Web"]'
    )
    website = await website_link.get_attribute('href') if website_link else None
    
    # Hours
    hours_btn = await page.query_selector(
        'button[aria-label*="Hours"], button[aria-label*="Horaires"]'
    )
    hours = await hours_btn.inner_text() if hours_btn else None
    
    return {
        'name': name,
        'address': address,
        'phone': phone,
        'website': website,
        'hours': hours
    }
```

### Extract Reviews

```python
async def extract_reviews(page, max_reviews=10):
    """Extract customer reviews from detail page."""
    
    reviews = []
    review_containers = await page.query_selector_all('generic[aria-label]')
    
    for container in review_containers[:max_reviews]:
        reviewer_name = await container.get_attribute('aria-label')
        if not reviewer_name:
            continue
            
        # Star rating (count filled stars)
        stars_img = await container.query_selector('img[alt*="star"], img[alt*="étoile"]')
        rating = 5  # Default, parse from alt text
        
        # Review text
        text_el = await container.query_selector('generic >> text=...')
        text = await text_el.inner_text() if text_el else ""
        
        # Date
        date_el = await container.query_selector('text=/il y a|ago/')
        date = await date_el.inner_text() if date_el else None
        
        reviews.append({
            'reviewer': reviewer_name,
            'rating': rating,
            'text': text,
            'date': date
        })
    
    return reviews
```

---

## Pain Signal Detection

From scraped data, identify these pain signals:

### Low Rating Signals
- Rating < 4.0 = High pain
- Rating 4.0-4.3 = Medium pain
- Rating >= 4.5 = Low pain

### Review Volume Signals
- < 10 reviews = New/struggling business
- 10-50 reviews = Growing business
- > 100 reviews = Established business

### Review Keyword Signals
Look for these topics in review text:
- "wait time", "slow", "delayed" = Operational issues
- "expensive", "overpriced", "price" = Pricing concerns  
- "rude", "unprofessional" = Service quality issues
- "no response", "didn't call back" = Communication issues
- "website", "hard to find" = Online presence issues

### Negative Review Patterns
- Multiple 1-star reviews in short period
- Recent negative trend (last 30 days worse than average)
- No owner responses to negative reviews

---

## Rate Limiting & Best Practices

### Recommended Delays
| Action | Delay |
|--------|-------|
| Between searches | 5-10 seconds |
| Between detail page loads | 2-5 seconds |
| Between scroll actions | 1-2 seconds |
| After page load | 2-3 seconds |

### Session Limits
- Max 50-100 searches per session
- Rotate IP/proxy after 30-50 searches
- Use different browser fingerprints

### Error Handling
- CAPTCHA detection: Pause and rotate session
- Rate limit (429): Back off exponentially
- Page not loading: Retry with different proxy

---

## Locale Considerations

Google Maps UI changes based on browser locale:

| Element | English | French |
|---------|---------|--------|
| Sponsored | "Sponsored" | "Sponsorisé" |
| Reviews | "reviews" | "avis" |
| Rating | "4.8 stars" | "4,8 étoiles" |
| Open | "Open" | "Ouvert" |
| Closed | "Closed" | "Fermé" |
| Hours | "Hours" | "Horaires" |
| Website | "Website" | "Site Web" |
| Phone | "Phone" | "Téléphone" |
| Address | "Address" | "Adresse" |

**Recommendation:** Force English locale via URL parameter or browser settings for consistent parsing.

```python
# Add language parameter
url = f"https://www.google.com/maps/search/{query}?hl=en"
```

---

## Output Schema

```python
@dataclass
class GoogleMapsLead:
    # Basic Info
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    website: str
    
    # Ratings
    rating: float
    review_count: int
    
    # Business Info
    category: str
    hours: str
    is_open_24h: bool
    
    # Reviews (sample)
    recent_reviews: List[Review]
    review_topics: Dict[str, int]  # topic -> count
    
    # Metadata
    google_maps_url: str
    place_id: str
    is_sponsored: bool
    scraped_at: datetime
```

---

## Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| CAPTCHAs | Use residential proxies, stealth mode, human-like behavior |
| Rate limiting | Implement delays, rotate sessions |
| Dynamic content | Wait for elements, use Playwright over requests |
| Infinite scroll | Programmatic scrolling with load detection |
| Locale variations | Force English locale with `?hl=en` |
| Data structure changes | Monitor selectors, use fallback patterns |
| Review text truncation | Click "See more" to expand |
| Review pagination | Click "More reviews" button |

---

## Files to Create

After documentation is complete, implement:
1. `src/scrapers/google_maps.py` - Main scraper class
2. `src/scrapers/base.py` - Base scraper interface
3. `tests/test_google_maps_scraper.py` - Unit tests
