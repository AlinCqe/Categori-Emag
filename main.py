from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import threading
import curl_cffi
import time
import random

from db import sheet, col_index, get_db_data
from utils import grab_sku_from_link, find_insert_row, col_index_to_letter


_session_lock = threading.Lock()
_shared_session: curl_cffi.Session | None = None

SCRAPING_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
    "accept-encoding": "gzip, deflate",
    
    "connection": "keep-alive",
}



base_emag_url = "https://www.emag.ro"

def get_shared_session() -> curl_cffi.Session:
    global _shared_session

    with _session_lock:
        if _shared_session is None:
            session = curl_cffi.Session()
            session.headers.update(SCRAPING_HEADERS)
            _shared_session = session

        return _shared_session
    
session = get_shared_session()


def get_item_page_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()

        page.goto("https://www.emag.ro/brands/brand/nextly?ref=grid")

        btn = page.locator(".js-more-rupture-categories")
        btn.wait_for(state="visible")
        btn.click()

        page.wait_for_load_state("networkidle")

        html = page.content()

        browser.close()
        return html


def extract_categories():

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

            results.append({
                "main_cat": main_cat,
                "subcat":  subcat.get("name"),
                "cat_link": urljoin(base_emag_url, subcat.get("url", {}).get("path"))
            })


    return results

            
def get_new_cats(sheet_data) -> list:

    new_categories = []

    emag_cats = extract_categories()

    for cat in emag_cats:
        found = False
        for row in sheet_data:
            if row["category"] == cat["main_cat"] and row["subcategory"] == cat["subcat"]:
                found = True
        
        if not found:
            new_categories.append(cat)

    return new_categories



"""
def grab_skus_new_cats(new_cats: list) -> list:
    updated_new_cats = list(new_cats)

    for index, cat in enumerate(new_cats):

        url = cat["cat_link"]

        try:
            print(url)
            response = session.get(url)
        except Exception as e:
            print(e)
            return None

        if response.status_code != 200:
            print("error", f"Failed request {url}, status {response.status_code}. Stopping grab_links.")
            return None
        
        print("info", f"Request to {url}, status {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        container = soup.find("div", class_="js-products-container")
        if not container:
            print("error", f"Products container not found at {url}. Stopping grab_links.")
            return None


        items = container.find_all("div", class_="card-item")
        bulk_skus = []
       
        for item in items:

            item_link = item.get("data-url", None)

            if not item_link:
                continue
            
            sku = grab_sku_from_link(session=session, url=item_link)
            if sku:
                bulk_skus.append(sku)
            time.sleep(random.randint(2, 6))

        print("info", f"Scraped {len(bulk_skus)} bulk items from {url}")

        time.sleep(3)

        if bulk_skus:

            updated_new_cats[index]["skus"] = bulk_skus
        
        else:
            print("error", f"No SKUs found for link: {url}")

    return updated_new_cats
"""


def write_new_categories():
    sheet_data = get_db_data()
    new_categories = get_new_cats(sheet_data)


    print("New cats", new_categories)
    for cat in new_categories:
        print(cat)



        prepared_row_data = [cat["main_cat"], cat["subcat"], cat["cat_link"]]

        sheet_data = get_db_data()
        row_index = find_insert_row(rows=sheet_data, category=cat["main_cat"])

        start_col = 4

        sheet.insert_row(
            prepared_row_data,
            row_index
        )
        print(f"Inserted in row {row_index}: {prepared_row_data}")
        time.sleep(2)



write_new_categories()

"""            col_range = (
                f"{col_index_to_letter(start_col)}{row_index}:"
                f"{col_index_to_letter(end_col)}{row_index}"
            )"""


"""        sheet.insert_row(
        [category, subcategory],
        row_index
)"""



