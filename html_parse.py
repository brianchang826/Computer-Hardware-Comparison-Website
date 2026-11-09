from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas
from io import StringIO
from collections import OrderedDict
import re

INTEL_CHIPSET_DICT = {"LGA1200": "Z590", "LGA1700": "Z690", "LGA1851": "Z890"}
AMD_CHIPSET_DICT = {"AM4": "B550", "AM5": "B650"}

def replace_whitespaces(dataframe: pandas.DataFrame):
    """
    Replace whitespaces in the column names of a dataframe with "_"
    """
    dataframe.columns = dataframe.columns.str.replace(r"\s+", "_", regex=True)
    return dataframe

def remove_references(dataframe: pandas.DataFrame):
    """
    Remove the wikipedia reference/citation patterns [] for every element in a dataframe
    """
    for column_name in dataframe.columns:
        if dataframe[column_name].dtype == "object":
            dataframe[column_name] = dataframe[column_name].str.replace(r"\[[\S\s]+\]", "", regex=True)
    return dataframe

def get_html_tables(url: str, table_class_name: str, pattern_dict: dict, csv_filename: str|None = None, invert_table_name: str|None = None):
    """
    Get html tables given the url and pattern_dict (in the format of {name: pattern})\n
    A pattern needs to be unique to one table\n
    Parse the tables with pandas and convert it to dataframes\n
    Then output each of the dataframe to a csv file\n
    The rows and columns of a specific table can be exchanged if given a invert_table_name (needs to match the name in pattern_dict)
    """
    opt = Options()
    opt.add_argument("headless")
    driver = webdriver.Chrome(options=opt)
    driver.get(url)
    tables = driver.find_elements(By.CLASS_NAME, table_class_name)
    
    for table in tables:
        for name, pattern in pattern_dict.items():
            if pattern not in table.text:
                continue
            html = table.get_attribute("outerHTML")
            parsed_table = pandas.read_html(StringIO(html))[0]
            parsed_table = remove_references(parsed_table)
            if invert_table_name and name == invert_table_name:
                parsed_table = parsed_table.transpose()
            parsed_table.to_csv(f"{csv_filename}_{name}.csv")


def get_html_table(url: str, table_class_name: str, pattern_dict: dict, csv_filename: str):
    """
    Get html tables given the url and pattern_dict (in the format of {name: pattern})\n
    A pattern needs to be unique to one table\n
    Parse the tables with pandas and convert it to dataframes\n
    Concat all dataframes based on each of its column names\n
    Then output one final dataframe to a csv file
    """
    
    opt = Options()
    opt.add_argument("headless")
    driver = webdriver.Chrome(options=opt)
    driver.get(url)
    tables = driver.find_elements(By.CLASS_NAME, table_class_name)
    
    parsed_tables: list[pandas.DataFrame] = []

    for table in tables:
        for name, pattern in pattern_dict.items():
            if pattern not in table.text:
                continue
            html = table.get_attribute("outerHTML")
            parsed_table = pandas.read_html(StringIO(html))[0]
            parsed_table = remove_references(parsed_table)
            parsed_tables.append(parsed_table)
            
    output = pandas.concat(parsed_tables, ignore_index=True)
    
    # flatten multilayers of column names
    flattened_columns = []
    for column in output.columns:
        flattened_columns.append("_".join(list(OrderedDict.fromkeys(column))))
    output.columns = flattened_columns
    
    output.to_csv(csv_filename, index=False)

unwanted_pattern_start = ["(", "[", "\""]
unwanted_pattern_end = [")", "]", "\""]
suffixes = ["Technology", "Technologies", "Inc.", "Inc", "Enterprise", "Semiconductor", "Corporation", "Electronics", "Systems", "Computer", "International"]

def get_hardware_manufacturers():
    opt = Options()
    opt.add_argument("headless")
    driver = webdriver.Chrome(options=opt)
    driver.get("https://en.wikipedia.org/wiki/List_of_computer_hardware_manufacturers")
    groups = driver.find_elements(By.CLASS_NAME, "div-col")

    output = []

    for group in groups:
        manufacturers = group.find_elements(By.TAG_NAME, "li")
        for manufacturer in manufacturers:
            output.append(manufacturer.text)

    driver.close()

    print(len(output))

    output = list(set(output))

    return output

def filter_manufacturers(manufacturer_names: list[str]) -> list[str]:
    
    output = []
    
    for name in manufacturer_names:
        # remove citations and parathesis from wikipeida
        for start, end in zip(unwanted_pattern_start, unwanted_pattern_end):
            name = re.sub(rf"\{start}.*\{end}", "", name)
        
        # remove 
        name = re.sub(r"\:.*", "", name)
        name = re.sub(r"\,.*", "", name)
        
        # remove general suffixes
        for suffix in suffixes:
            name = re.sub(rf"{suffix}", "", name)

        # remove remaining whitespaces
        name = name.rstrip()
        
        output.append(name)

    # remove repeating names
    output = list(set(output))

    return output

def get_chipset_specs():
    get_html_tables("https://en.wikipedia.org/wiki/List_of_AMD_chipsets", "wikitable", AMD_CHIPSET_DICT, "AMD_Chipset_Specs.csv", "AM5")
    get_html_table("https://en.wikipedia.org/wiki/List_of_Intel_chipsets", "wikitable", INTEL_CHIPSET_DICT, "Intel_Chipset_Specs.csv")