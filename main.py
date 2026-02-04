from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import curl_cffi
import time

from db import sheet, get_db_data
from utils import find_insert_row

SCRAPING_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
    "accept-encoding": "gzip, deflate",
    
    "connection": "keep-alive",
}


base_emag_url = "https://www.emag.ro"

def get_item_page_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()

        page.goto("https://www.emag.ro/brands/brand/nextly?ref=grid")

        btn = page.locator(".js-more-rupture-categories")
        btn.wait_for(state="visible")
        btn.click()

        page.wait_for_load_state("networkidle")

        html = page.content()

        browser.close()
        return html

def extract_categories_html() -> list:

    all_categories_emag = []

    html = get_item_page_html()
    soup = BeautifulSoup(html, "html.parser")
    categories = soup.find_all("div", class_="js-filter-letter-group")

    for cat in categories:
        cat_name = cat.find("div", class_="col-sm-12").select_one("h2 span").get_text(strip=True)
        subcats = cat.find_all("div", class_="filter-item")

        for subcat in subcats:
            subcat_name = subcat.find("div", class_="category-name").text

            a = subcat.select_one("a[href]")
            link = a.get("href") if a else None
            full_link = urljoin(base_emag_url, link)

            all_categories_emag.append({"main_cat": cat_name, "subcat": subcat_name, "cat_link": full_link})
            

    return all_categories_emag
            
def extract_categories_api():

    data = curl_cffi.get("https://sapi.emag.ro/get-more-rupture-categories?source_id=7&filters%5Bpage_type%5D=brands&filters%5BhasFiltersSelected%5D=false&filters%5Bsubdepartment%5D%5B%5D=wearables-gadgeturi&filters%5Bdepartment%5D%5B%5D=laptop-tablete-telefoane&filters%5Bcategory%5D%5B%5D=2991&filters%5Bbrand%5D%5B%5D=739747&filters%5Bshop_id%5D=1",headers=SCRAPING_HEADERS).json()

    results = []

    items = (
        data
        .get("data", {})
        .get("recommended_categories", {})
        .get("items", [])
    )

    for cat in items:


        main_cat = cat.get("name")

        for subcat in cat.get("items", []):

            results.append({"main_cat": main_cat, "subcat": subcat.get("name"), "cat_link": urljoin(base_emag_url, subcat.get("url", {}).get("path"))})


    return results

def merge_scraped_cats(existing: list, incoming: list) -> list:
    seen = {
        (c["main_cat"], c["subcat"])
         for c in existing
    }


    for cat in incoming:
        if (cat["main_cat"], cat["subcat"]) not in seen:
            existing.append(cat)
            seen.add((cat["main_cat"], cat["subcat"]))

    print(f"Total scraped categories: {len(existing)}")

    return existing



def compare_new_cats(sheet_data, scraped_categories) -> list:

    new_categories = []


    print(f"API cats, {len(scraped_categories)}: {scraped_categories}", )
    
    for cat in scraped_categories:
        found = False
        for row in sheet_data:
            if row["category"] == cat["main_cat"] and row["subcategory"] == cat["subcat"]:
                found = True
        
        if not found:
            new_categories.append(cat)

    return new_categories



def write_new_categories():

    scraped_cats_html = extract_categories_html()
    scraped_cats_api = extract_categories_api()

    merged_scraped_data = merge_scraped_cats(scraped_cats_api, scraped_cats_html)

    sheet_data = get_db_data()

 
    new_categories = compare_new_cats(sheet_data=sheet_data, scraped_categories=merged_scraped_data)


    print("New cats", new_categories)
    for cat in new_categories:

        prepared_row_data = [cat["main_cat"], cat["subcat"], cat["cat_link"]]

        sheet_data = get_db_data()
        row_index = find_insert_row(rows=sheet_data, category=cat["main_cat"])


        sheet.insert_row(
            prepared_row_data,
            row_index
        )
        sheet.format(
            f"A{row_index}:Z{row_index}",
            {
                "backgroundColor": {"red": 1, "green": 1, "blue": 1},
                "textFormat": {
                    "bold": False,
                    "italic": False
                }
            }
        )
        
        print(f"Inserted in row {row_index}: {prepared_row_data}")
        time.sleep(2)





write_new_categories()








































