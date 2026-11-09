from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from tqdm import tqdm
from bs4 import BeautifulSoup 
from io import StringIO
from specs_parser import Product, CPU, GPU, Motherboard, RAM, SSD, PSU, Case, AirCooler, AIOCooler
from utils import find_elements_until_exists
import time
import requests
import pandas

# Dictionaries used to match the category index with the specs parser
COOLPC_CLASS_DICT = {4: CPU, 12: GPU, 5: Motherboard, 6: RAM, 7: SSD, 15: PSU, 14: Case, 10: AirCooler, 11: AIOCooler}
SINYA_CLASS_DICT = {7: CPU, 12: GPU, 8: Motherboard, 9: RAM, 10: SSD, 15: PSU, 16: Case, 13: AirCooler, 14: AIOCooler}

COOLPC_SOURCE_NAME = "Coolpc"
SINYA_SOURCE_NAME = "Sinya"

COOLPC_ALL_CATEGORY_IDXS = range(1, 31)
SINYA_ALL_CATEGORY_IDXS = range(0, 35)

def return_data_sinya(idxs: list[int]|None = None, crawl_all_category: bool = False) -> list[Product]:
    """
    Return all items under the given categories (idxs).\n
    If crawl_all_category is set to True, then the first parameter will be ignored.\n
    Selenium is used to interact with the page to load products while Beaitifulsoup is used to parse their details.
    """
    def create_driver() -> webdriver.Chrome:
        """ Create a Chrome webdriver """
        driver = webdriver.Chrome()
        driver.set_window_size(1000, 2200) # allow the entire page to be rendered at once
        driver.get("https://www.sinya.com.tw/")
        return driver
    
    def close_ad_window(driver: webdriver.Chrome):
        """ Close the ad window if found one """
        try:
            ad_close_button = driver.find_element(By.CLASS_NAME, "diyAdBox").find_element(By.CLASS_NAME, "btn")
            ad_close_button.click()
        except:
            pass

    def load_categories(driver: webdriver.Chrome):
        """ Allow all categories to be displayed on the window at once """
        actions = ActionChains(driver)
        time.sleep(0.5)
        actions.move_by_offset(200, 200).scroll_by_amount(0, 500).perform()

    def enter_category(category: WebElement):
        """ Enter the category to load subcategories """
        category.click()
        time.sleep(0.1)

    def open_subcategories(driver: webdriver.Chrome):
        """ Open (click) the subcategories to load products """
        subcategories = find_elements_until_exists(driver, 90, By.CLASS_NAME, "groupBox")
        time.sleep(0.1)
        
        external_link_count = 0
        for subcategory in tqdm(subcategories):
            subcategory.click()
            time.sleep(0.4)
            
            # close tab if clicking elements leading to an external link
            tabs = driver.window_handles
            if len(tabs) <= 1:
                continue
            driver.switch_to.window(tabs[1])
            driver.close()
            time.sleep(0.3)
            driver.switch_to.window(tabs[0])
            external_link_count += 1
        
        # wait for items to load after clicking on the group
        while True:
            opened_subcategories = len(driver.find_elements(By.CSS_SELECTOR, ".title.open"))
            if opened_subcategories + external_link_count == len(subcategories):
                break
            time.sleep(0.3)

    def get_products(html: str, category_title: str, parser: Product) -> list[Product]:
        """ Get the details of the products under the category after loading the subcategories """
        
        products = []
        
        # Use BeautifulSoup since it's much faster than selenium
        parsed_html = BeautifulSoup(html, "html.parser")
        subcategories = parsed_html.select(".groupBox")
        
        for subcategory in subcategories:
            # skip if it is an empty subcategory
            if not subcategory.select(".title.open"):
                continue

            subcategory_title = subcategory.select_one(".title.open").select_one(".left").text
            items = subcategory.select(".prod")

            for item in items:
                # skip if the item is used as a label rather than an actual product
                if not item.select(".price"):
                    continue
                title = item.select_one(".left").text
                price = item.select_one(".price").text
                product = parser(title, price, category_title, subcategory_title, None, SINYA_SOURCE_NAME)
                products.append(product)

        return products
    
    def exit_category(driver: webdriver.Chrome):
        """ Exit the current category """
        time.sleep(0.1)
        try:
            close_btn = driver.find_element(By.CLASS_NAME, "diyModal").find_element(By.CLASS_NAME, "btn")
            close_btn.click()
        except:
            pass
        time.sleep(0.5)
    
    # -----------------------------------------------
    # main process

    start = time.time()
    
    all_products = []
    if crawl_all_category:
        idxs = SINYA_ALL_CATEGORY_IDXS
    
    driver = create_driver()
    
    close_ad_window(driver)
    load_categories(driver)
    
    categories = driver.find_elements(By.CLASS_NAME, "diyRow")
    
    # iterate over each selected category
    for idx in idxs:

        category_title = categories[idx].find_element(By.CSS_SELECTOR, ".diyClass.showWeb").text
        parser = match_sinya_idx(idx)

        enter_category(categories[idx])
        open_subcategories(driver)

        products = get_products(driver.page_source, category_title, parser)
        all_products.extend(products)
        
        exit_category(driver)

    driver.close()
    print(f"Successfully return {len(all_products)} items in {round(time.time() - start, 2)}s ({idxs})")
    return all_products

def return_data_coolpc(idxs: list[int]|None = None, crawl_all_category: bool = False) -> list[Product]:
    """
    Return all items under the given categories (category_idx).\n
    If crawl_all_category is set to True, then the first parameter will be ignored.\n
    Only requests and Beautifulsoup are used since the entire site can be crawled with one request.
    """
    
    html = requests.get("https://www.coolpc.com.tw/evaluate.php").text
    parsed_html = BeautifulSoup(html, "html.parser")
    
    # get category titles
    table_html = parsed_html.find("table", attrs={"id": "Tfix"})
    parsed_table = pandas.read_html(StringIO(str(table_html)))[0]
    category_titles = list(parsed_table[1])[0:30]
    
    if crawl_all_category:
        idxs = COOLPC_ALL_CATEGORY_IDXS
    
    all_products = []

    # iterate over each selected category
    for idx in idxs:
        
        category = parsed_html.find("select", attrs={"name": f"n{idx}"}) # is a <select> and a class name of n{idx}
        category_title = category_titles[idx-1]
        parser = match_coolpc_idx(idx)

        subcategories = category.select("optgroup")
        
        # iterate over each subcategory
        for subcategory in subcategories:
            
            items = subcategory.find_all("option", recursive=False)
            subcategory_title = subcategory.get("label")
            
            for item in items:
                title = item.text
                
                # skip if the item is used as a label rather than an actual product
                if not "$" in title:
                    continue

                product = parser(title, None, category_title, subcategory_title, None, COOLPC_SOURCE_NAME)
                all_products.append(product)

    return all_products

def match_coolpc_idx(input_idx: int):  
    """ Determine the parser by the idx of the category """
    try:
        return COOLPC_CLASS_DICT[input_idx]
    except:
        return Product

def match_sinya_idx(input_idx: int):
    """ Determine the parser by the idx of the category """
    try:
        return SINYA_CLASS_DICT[input_idx]
    except:
        return Product

if __name__ == "__main__":
    products = return_data_sinya([7, 8])
    print(products[0].name)
    print(products[0].price_int)
    print(products[0].manufacturer)
    print(products[0].source)
    print(products[0].category)
    print(products[0].subcategory)
