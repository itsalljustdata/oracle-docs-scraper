
from OracleDocsScraper import *
from sql_converter import convert_single_query, extract_table_names
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import sqlglot


def runForURL (url: str) -> Path|None:
    """Main function to run the scraper"""

    urlParts = Path(url).parts
    outFileParts = urlParts[urlParts.index('saas') + 1:]
    if outFileParts[-1].endswith('.html'):
        outFileParts = outFileParts[:-2]
    outFileName = '.'.join(outFileParts) + '.json'
    output_file = Path('.').joinpath('output',outFileName)

    if not output_file.parent.exists():
        output_file.parent.mkdir(parents=True, exist_ok=True)
    elif output_file.exists():
        output_file.unlink()

    scraper = OracleDocsScraper(url, delay=1.0)
    views_data, table_data = scraper.scrape_all_views_tabs()
    
    if not views_data:
        logger.warning(msg=f"No views data scraped for URL: {url}")
    if not table_data:
        logger.warning(msg=f"No table data scraped for URL: {url}")
    # if not (views_data or table_data):
    #     return None

    remaps = [('query','pretty'),('query_databricks','converted'),('error','conversion_error')]

    for v in views_data:
        if 'query' in v:

            vTabs = extract_table_names(v['query'])
            if isinstance(vTabs, list) and len(vTabs) == 1:
                firstOne = vTabs[0]
                if isinstance(firstOne, str) and firstOne.startswith('Error parsing SQL'):
                    vTabs = None
            
            if vTabs is not None:
                vTabs = sorted(vTabs, key=lambda x: x['name'].upper())
                v['tables'] = {t.pop('name'): t for t in vTabs}
            result: dict[str,str|None] = convert_single_query(oracle_sql=v['query'])

            for v_key, r_key in remaps:
                if (r_value := result.get(r_key,None)) is not None:
                    v[v_key] = r_value
    
    def knockOffUrl (theDictList: list[dict]) -> list[dict]:
        theDictList = sorted(theDictList, key=lambda x: x['name'].upper())
        for x in theDictList:
            if 'url' in x:
                x.pop('url')
        return theDictList

    table_data = knockOffUrl(table_data)
    views_data = knockOffUrl(views_data)
    
    obj = dict(
        product = outFileParts[0].replace('-',' ').title(), 
        url = url,
        numTables = len(table_data),
        numViews = len(views_data),
        tables = {t.pop('name'): t for t in table_data},
        views = {v.pop('name'): v for v in views_data},
    )

    # Custom JSON formatting to preserve line feeds in queries
    json_str = json.dumps(obj, indent=1, ensure_ascii=False)
    # Replace escaped newlines with actual newlines in query strings
    # This is a bit of a hack but works for our specific case
    # json_str = re.sub(r'"query": "([^"]*)"', lambda m: '"query": "' + m.group(1).replace('\\n', '\n') + '"', json_str)
    
    output_file.write_text(json_str, encoding='utf-8')
    return output_file


def runForURLs (urls: list[str]|str,threaded: bool = True) -> list[Path]:
    """Run scraper for multiple URLs in parallel"""

    # If called for a single one
    if isinstance(urls, str):
        return [runForURL(url=urls)]
    # Run scraping in parallel using ThreadPoolExecutor
    if not threaded:
        files: list[Path | None] = [runForURL(url) for url in urls]  # pyright: ignore[reportRedeclaration]
    else:
        files: list[Path | None] = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Submit all tasks
            future_to_url = {executor.submit(runForURL, url): url for url in urls}
            
            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    output_file: Path | None = future.result()
                    files.append(output_file)
                    print(f"Completed scraping: {url} -> {output_file}")
                except Exception as e:
                    print(f"Error scraping {url}: {e}")
    return files

def main() -> None:
    versions = ['25d','26a']
    
    # Define all applications to scrape
    applications = {
        'oedpp': 'project-management',
        'oedmf': 'financials',
        'oedmp': 'procurement',
        'oedsc': 'supply-chain-and-manufacturing',
        'oedma': 'applications-common',
        
    }
    urlsExtra = ['https://docs.oracle.com/en/cloud/saas/human-resources/oedmh/hcm-tables-and-views.html']
    urls = []

    for version in versions:
    # Create URLs for all applications
        urls.extend([f"https://docs.oracle.com/en/cloud/saas/{long}/{version}/{short}/index.html" 
                for short, long in applications.items()])

    urls.extend(urlsExtra)
    # urls = urls[0:2]
    if len(urls) == 1:
        logger.setLevel(level=logging.DEBUG)      
    files = runForURLs(urls=sorted(urls),threaded=len(urls) > 1)
    print("Generated files:")
    for f in [f for f in files if f]:
        print(f)

if __name__ == "__main__":
    main()