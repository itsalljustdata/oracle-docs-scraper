#!/usr/bin/env python3
"""
Oracle Documentation Scraper
Extracts view information from Oracle Cloud documentation pages
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
import logging
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OracleDocsScraper:
    def writePage(self, html_content: str | BeautifulSoup, filename: str = "page.html") -> None:
        """Save HTML content to a local HTML file."""
        file = Path('.').joinpath(filename)
        if isinstance(html_content, BeautifulSoup):
            html_content = html_content.prettify()
        file.write_text(html_content, encoding="utf-8")
        logger.info(f"Saved HTML content to {filename}")
    def __init__(self, base_url: str, delay: float = 1.0):
        """
        Initialize the scraper
        
        Args:
            base_url: The main documentation URL
            delay: Delay between requests to be respectful
        """
        self.base_url = base_url
        self.delay = delay
        # Playwright handles browser headers automatically
        
    def get_page_simple(self, url: str) -> BeautifulSoup | None:
        """Fetch a page using simple HTTP requests for static content"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url} with HTTP: {e}")
            return None

    def get_page(self, url: str, expand_tree: bool = False) -> None|BeautifulSoup:
        """Fetch and parse a webpage using Playwright for dynamic content"""
        try:
            logger.info(f"Fetching (Playwright): {url}")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Set headers to mimic a real browser and suppress anti-scraping
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    extra_http_headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1"
                    }
                )
                page = context.new_page()
                page.goto(url, timeout=60000)
                time.sleep(self.delay)
                
                # Only expand tree for the main index page
                if expand_tree:
                    logger.debug("Expanding navigation tree...")
                    max_expand_rounds = 10
                    for _ in range(max_expand_rounds):
                        icons = page.query_selector_all(
                            '.oj-treeview-item.oj-collapsed .oj-treeview-disclosure-icon.oj-clickable-icon-nocontext.oj-default'
                        )
                        if not icons:
                            break
                        for icon in icons:
                            try:
                                if icon.is_visible() and icon.is_enabled():
                                    icon.click(timeout=5000)
                                    time.sleep(0.1)
                            except Exception as e:
                                logger.error(msg=f"{self.base_url} : Tree expansion failed due to error: {e}")
                                logger.info(msg="Aborting tree expansion and proceeding with current state")
                                # browser.close()
                        time.sleep(0.5)  # Wait for DOM update
                    time.sleep(1)  # Final wait for tree to expand
                
                html = page.content()
                browser.close()
            return BeautifulSoup(html, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url} with Playwright: {e}")
            return None
    
    def extract_navigation_tree(self, soup: BeautifulSoup) -> dict[str, list[str]]:
        """
        Extract the navigation tree structure from the main page
        Returns dict with categories and their view links
        """
        # Save the HTML content for debugging/inspection
        # self.writePage(soup, "navigation_tree.html") 
        navigation = {}
        
        # Look for Oracle JET treeview structure
        nav_element = soup.select_one('oj-tree-view ul.oj-treeview-list')
        
        if nav_element:
            logger.debug("Found Oracle JET treeview navigation")
            # Extract hierarchical structure
            navigation = self._parse_navigation_hierarchy(nav_element)
        else:
            logger.error("Could not find Oracle JET treeview navigation structure")
        
        return navigation
    
    def _parse_navigation_hierarchy(self, nav_element) -> dict[str, list[str]]:
        """Parse Oracle JET treeview hierarchical navigation structure"""
        navigation = {}
        
        # Find all top-level li elements (main categories)
        top_level_items = nav_element.find_all('li', recursive=False)
        
        for li in top_level_items:
            # Find the category name from the toc-anchor link
            anchor = li.find('a', class_='toc-anchor')
            if not anchor:
                continue
                
            # Get the category text from the span
            category_span = anchor.find('span', class_='oj-treeview-item-text')
            if not category_span:
                continue
                
            category_text = category_span.get_text(strip=True)
            
            # Skip non-numbered categories or title pages
            if not re.match(r'^\d+\s+', category_text):
                continue
                
            navigation[category_text] = {'Tables': [], 'Views': []}
            logger.debug(f"Found category: {category_text}")
            
            # Look for nested ul elements containing subcategories
            nested_ul = li.find('ul', class_='oj-treeview-list')
            if nested_ul:
                self._parse_subcategories(nested_ul, navigation[category_text], category_text)

        return navigation
    
    def _parse_subcategories(self, ul_element, category_data, category_name):
        """Parse subcategories (Tables/Views) within a category"""
        sub_items = ul_element.find_all('li', recursive=False)
        
        current_subcategory = None
        
        for li in sub_items:
            anchor = li.find('a', class_='toc-anchor')
            if not anchor:
                continue
                
            text_span = anchor.find('span', class_='oj-treeview-item-text')
            if not text_span:
                continue
                
            text = text_span.get_text(strip=True)
            
            # Check if this is a Tables or Views subcategory
            if text.lower() == 'tables':
                current_subcategory = 'Tables'
                logger.debug(f"Found Tables subcategory in {category_name}")
                # Look for nested items under Tables
                nested_ul = li.find('ul', class_='oj-treeview-list')
                if nested_ul:
                    self._parse_table_view_items(nested_ul, category_data['Tables'], 'Tables')
                    
            elif text.lower() == 'views':
                current_subcategory = 'Views'
                logger.debug(f"Found Views subcategory in {category_name}")
                # Look for nested items under Views
                nested_ul = li.find('ul', class_='oj-treeview-list')
                if nested_ul:
                    self._parse_table_view_items(nested_ul, category_data['Views'], 'Views')
    
    def _parse_table_view_items(self, ul_element, item_list, subcategory_type):
        """Parse individual table/view items"""
        items = ul_element.find_all('li', recursive=False)
        
        for li in items:
            anchor = li.find('a', class_='toc-anchor')
            if not anchor:
                continue
                
            text_span = anchor.find('span', class_='oj-treeview-item-text')
            if not text_span:
                continue
                
            text = text_span.get_text(strip=True)
            href = anchor.get('href', '')
            
            # For views, look for items ending with _V or containing VIEW
            if (subcategory_type == 'Views' and 
                (text.endswith('_V') or 'VIEW' in text.upper() or '_V_' in text)):
                full_url = urljoin(self.base_url, href)
                item_list.append({
                    'name': text,
                    'url': full_url
                })
                logger.debug(f"Found view: {text} -> {full_url}")
            
            # For tables, look for items ending with _T or containing TABLE
            elif (subcategory_type == 'Tables' and 
                  (text.endswith('_T') or 'TABLE' in text.upper() or '_T_' in text)):
                full_url = urljoin(self.base_url, href)
                item_list.append({
                    'name': text,
                    'url': full_url
                })
                logger.debug(f"Found table: {text} -> {full_url}")
    
    def extract_view_details(self, view_url: str, view_name: str) -> dict:
        """Extract details, columns, and query information for a specific view"""
        soup = self.get_page_simple(view_url)  # Use simple HTTP for view pages
        if not soup:
            return {'name': view_name, 'url': view_url, 'error': 'Could not fetch page'}
        
        view_info = {
            'name': view_name,
            'url': view_url,
            # 'details': {},
            # 'columns': [],
            # 'query': '',
            # 'description': ''
        }
        
        # Extract description/details
        description_selectors = [
            '.description',
            '.summary',
            'p:first-of-type',
            '.content p:first-child'
        ]
        
        for selector in description_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                view_info['description'] = desc_elem.get_text(strip=True)
                break
        
        # Extract column information
        view_info['columns'] = self._extract_view_columns(soup)
        
        # Extract query if available
        view_info['query'] = self._extract_query(soup)
        
        # Extract additional details
        view_info['details'] = self._extract_details(soup)

        return {k:v for k,v in view_info.items() if v}
    
    def _extract_view_columns(self, soup: BeautifulSoup) -> list[str]:
        """Extract column information from the page"""
        columns = []
        
        # Look for the Columns section in Oracle docs
        # Find heading containing "Columns"
        column_heading = None
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if heading.get_text(strip=True).lower() == 'columns':
                column_heading = heading
                break
        
        if column_heading:
            # Find the next table or content after the heading
            next_element = column_heading.find_next_sibling()
            while next_element:
                if next_element.name == 'table':
                    # Extract from table - check for individual <p> tags in cells first
                    rows = next_element.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        for cell in cells:
                            # First, look for individual <p> tags within the cell
                            p_tags = cell.find_all('p')
                            if len(p_tags) > 1:  # Multiple <p> tags suggest individual column names
                                for p_tag in p_tags:
                                    col_name = p_tag.get_text(strip=True)
                                    if col_name and len(col_name) > 1 and col_name.upper() != 'NAME':
                                        columns.append(col_name)
                            else:
                                # Fallback: try to parse cell text directly
                                cell_text = cell.get_text(strip=True)
                                if cell_text and cell_text.upper() != 'NAME':
                                    # Split by newlines first (most reliable separator)
                                    column_names = cell_text.split('\n')
                                    if len(column_names) == 1:
                                        # If no newlines, try splitting by multiple spaces
                                        column_names = re.split(r'\s{2,}|\t', cell_text)
                                    if len(column_names) == 1:
                                        # Last resort: split by single spaces
                                        column_names = cell_text.split()
                                    
                                    for col_name in column_names:
                                        col_name = col_name.strip()
                                        if col_name and len(col_name) > 1 and not col_name.isdigit():
                                            columns.append(col_name)
                    break
                elif next_element.name in ['div', 'p'] and next_element.get_text(strip=True):
                    # Extract column names from text content
                    text = next_element.get_text(strip=True)
                    # Look for column names (usually ALL_CAPS with underscores)
                    column_names = re.findall(r'[A-Z_][A-Z0-9_]*', text)
                    for col_name in column_names:
                        if len(col_name) > 2:  # Filter out short matches
                            columns.append(col_name)
                    break
                next_element = next_element.find_next_sibling()
        
        return columns
    
    def _extract_query(self, soup: BeautifulSoup) -> str:
        """Extract SQL query if available"""
        query = ''
        
        # Look for the Query section in Oracle docs
        query_heading = None
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if heading.get_text(strip=True).lower() == 'query':
                query_heading = heading
                break
        
        if query_heading:
            # Find the next table or content after the heading
            next_element = query_heading.find_next_sibling()
            while next_element:
                if next_element.name == 'table':
                    # Query might be in a table cell
                    cells = next_element.find_all('td')
                    for cell in cells:
                        # First check if there are multiple <p> tags in the cell
                        p_tags = cell.find_all('p')
                        if len(p_tags) > 1:
                            # Extract text from each <p> tag separately to preserve line structure
                            lines = []
                            for p_tag in p_tags:
                                line_text = p_tag.get_text(strip=True)
                                if line_text:
                                    lines.append(line_text)
                            cell_text = '\n'.join(lines)
                        else:
                            cell_text = cell.get_text(strip=True)
                            
                        if 'SELECT' in cell_text.upper() or 'select' in cell_text:
                            # Format the SQL query with proper line breaks
                            query = self._format_sql_query(cell_text)
                            break
                    if query:
                        break
                elif next_element.name in ['div', 'p', 'pre', 'code']:
                    text = next_element.get_text(strip=True)
                    if 'SELECT' in text.upper() or 'select' in text:
                        query = text
                        break
                next_element = next_element.find_next_sibling()
        
        # Fallback: look for code blocks, pre tags, or SQL content anywhere
        if not query:
            code_selectors = ['code', 'pre', '.sql', '.query']
            for selector in code_selectors:
                code_elem = soup.select_one(selector)
                if code_elem:
                    text = code_elem.get_text(strip=True)
                    if 'SELECT' in text.upper() or 'FROM' in text.upper():
                        query = text
                        break
        
        return query
    
    def _format_sql_query(self, query_text: str) -> str:
        """Format SQL query with proper line breaks and indentation"""
        if not query_text:
            return query_text
            
        # Add line breaks after common SQL keywords
        keywords = ['SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'ORDER BY', 'GROUP BY', 'HAVING', 'UNION']
        formatted = query_text
        
        for keyword in keywords:
            # Add line break before keyword (except for SELECT at the beginning)
            if keyword != 'SELECT':
                formatted = formatted.replace(f' {keyword} ', f'\n{keyword} ')
                formatted = formatted.replace(f' {keyword.lower()} ', f'\n{keyword} ')
            
            # Also handle keywords at the start of clauses
            formatted = formatted.replace(f'{keyword} ', f'{keyword}\n  ')
            formatted = formatted.replace(f'{keyword.lower()} ', f'{keyword}\n  ')
        
        # Clean up extra whitespace and normalize
        lines = [line.strip() for line in formatted.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def _extract_details(self, soup: BeautifulSoup) -> dict:
        """Extract additional details about the view as a structured dictionary"""
        details = {}
        
        # Look for the Details section in Oracle docs
        details_heading = None
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if heading.get_text(strip=True).lower() == 'details':
                details_heading = heading
                break
        
        if details_heading:
            # Find the next content after the heading
            next_element = details_heading.find_next_sibling()
            while next_element:
                if next_element.name in ['ul', 'ol']:
                    # Extract list items (schema, object owner, etc.)
                    for li in next_element.find_all('li'):
                        li_text = li.get_text(strip=True)
                        if li_text and ':' in li_text:
                            # Split key-value pairs like "Schema: FUSION"
                            key, value = li_text.split(':', 1)
                            details[key.strip().lower().replace(' ', '_')] = value.strip()
                        elif li_text:
                            # Handle items without colons
                            details[li_text.lower().replace(' ', '_')] = True
                    break
                elif next_element.name in ['div', 'p'] and next_element.get_text(strip=True):
                    # Extract paragraph content and try to parse key-value pairs
                    text = next_element.get_text(strip=True)
                    if text:
                        # Try to split by bullet points or line breaks
                        lines = text.replace('•', '\n').split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and ':' in line:
                                key, value = line.split(':', 1)
                                details[key.strip().lower().replace(' ', '_')] = value.strip()
                            elif line:
                                details['description'] = line
                        break
                elif next_element.name == 'table':
                    # Extract table content as key-value pairs
                    for row in next_element.find_all('tr'):
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            key = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            if key and value:
                                details[key.lower().replace(' ', '_')] = value
                    break
                next_element = next_element.find_next_sibling()
        
        return details
    
    def scrape_all_views(self, max_workers: int = 10) -> list[dict]:
        """Main method to scrape all views from the documentation"""
        logger.debug(f"Starting scrape of {self.base_url}")
        
        # Get main page
        soup = self.get_page(self.base_url, expand_tree=True)
        if not soup:
            logger.error("Could not fetch main page")
            return []
        
        # Extract navigation structure
        navigation = self.extract_navigation_tree(soup)
        if not navigation:
            logger.error("Could not find navigation structure. Aborting.")
            raise RuntimeError("Could not find navigation structure.")

        # Collect all view info first
        all_view_tasks = []
        for category, content in navigation.items():
            logger.debug(f"Processing category: {category}")
            views = content.get('Views', []) if isinstance(content, dict) else []
            for view_info in views:
                view_name = view_info.get('name', '')
                view_url = view_info.get('url', '')
                all_view_tasks.append((view_url, view_name, category))
        
        logger.debug(f"Found {len(all_view_tasks)} views to process")
        
        # Process views in parallel using ThreadPoolExecutor
        all_views = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_view = {
                executor.submit(self._process_single_view, view_url, view_name, category): (view_name, view_url)
                for view_url, view_name, category in all_view_tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_view):
                view_name, view_url = future_to_view[future]
                try:
                    view_details = future.result()
                    all_views.append(view_details)
                except Exception as e:
                    logger.error(f"Error processing view {view_name} ({view_url}): {e}")
                    # Add error entry
                    all_views.append({
                        'name': view_name,
                        'url': view_url,
                        'error': str(e),
                        'category': 'Unknown'
                    })
        
        return all_views
    
    def _process_single_view(self, view_url: str, view_name: str, category: str) -> dict:
        """Process a single view (for use in threading)"""
        view_details = self.extract_view_details(view_url, view_name)
        view_details['category'] = category
        return view_details
    
    # def _fallback_scrape(self, soup: BeautifulSoup) -> list[dict]:
    #     """Fallback method if navigation structure is not found"""
    #     logger.info("Using fallback scraping method")
        
    #     all_views = []
        
    #     # Look for all links that might be views
    #     view_links = []
    #     all_links = soup.find_all('a', href=True)
        
    #     for link in all_links:
    #         href = str(link.get('href', ''))
    #         text = link.get_text(strip=True)
    #         # Identify potential view links
    #         if (text.endswith('_V') or 
    #             'VIEW' in text.upper() or 
    #             re.match(r'^[A-Z_]+_V$', text)):
    #             full_url = urljoin(self.base_url, href)
    #             view_links.append({'name': text, 'url': full_url})
        
    #     # Extract details for each view
    #     for view_info in view_links:
    #         view_name = view_info['name']
    #         view_url = view_info['url']
            
    #         logger.info(f"Extracting details for view: {view_name}")
    #         view_details = self.extract_view_details(view_url, view_name)
    #         view_details['category'] = 'Unknown'
            
    #         all_views.append(view_details)
        
    #     return all_views
