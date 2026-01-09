# Oracle Documentation Scraper

## Overview
These scripts scrape Oracle Cloud documentation to extract view information (Details, Columns, Query) and save it as JSON.

## Files Created
- `oracle_docs_scraper.py` - Full-featured scraper with robust navigation parsing
- `oracle_docs_scraper_simple.py` - Simpler version, easier to customize
- `requirements_scraper.txt` - Python dependencies

## Installation

```bash
pip install -r requirements_scraper.txt
```

Or install manually:
```bash
pip install requests beautifulsoup4 lxml
```

## Usage

### Method 1: Full Scraper
```bash
python oracle_docs_scraper.py
```

This will:
1. Parse the navigation tree structure
2. Find all categories (e.g., "2 Grants Management")
3. Extract all views under each category
4. Scrape detailed information for each view
5. Save to `oracle_views_data.json`

### Method 2: Simple Scraper
```bash
python oracle_docs_scraper_simple.py
```

This is easier to customize if the page structure is different.

## Output Format

The JSON file will contain an array of view objects:

```json
[
  {
    "name": "GMS_ACTIVE_FUNDING_PATTERN_V",
    "url": "https://docs.oracle.com/...",
    "category": "2 Grants Management",
    "description": "View description text...",
    "columns": [
      {
        "name": "FUNDING_PATTERN_ID",
        "type": "NUMBER",
        "description": "Unique identifier..."
      }
    ],
    "query": "SELECT ... FROM ...",
    "details": "Additional details about the view..."
  }
]
```

## Customization

If the Oracle documentation structure is different, you can modify:

### Navigation Selectors
In `oracle_docs_scraper.py`, update the `nav_selectors` list:
```python
nav_selectors = [
    'nav.toc',           # Table of contents
    '.navigation',       # Navigation section
    '.sidebar',          # Sidebar navigation
    '#your-custom-id'    # Add your specific selector
]
```

### View Detection
Update the view detection pattern:
```python
# Look for views ending with _V
if text.endswith('_V'):

# Or views containing specific text
if 'VIEW' in text.upper():

# Or custom pattern
if re.match(r'YOUR_PATTERN', text):
```

### Column Extraction
Modify the table parsing logic in `_extract_columns()` if the table structure is different.

## Troubleshooting

### No views found
- Check if the URL is accessible
- Inspect the page source to understand the navigation structure
- Modify the navigation selectors in the script

### Missing columns/details
- The page structure might be different than expected
- Check the HTML structure of individual view pages
- Update the extraction selectors accordingly

### Rate limiting
- Increase the delay between requests:
```python
scraper = OracleDocsScraper(url, delay=2.0)  # 2 second delay
```

## Example Usage in Code

```python
from oracle_docs_scraper import OracleDocsScraper

# Create scraper
scraper = OracleDocsScraper("https://docs.oracle.com/...")

# Get all views
views = scraper.scrape_all_views()

# Filter by category
grants_views = [v for v in views if 'Grants' in v['category']]

# Get specific view details
specific_view = scraper.extract_view_details(
    "https://docs.oracle.com/.../specific_view.html",
    "VIEW_NAME"
)
```

## Notes

- The scraper includes delays to be respectful to Oracle's servers
- It handles various Oracle documentation layouts
- Error handling ensures partial results even if some pages fail
- Output is saved as JSON for easy processing