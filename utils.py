from bs4 import BeautifulSoup



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

