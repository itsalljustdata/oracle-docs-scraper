# Oracle Cloud Documentation Scraper

## Overview
This project scrapes Oracle Cloud Applications documentation to extract database table and view information including column definitions, details, and metadata. The scraper is designed to work with Oracle JET-based documentation sites and saves structured data as JSON files.

## Project Structure
```
oracle-docs-scraper/
├── scraper/
│   ├── __main__.py              # Main entry point
│   ├── OracleDocsScraper.py     # Core scraper class
│   └── sql_converter.py         # SQL conversion utilities
├── output/                      # Generated JSON files
│   ├── applications-common.25d.json
│   ├── financials.25d.json
│   ├── human-resources.json
│   └── ... (other module files)
├── requirements.txt             # Python dependencies
└── ORACLE_SCRAPER_README.md    # This file
```

## Key Features

### 1. Navigation Tree Parsing
- Extracts hierarchical navigation from Oracle JET treeview components
- Handles dynamic content loading using Playwright
- Expands collapsed tree nodes to discover all available content
- Categorizes content into Tables and Views sections

### 2. Content Extraction
- **Tables & Views**: Scrapes both database tables and views from documentation
- **Column Information**: Extracts column names, types, and descriptions
- **Details**: Captures additional metadata and descriptions
- **Query Information**: Retrieves SQL queries when available

### 3. Dual Fetching Strategy
- **Playwright**: For JavaScript-heavy pages with dynamic content
- **Simple HTTP**: For static content to improve performance
- Automatic fallback between methods

### 4. SQL Conversion Utilities
- Oracle to Databricks SQL conversion using SQLGlot
- Query optimization and formatting
- Table name extraction from SQL queries
- Error handling and logging

## Installation

```bash
pip install -r requirements.txt
```

Dependencies include:
- `playwright` - Browser automation
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP requests
- `sqlglot` - SQL parsing and conversion

## Usage

### Running the Scraper
```bash
cd scraper
python -m scraper
```

Or directly:
```bash
python scraper/__main__.py
```

### Configuration
The scraper targets Oracle Cloud Applications documentation and automatically:
1. Navigates to the main documentation page
2. Expands the navigation tree to find all modules
3. Identifies Tables and Views sections
4. Extracts detailed information for each item
5. Saves results to JSON files in the `output/` directory

### SQL Conversion
```python
from scraper.sql_converter import convert_single_query, extract_table_names

# Convert Oracle SQL to Databricks
result = convert_single_query(oracle_sql)
print(result['converted'])  # Databricks SQL

# Extract table names from SQL
tables = extract_table_names(sql_query)
print(tables)  # List of table dictionaries
```

## Output Format

Each JSON file contains structured data for a documentation module:

```json
{
  "module_name": {
    "Tables": [
      {
        "name": "TABLE_NAME",
        "url": "https://docs.oracle.com/...",
        "columns": ["COL1", "COL2", "COL3"],
        "details": "Table description..."
      }
    ],
    "Views": [
      {
        "name": "VIEW_NAME_V",
        "url": "https://docs.oracle.com/...",
        "columns": ["COL1", "COL2", "COL3"],
        "query": "SELECT ... FROM ...",
        "description": "View description...",
        "details": "Additional details..."
      }
    ]
  }
}
```

## Architecture

### OracleDocsScraper Class
- **Navigation Parsing**: Handles Oracle JET treeview navigation
- **Content Extraction**: Processes individual table/view pages
- **Error Handling**: Graceful degradation when pages fail to load
- **Rate Limiting**: Configurable delays to respect server resources

### Key Methods
- `extract_navigation_tree()`: Parses the main navigation structure
- `extract_view_details()`: Extracts detailed information from view pages
- `extract_table_details()`: Extracts information from table pages
- `_extract_view_columns()`: Parses column information from documentation

### Column Extraction Strategy
The scraper uses multiple strategies to extract column information:
1. Looks for "Columns" headings in the documentation
2. Finds associated tables with column data
3. Parses individual `<p>` tags for column names
4. Falls back to text splitting on newlines, spaces, and tabs
5. Filters out header text and invalid entries

## Customization

### Modifying Selectors
To work with different Oracle documentation layouts:

```python
# Update navigation selectors
nav_element = soup.select_one('oj-tree-view ul.oj-treeview-list')

# Modify column extraction
column_heading = soup.find('h2', string=re.compile(r'columns', re.I))
```

### Adding New Extraction Logic
Extend the `_extract_view_columns()` method to handle different table structures:

```python
def _extract_view_columns(self, soup: BeautifulSoup) -> list[str]:
    # Add your custom extraction logic here
    # Look for tables with summary="Columns"
    columns_table = soup.find('table', attrs={'summary': 'Columns'})
    if columns_table:
        # Process the table...
```

## Error Handling
- Individual page failures don't stop the entire scraping process
- Comprehensive logging for debugging
- Graceful fallback between Playwright and simple HTTP requests
- Timeout handling for slow-loading pages

## Performance Considerations
- Configurable delays between requests (default: 1 second)
- Uses simple HTTP requests for static content when possible
- Parallel processing capabilities for multiple URLs
- Efficient memory usage with streaming JSON output

## Troubleshooting

### Common Issues
1. **Navigation not found**: Check if the target site uses Oracle JET components
2. **Missing columns**: Verify the table structure matches expected format
3. **Timeout errors**: Increase delay or timeout values
4. **JavaScript errors**: Ensure Playwright is properly installed

### Debugging
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Notes
- Designed specifically for Oracle Cloud Applications documentation
- Respects server resources with built-in delays
- Handles both static and dynamic content
- Generates structured JSON output for further processing
- Includes SQL conversion utilities for database migration tasks