"""

def scrape_categories_skus(page, data: list) -> list:
    bugged_links = []
    scraped_categories_and_skus = []
    for row in data:
        
        url = row["link"].strip().replace("c?ref=see_more_rupture", "sort-offer_iddesc")

        try:
            print(url)
            page.goto(url)
            
            page.wait_for_load_state("networkidle")

            html = page.content()
        except Exception as e:
            print(e)
            bugged_links.append([{url}, "error:", {e}])
            continue




        soup = BeautifulSoup(html, 'html.parser')

        if not soup.find("div", class_="js-products-container"):
            print(f"Soft block or empty container at {url}")
            continue

        container = soup.find("div", class_="js-products-container")
        if not container:

            print("error", f"Products container not found at {url}. Stopping grab_links.")
            bugged_links.append(["error", f"Products container not found at {url}. Stopping grab_links."])
            return None


        items = container.find_all("div", class_="card-item")
        bulk_skus = []
    
        for item in items:

            item_link = item.get("data-url", None)

            if not item_link:
                continue
            
            sku = grab_sku_from_link(page=page, url=item_link)
            
            if sku:
                bulk_skus.append(sku)
                bugged_links.append([item_link, "couldnt grab sku"])
            time.sleep(random.randint(4, 7))

        print("info", f"Scraped {len(bulk_skus)} bulk items from {url}")

        time.sleep(3)

        if bulk_skus:

            scraped_categories_and_skus.append({"category": row["category"], "subcategory": row["subcategory"], "skus": bulk_skus})
        else:
            print("error", f"No SKUs found for link: {url}")
    print(bugged_links)
    return scraped_categories_and_skus
        


def write_new_skus():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()


        sheet_data = get_db_data()
        
        scraped_categories_skus = scrape_categories_skus(page=page, data=sheet_data)
        print(scraped_categories_skus)


        browser.close()

write_new_skus()

"""





































"""

col_index = col_index()


    
data = sheet.get_all_records() 

def grab_links():


    for row_index, row in enumerate(data, start=2):
        bulk_items = []
        url = row["link"]

        if row["sku-uri"] != "":
            print(row["sku-uri"])
            continue

        try:
            print(url)
            response = session.get(url)
        except Exception as e:
           
            return None

        if response.status_code != 200:
            print("error", f"Failed request {url}, status {response.status_code}. Stopping grab_links.")
            return None
        
        print("info", f"Request to {url}, status {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        container = soup.find("div", class_="js-products-container")
        if not container:
            print("error", f"Products container not found at {url}. Stopping grab_links.")
            return None


        items = container.find_all("div", class_="card-item")
        bulk_skus = []
       
        for item in items:
            sku = grab_sku(item.get("data-url"))
            print(sku)
            if sku:
                bulk_skus.append(sku)
            time.sleep(random.randint(2, 6))

        print("info", f"Scraped {len(bulk_items)} bulk items from {url}")

        time.sleep(3)

        if bulk_skus:
            
            start_col = 4
            end_col = start_col + len(bulk_skus) - 1

            
            def col_index_to_letter(index):
                result = ""
                while index > 0:
                    index, remainder = divmod(index - 1, 26)
                    result = chr(65 + remainder) + result
                return result

            col_range = f"{col_index_to_letter(start_col)}{row_index}:{col_index_to_letter(end_col)}{row_index}"

            
            sheet.update(col_range, [bulk_skus])




def grab_links2():


    for row_index, row in enumerate(data, start=2):

        bulk_skus = []
        if row["subcategory"] != "Tapet":
            print(row["subcategory"])
            continue
        for i in range(1, 9):
            print(bulk_skus)
            print(len(bulk_skus))
            url = f"https://www.emag.ro/brands/tapet/brand/nextly/p{i}/c"

            try:
                print(url)
                response = session.get(url)
            except Exception as e:
            
                return None

            if response.status_code != 200:
                print("error", f"Failed request {url}, status {response.status_code}. Stopping grab_links.")
                return None
            
            print("info", f"Request to {url}, status {response.status_code}")

            soup = BeautifulSoup(response.text, 'html.parser')

            container = soup.find("div", class_="js-products-container")
            if not container:
                print("error", f"Products container not found at {url}. Stopping grab_links.")
                return None


            items = container.find_all("div", class_="card-item")

        
            for item in items:
                sku = grab_sku(item.get("data-url"))
                print(sku)
                if sku:
                    bulk_skus.append(sku)
                time.sleep(random.randint(2, 3))

            print("info", f"Scraped {len(bulk_skus)} bulk items from {url}")

            time.sleep(3)

        if bulk_skus:
            
            start_col = 4
            end_col = start_col + len(bulk_skus) - 1

            
            def col_index_to_letter(index):
                result = ""
                while index > 0:
                    index, remainder = divmod(index - 1, 26)
                    result = chr(65 + remainder) + result
                return result

            col_range = f"{col_index_to_letter(start_col)}{row_index}:{col_index_to_letter(end_col)}{row_index}"

            
            sheet.update(col_range, [bulk_skus])

grab_links2()

"""