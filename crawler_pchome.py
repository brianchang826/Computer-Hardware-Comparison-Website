from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from internal_assessment.specs_parser import Product, CPU, GPU, Motherboard, RAM, SSD, PSU, Case, AirCooler, AIOCooler
import requests
from bs4 import BeautifulSoup
from internal_assessment.specs_parser import Product
import time
from tqdm import tqdm
import re

base_url = "https://24h.pchome.com.tw"

# The urls of the subcategories that contains products that will have a different specs parser
# specifically picked since the categories are unreliable 
# for instance the category "顯示卡" (GPU) even contains CPU aircoolers

SELECTED_SUBCATEGORIES = [
    ("https://24h.pchome.com.tw/category/DSAJ01C", Motherboard, "主機板", "Intel平台"),
    ("https://24h.pchome.com.tw/category/DSAJ02C", Motherboard, "主機板", "AMD平台快選"),
    ("https://24h.pchome.com.tw/category/DRAE17C?attrs=G25I21411", AirCooler, "機殼/散熱", "水冷│散熱│DIY"),
    ("https://24h.pchome.com.tw/category/DRAE17C?attrs=G25I21410", AIOCooler, "機殼/散熱", "水冷│散熱│DIY"),
    ("https://24h.pchome.com.tw/category/DSAZ06C", PSU, "電源供應器", "品牌快選A-Z"),
    ("https://24h.pchome.com.tw/category/DRAC01C", RAM, "記憶體", "記憶體--品牌"),
    ("https://24h.pchome.com.tw/category/DRAH06C", SSD, "SSD", "| SSD品牌"),
    ("https://24h.pchome.com.tw/category/DRAE03C", Case, "機殼/散熱", "機殼品牌A-Z"),
    ("https://24h.pchome.com.tw/category/DRAI02C", CPU, "CPU", "AMD 系列館"),
    ("https://24h.pchome.com.tw/category/DRAI01C", CPU, "CPU", "INTEL 系列館"),
    ("https://24h.pchome.com.tw/category/DRAD21C", GPU, "顯示卡", "NVIDIA晶片"),
    ("https://24h.pchome.com.tw/category/DRAD22C", GPU, "顯示卡", "AMD 晶片"),
    ("https://24h.pchome.com.tw/category/DRAD67C", GPU, "顯示卡", "Intel 晶片"),
]

# The urls of the categories that contains products that will have a base "Product" spec parser
# this is picked since it is unable to crawl the entire site as it will take several days or even weeks (even if multiple instances)
# these categories will include most "computer hardwares" in the website

SELECTED_CATEGORIES = [
    ("筆記電腦", "https://24h.pchome.com.tw/region/DSAB"),
    ("桌上電腦", "https://24h.pchome.com.tw/region/DHAA"),
    ("商用電腦", "https://24h.pchome.com.tw/region/DSAA"),
    ("DIY電腦", "https://24h.pchome.com.tw/region/DSAM"),
    ("LCD螢幕", "https://24h.pchome.com.tw/region/DSAU"),
    ("SSD", "https://24h.pchome.com.tw/region/DRAH"),
    ("內接硬碟", "https://24h.pchome.com.tw/region/DRAB"),
    ("網路硬碟", "https://24h.pchome.com.tw/region/DRAG"),
    ("CPU", "https://24h.pchome.com.tw/region/DRAI"),
    ("主機板", "https://24h.pchome.com.tw/region/DSAJ"),
    ("顯示卡", "https://24h.pchome.com.tw/region/DRAD"),
    ("電源供應器", "https://24h.pchome.com.tw/region/DSAZ"),
    ("機殼/散熱", "https://24h.pchome.com.tw/region/DRAE"),
    ("記憶體", "https://24h.pchome.com.tw/region/DRAC"),
    ("電腦擴充", "https://24h.pchome.com.tw/region/DCAX"),
    ("鍵盤", "https://24h.pchome.com.tw/region/DCAH"),
    ("滑鼠", "https://24h.pchome.com.tw/region/DCAN"),
    ("喇叭", "https://24h.pchome.com.tw/region/DCAI"),
    ("藍芽耳機/耳機", "https://24h.pchome.com.tw/region/DYAQ"), 
    ("錄音/音訊周邊", "https://24h.pchome.com.tw/region/DGAF")
]

