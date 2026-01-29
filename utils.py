from bs4 import BeautifulSoup

def grab_sku_from_link(session, url):
    try:
        response = session.get(url)

        soup = BeautifulSoup(response.text, 'html.parser')
        sku = soup.find("div", class_="main-container-inner").find("main", class_="main-container").find("section", class_="page-section").find("div", class_="container").find("div", class_="justify-content-between").find("span", class_="product-code-display").text
        return sku.replace("                    Cod produs: ", "").strip()
    except:
        return None
    

def find_insert_row(rows, category):
    last_match = None

    for i, row in enumerate(rows, start=1): 
        if row and row["category"] == category:
            last_match = i

    if last_match:
        return last_match + 1  
    else:
        return len(rows) + 1  
    
def col_index_to_letter(index):
    result = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result