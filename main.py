from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from db import sheet, col_index, get_db_data
import time
import threading
import curl_cffi
import random
_session_lock = threading.Lock()
_shared_session: curl_cffi.Session | None = None

SCRAPING_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
    "accept-encoding": "gzip, deflate",
    "upgrade-insecure-requests": "1",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-dest": "document",
    "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "connection": "keep-alive",
}


sheet_data = get_db_data()
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


def grab_categories_emag() -> list:

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
            
            #sheet.append_row([cat_name, subcat_name,full_link])  old append cats
    
    return all_categories_emag
            
def get_new_cats():

    new_categories = []

    emag_cats = grab_categories_emag()

    for cat in emag_cats:
        found = False
        for row in sheet_data:
            if row["category"] == cat["main_cat"] and row["subcategory"] == cat["subcat"]:
                found = True
        
        if not found:
            new_categories.append(cat)

    return new_categories




col_index = col_index()

def grab_sku(url):
    try:
        response = session.get(url)

        soup = BeautifulSoup(response.text, 'html.parser')
        sku = soup.find("div", class_="main-container-inner").find("main", class_="main-container").find("section", class_="page-section").find("div", class_="container").find("div", class_="justify-content-between").find("span", class_="product-code-display").text
        return sku.replace("                    Cod produs: ", "").strip()
    except:
        return None
    
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