UNWANTED_PATTERNS = ["推薦", "促銷", "回饋", "新品", "折價", "價格", "$", "館長", "活動", "南紡", "優惠"]

SOURCE_NAME = "Pchome"

def filter_subcategory(title: str) -> bool:
    """ Check whether the subcategory titles contain unwanted patterns """
    for pattern in UNWANTED_PATTERNS:
        if pattern in title:
            return False
    return True

def get_subcategories(category_url: str) -> list[tuple[str, str]]|None:
    """
    Return a list of tuples containing the title and url of the subcategories.\n
    Format: (title, url)
    Use the url of a category as input. 
    """

    html = requests.get(category_url).text
    parsed_html = BeautifulSoup(html, "html.parser")
    
    # locate the menu element (contains the subcategories)
    menu = parsed_html.select_one(".c-sideMenu")
    if not menu:
        return None
    
    # locate the elements that hold the details of each subcategory
    subcategories = menu.select(".c-menuList__titleHtml")
    subcategory_details = []
    
    if not subcategories:
        return None
    
    # iterate over each element to extract information
    for subcategory in subcategories:
        try:
            url = base_url + subcategory["href"]
            title = subcategory.text
            
            if not filter_subcategory(title):
                continue

            subcategory_details.append((title, url))
        except:
            continue
    return subcategory_details

def return_data_subcategory(subcategory_url: str, parser: Product, category_title: str|None = None, subcategory_title: str|None = None) -> list[Product]:
    """
    Return all items under a subcategory.\n
    Selenium is used to access the website and the raw source html is passed to Beautifulsoup to parse.\n
    This is because the "webelement" in Selenium is dynamic and can changed as the webpage updates, which cause a lot of errors when accessing these elements.
    """
    opt = Options()
    opt.add_argument("headless")
    driver = webdriver.Chrome(options=opt)
    driver.get(subcategory_url)
    
    products = []

    time.sleep(0.1)

    # Get the current static html (there are many problems with dynamic webelements)
    parsed_html = BeautifulSoup(driver.page_source, "html.parser")
    
    # Use the number of total items to estimate the number of pages (40 items / page)
    # because it is not able to determine if we reached the end of pages since it will just load the content of the first page
    total_item_num = parsed_html.select(".c-pagination__text")
    if total_item_num:
        page_num = int(re.sub(r"\D", "", total_item_num[0].text)) // 40 + 1
    else:
        page_num = 1
    
    # Go through each page
    for n in range(1, page_num+1):
        url = f"{subcategory_url}?p={n}"
        if "?attrs" in subcategory_url:
            url = f"{subcategory_url}&p={n}"
        
        driver.get(url)
        time.sleep(0.1)
        
        items = BeautifulSoup(driver.page_source, "html.parser").select(".c-listInfoGrid__item") # locate items 

        if not items:
            break
        
        # get details for each item
        for item in tqdm(items):
            ads = item.select(".c-prodInfoV2__prodTypeLabel--adLabel")
            title = item.select(".c-prodInfoV2__title")
            price = item.select(".c-prodInfoV2__priceValue")
            product_url = base_url + item.select_one(".c-prodInfoV2__link")["href"]

            if ads or not title or not price:
                continue
            
            products.append(parser(title[0].text, price[0].text, category_title, subcategory_title, product_url, SOURCE_NAME))
        
        page_num += 1

    driver.close()
    return products

def return_data_selected_subcategories(subcategories: list[tuple]):
    dataset = []
    for arg in subcategories:
        dataset.extend(return_data_subcategory(*arg))
    return dataset

def return_data_selected_categories():
    """
    Return all items under a subcategory.\n
    """
    args = []
    
    # avoid going to the same page twice
    repeated_urls = [subcategory[0] for subcategory in SELECTED_SUBCATEGORIES]
    
    # iterate over each category and get its subcategories 
    for category_title, category_url in SELECTED_CATEGORIES:
        subcategories = get_subcategories(category_url)
        
        # avoid going to the same page twice
        subcategories = [subcategory for subcategory in subcategories if not subcategory[1] in repeated_urls]
        
        if not subcategories:
            continue
        
        # convert it to a tuple form (use as arguments for func return_data_selected_subcategories())
        for subcategory_title, subcategory_url in subcategories:
            args.append((subcategory_url, Product, category_title, subcategory_title))

    return return_data_selected_subcategories(args)
    
