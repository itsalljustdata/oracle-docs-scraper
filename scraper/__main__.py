
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
    outFileName = '.'.join(outFileParts) + '.views.json'
    output_file = Path('.').joinpath('output',outFileName)

    if not output_file.parent.exists():
        output_file.parent.mkdir(parents=True, exist_ok=True)
    elif output_file.exists():
        output_file.unlink()

    scraper = OracleDocsScraper(url, delay=1.0)
    views_data = scraper.scrape_all_views()
    
    if not views_data:
        logger.error(msg=f"No views data scraped for URL: {url}")
        return None


    remaps = [('query','pretty'),('query_databricks','converted'),('error','conversion_error')]

    for v in views_data:
        if 'query' in v:

            v['tables'] = extract_table_names(v['query'])
            result: dict[str,str|None] = convert_single_query(oracle_sql=v['query'])

            for v_key, r_key in remaps:
                if (r_value := result.get(r_key,None)) is not None:
                    v[v_key] = r_value
    
    obj = dict(
        product = outFileParts[0].replace('-',' ').title(), 
        url = url,
        numViews = len(views_data),
        views = views_data
    )

    # Custom JSON formatting to preserve line feeds in queries
    json_str = json.dumps(obj, indent=2, ensure_ascii=False)
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
    files = []
    if not threaded:
        files = [runForURL(url) for url in urls]
    else:
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_url = {executor.submit(runForURL, url): url for url in urls}
            
            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    output_file = future.result()
                    files.append(output_file)
                    print(f"Completed scraping: {url} -> {output_file}")
                except Exception as e:
                    print(f"Error scraping {url}: {e}")
    return files

def main() -> None:
    version = '25d'
    
    # Define all applications to scrape
    applications = {
        'oedpp': 'project-management',
        'oedmf': 'financials',
        'oedmp': 'procurement',
        'oedsc': 'supply-chain-and-manufacturing',
        'oedma': 'applications-common',
        
    }
    urlsExtra = ['https://docs.oracle.com/en/cloud/saas/human-resources/oedmh/hcm-tables-and-views.html']
    
    # Create URLs for all applications
    urls = [f"https://docs.oracle.com/en/cloud/saas/{long}/{version}/{short}/index.html" 
            for short, long in applications.items()]
    urls.extend(urlsExtra)
    files = runForURLs(urls=sorted(urls),threaded=True)
    print("Generated files:")
    for f in files:
        print(f)

if __name__ == "__main__":
    main()