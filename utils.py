from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.remote.webelement import WebElement
import urllib.robotparser
import re
from typing import Any

def is_url_allowed(root_url: str, url_to_check: str):
    """
    Check whether the given url is allowed to be crawled (based on the site's robots.txt)
    """
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{root_url}/robots.txt")
    rp.read()
    user_agent = "*"
    return rp.can_fetch(user_agent, url_to_check)

def extract_int(s: str):
    return re.sub(r"\D", "", s)

def find_element_until_exists(driver: webdriver.Chrome|WebElement, wait_time_s: int, by: Any, expected_value: str):
    try:
        return WebDriverWait(driver, wait_time_s).until(expected_conditions.presence_of_element_located((by, expected_value)))
    except:
        return None

def find_elements_until_exists(driver: webdriver.Chrome|WebElement, wait_time_s: int, by: Any, expected_value: str):
    try:
        return WebDriverWait(driver, wait_time_s).until(expected_conditions.presence_of_all_elements_located((by, expected_value)))
    except:
        return None

def split_list(input_list: list, num_of_output_list: int):
    """
    Separate the elements in one list equally to a specific number of lists
    """
    length = len(input_list)

    chunk_size = length // num_of_output_list
    remainder = length % num_of_output_list

    if remainder != 0:
        chunk_size += 1

    output_list = []
    idx = 0

    for _ in range(num_of_output_list - 1):
        output_list.append(input_list[idx:idx+chunk_size])
        idx += chunk_size

    output_list.append(input_list[idx:length])

    return output_list

def validate_value_range(input_value: int|float, min_value: int|float|None, max_value: int|float|None) -> int|float|None:
    """ Check if the input_value is within the range of the given min_value and max_value """
    if (min_value and input_value < min_value) or (max_value and input_value > max_value):
        return None
    return input_value