from utils import validate_value_range
import re
import sqlite3

PSU_RATING_DICT = {
    "鈦金": "80 Plus Titanium",
    "白金": "80 Plus Platinum",
    "金牌": "80 Plus Gold",
    "銀牌": "80 Plus Silver",
    "銅牌": "80 Plus Bronze",
    "白牌": "80 Plus White",
}

PSU_MODULAR_DICT = {"全模": "Full", "半模": "Semi", "直出線": "Non"}

PSU_ATX_STANDARD_DICT = {r"atx[\S\s]*3.0": "ATX 3.0", r"atx[\S\s]*3.1": "ATX 3.1"}

SSD_MEMORY_TYPES = ["TLC", "QLC"]

SSD_CAPACITY_DICT = {r"(\d+)GB?": 1, r"(\d+)TB?": 1024}

RAM_CAPACITY_DICT = {r"(\d+)GB?[\*x]4": 4, r"(\d+)GB?[\*x]2": 2, r"(\d+)GB?[^0-9A-Z]": 1}

AIOCOOLER_LENGTHS = [120, 240, 280, 360, 420]

MB_FORM_FACTOR_DICT = {
    "mini-itx": "Mini-ITX",
    "mitx": "Mini-ITX",
    "m-atx": "M-ATX",
    "matx": "M-ATX",
    "e-atx": "E-ATX",
    "itx": "ITX",
    "atx": "ATX"
}

CASE_GPU_LENGTH_DICT = {r"卡長(\d+\.?\d*)": 1, r"顯卡(\d+)mm": 0.1}

CASE_CPU_HEIGHT_DICT = {r"u高(\d+\.?\d*)": 1, r"塔散(\d+)mm": 0.1}

def get_manufacturer_names(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """
    Return a list of manufacturer names in the format of (chinese_name, en_name)
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM manufacturers")
    names = cursor.fetchall()
    return names

def get_gpu_names(conn: sqlite3.Connection, start_date: str) -> list[str]:
    """ 
    Return a list of gpu names
    Parameters:
        conn (sqlite3.Connection): connection
        start_date (str): Starting date for the selected gpus (format: YYYY-MM-DD)
    """
    cursor = conn.cursor()
    cursor.execute(f"SELECT gpu_name FROM gpu_specs WHERE release_date >= '{start_date}' AND display_connectors IS NOT NULL AND display_connectors != 'Unknown' AND display_connectors != ''")
    names = [name[0] for name in cursor.fetchall()]
    return names

def get_chipset_names(conn: sqlite3.Connection) -> list[str]:
    """ Return a list of gpu names """
    cursor = conn.cursor()
    cursor.execute("SELECT chipset_name FROM chipset_specs")
    names = [name[0] for name in cursor.fetchall()]
    return names

def get_cpu_names(conn: sqlite3.Connection) -> list[str]:
    """ Return a list of gpu names """
    cursor = conn.cursor()
    cursor.execute("SELECT model_name FROM cpu_specs WHERE (release_date IS NOT NULL OR model_name LIKE '%Threadripper%') AND (model_name NOT LIKE '%Vega%')")
    names = [name[0] for name in cursor.fetchall()]
    return names

conn = sqlite3.connect("hardware.db")
CPU_NAMES = get_cpu_names(conn)
GPU_NAMES = get_gpu_names(conn, "2013-01-01")
CHIPSET_NAMES = get_chipset_names(conn)
MANUFACTURER_NAMES = get_manufacturer_names(conn)
conn.commit()
conn.close()

class SearchInfo:
    """
    A class to contain additional information for model names.\n
    To match the name/title of the product to a more general model.  
    Parameters:
        model_name (str): Full name of a model
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.name_patterns = model_name.split(" ") # patterns separated by spaces
        self.name_patterns_length = len(model_name.split(" ")) # numbers of patterns
        self.name_patterns_str_total_len = 0 # total string length of matched patterns
        self.similarity_score = 0 # calculated score to determine if two names are similar

    def reset_info(self):
        """ Set name_patterns_str_total_len and similarity_score to 0 """
        self.name_patterns_str_total_len = 0
        self.similarity_score = 0

def match_manufacturers(item_name: str, manufacturer_names: list[tuple[str, str]]):
    """ 
    Match the name/title of a product to a manufacturer 
    Parameters:
        item_name (str): The name/title of a product
        manufacturer_names (list[tuple[str, str]]): English and chinese names for each manufacturer
    """
    def match_en_name(en_name: str):
        for pattern in en_name.lower().split(" "):
            if len(pattern) <= 3 and not (re.findall(rf"[^0-9a-z]{pattern}[^0-9a-z]", item_name.lower()) + re.findall(rf"^{pattern}[^0-9a-z]", item_name.lower())):
                return False
            
            elif pattern not in item_name.lower():
                return False
        return True
    
    matched_cases = []
    for en_name, ch_name in manufacturer_names:
        if ch_name and ch_name in item_name:
            return en_name
        
        if match_en_name(en_name):
            matched_cases.append(en_name)
            
    return max(matched_cases, key=len) if matched_cases else None

def match_model(item_name: str, model_infos: list[SearchInfo]) -> list[str]|None:
    """
    Compare a name/title of a product to a list of models and return the most similar ones
    Parameters:
        item_name (str): Name/title of a product
        model_infos (list[SearchInfo]): models 
    """
    for model_info in model_infos:
        # specific for gpus
        if "D" in model_info.name_patterns:
            continue

        for pattern in model_info.name_patterns:
            pattern = pattern.lower()
            
            # specific for gpus
            if pattern == "ti" and re.findall(r"[a-z]+ti[a-z]+", item_name):
                continue

            if pattern in item_name:
                model_info.similarity_score += 1
                model_info.name_patterns_str_total_len += len(pattern)
            
            # increase similarity_score if a pattern contains only digits
            if pattern in item_name and len(pattern) >= 3 and pattern.isdigit() == True:
                model_info.similarity_score += 1
            
            # increase similarity_score if a pattern consists both en characters and numbers
            if pattern in item_name and len(pattern) >= 4 and re.findall(r"[a-z]+", pattern) and re.findall(r"[0-9]+", pattern):
                model_info.similarity_score += 1

    # Filter models with the highest score
    max_score = max([model_info.similarity_score for model_info in model_infos])
    matched_models = [model_info for model_info in model_infos if model_info.similarity_score == max_score]
    
    # Filter models with the least number of patterns
    min_pattern_length = min([model_info.name_patterns_length for model_info in matched_models])
    matched_models = [model for model in matched_models if model.name_patterns_length == min_pattern_length]
    
    # Filter models with the greatest number of matched str length
    max_patterns_str_length = max([model.name_patterns_str_total_len for model in matched_models])
    matched_models = [model for model in matched_models if model.name_patterns_str_total_len == max_patterns_str_length and max_patterns_str_length >= 4]

    if len(matched_models) >= 4:
        return None

    return matched_models[0].model_name if matched_models else None

def match_model_main(item_name: str, model_names: list[str]):
    """ Pre process for match_model """
    model_infos = [SearchInfo(name) for name in model_names]

    item_name = re.sub(r"\$\d+", "", item_name)
    
    for model in model_infos:
        model.reset_info()
    
    return match_model(item_name.lower(), model_infos)

def match_chipset(item_name: str, chipset_names: list[str]):
    """ Match the name/title of a motherboard to a chipset """
    match_cases = [name for name in chipset_names if name.lower() in item_name.lower()]
    return max(match_cases, key=len) if match_cases else None

class Product:
    """
    A class to parse additional details of hardware products\n
    Parameters:
        item_name (str): Name/title of the product
        price_str (str | None): String that contains the price of the product
        category (str): Name/title of the category
        subcategory (str): Name/title of the subcategory
        url (str | None): URL of the product if applicable 
        source (str): The retailer site of the product 
    
    Property:
    - Price in integers (extract from item_name or price_str)
    - Manufacturer of the product (ex. Asus)
    - Display name
    """
    def __init__(self, item_name: str, price_str: str|None, category: str, subcategory: str, url: str|None, source: str):
        self.name = item_name
        self.price_str = price_str
        self.category = category
        self.subcategory = subcategory
        self.source = source
        self.url = url
    
    @property
    def price_int(self) -> int:
        """ Return the price in int """
        if not self.price_str:
            matched_cases = re.findall(r"\$[^0-9]?(\d+)", self.name)
            return matched_cases[-1] if matched_cases else None
        return re.sub(r"\D", "", self.price_str)

    @property
    def manufacturer(self) -> str:
        return match_manufacturers(self.name, MANUFACTURER_NAMES)
    
    @property
    def display_name(self) -> str:
        if self.source == "Coolpc":
            return re.sub(r",[\S\s]*", "", self.name)
        else:
            return self.name

class RAM(Product):
    """
    A subclass of Product (for random access memories) to parse additional specs
    - Total capactiy in gigabytes (ex. 32)
    - Quantity/Number of memory modules (ex. 2)
    - DDR generation (ex. DDR5)
    - Frequency in mhz (ex. 6000)
    - Cas latency (ex. CL30)
    """
    def __init__(self, item_name, price_str, category, subcategory, url, source):
        super().__init__(item_name, price_str, category, subcategory, url, source)
        self.quantity: int|None = None

    @property
    def total_capacity_gb(self) -> int|None:
        for pattern, quantity in RAM_CAPACITY_DICT.items():
            match_cases = re.findall(pattern, self.name)
            if not match_cases:
                continue
            capactiy = int(match_cases[0]) * quantity
            if not validate_value_range(capactiy, 4, 512):
                continue
            self.quantity = quantity
            return capactiy
        return None
    
    @property
    def generation(self) -> str|None:
        matched_cases = re.findall(r"DD?R?(\d)", self.name)
        return f"DDR{matched_cases[0]}" if matched_cases else None
    
    @property
    def frequency(self) -> int|None:
        if not self.generation:
            return None
        matched_cases = re.findall(rf"DD?R?{self.generation[3]}[^0-9]*(\d+)", self.name)
        return int(matched_cases[0]) if matched_cases else None
        
    @property
    def cas_latency(self) -> int|None:
        matched_cases = re.findall(r"cl?(\d\d)", self.name.lower())
        return int(matched_cases[0]) if matched_cases else None
    
class SSD(Product):
    """
    A subclass of Product (for M.2 solid state drives) to parse additional specs
    - Capacity in gigabytes (ex. 1024)
    - PCIe generation (ex. 4)
    - NAND flash memory type (ex. TLC)
    - Marketed sequential read speed in megabytes per second
    - Marketed sequential write speed in megabytes per second
    """
    def __init__(self, item_name, price_str, category, subcategory, url, source):
        super().__init__(item_name, price_str, category, subcategory, url, source)

    @property
    def capacity_gb(self) -> int|None:
        for pattern, value in SSD_CAPACITY_DICT.items():
            matched_cases = re.findall(pattern, self.name)
            if not matched_cases:
                continue
            capacity = int(matched_cases[0]) * value
            if not validate_value_range(capacity, 64, 16384):
                continue
            return capacity
        return None

    @property
    def generation(self) -> int|None:
        matched_cases = re.findall(r"gen(\d)", self.name.lower()) + re.findall(r"pcie[\S\s]?(\d)", self.name.lower())
        return int(matched_cases[0]) if matched_cases else None

    @property
    def memory_type(self) -> str|None:
        for pattern in SSD_MEMORY_TYPES:
            if pattern.lower() in self.name.lower():
                return pattern
        return None
        
    @property
    def read_speed(self) -> int|None:
        matched_cases = re.findall(r"讀[^0-9]*(\d+)", self.name)
        return int(matched_cases[0]) if matched_cases else None
    
    @property
    def write_speed(self) -> int|None:
        matched_cases = re.findall(r"寫[^0-9]*(\d+)", self.name)
        return int(matched_cases[0]) if matched_cases else None

class PSU(Product):
    """
    A subclass of Product (for power supply units) to parse additional specs
    - Wattage in watts (ex. 750w)
    - Efficiency Ratings (ex. 80 Plus Gold)
    - ATX standard (ex. ATX 3.0)
    - Modularity (ex. Full)
    """
    def __init__(self, item_name, price_str, category, subcategory, url, source):
        super().__init__(item_name, price_str, category, subcategory, url, source)

    @property
    def wattage(self) -> int|None:        
        matched_cases = re.findall(r'(\d+)w', self.name.lower())
        return int(matched_cases[0]) if matched_cases else None
    
    @property
    def efficiency_rating(self) -> str|None:
        for pattern, rating in PSU_RATING_DICT.items():
            if pattern in self.name:
                return rating
        return None

    @property
    def atx_standard(self):
        for pattern, name in PSU_ATX_STANDARD_DICT.items():
            if re.findall(pattern, self.name.lower()):
                return name
        return None

    @property
    def modular(self):
        for pattern, name in PSU_MODULAR_DICT.items():
            if pattern in self.name:
                return name
        return None
    
class CPU(Product):
    """
    A subclass of Product (for central processing units) to parse additional specs
    - Model name (ex. Intel i7-12700)
    """
    def __init__(self, item_name, price_str, category, subcategory, url, source):
        super().__init__(item_name, price_str, category, subcategory, url, source)

    @property
    def model(self):
        return match_model_main(self.name, CPU_NAMES)
        
class GPU(Product):
    """
    A subclass of Product (for graphics processing units) to parse additional specs
    - Model name (ex. RTX 5070)
    - Length of the graphics card (ex. 32cm)
    """
    def __init__(self, item_name, price_str, category, subcategory, url, source):
        super().__init__(item_name, price_str, category, subcategory, url, source)
    
    @property
    def model(self):
        return match_model_main(self.name, GPU_NAMES)

    @property
    def card_length_cm(self):
        matched_cases = re.findall(r"(\d*\.?\d?)cm", self.name)
        return matched_cases[0] if matched_cases else None

class AIOCooler(Product):
    """
    A subclass of Product (for CPU AIOcoolers) to parse additional specs
    - Length of the longer side of the radiator (ex. 360mm)
    - Thickness of the radiator
    """
    def __init__(self, item_name, price_str, category, subcategory, url, source):
        super().__init__(item_name, price_str, category, subcategory, url, source)

    @property
    def length_mm(self):
        for length in AIOCOOLER_LENGTHS:
            if str(length) in self.name:
                return length
        return None
    
    @property
    def thickness_cm(self):
        matched_case = re.findall(rf"厚[^0-9]?(\d+\.?\d*)", self.name)
        return float(matched_case[0]) if matched_case else None
    
class AirCooler(Product):
    """
    A subclass of Product (for CPU aircoolers) to parse additional specs
    - Height of the CPU cooler
    - Number of heat sink(s)
    - Number of heat pipes 
    """
    def __init__(self, item_name, price_str, category, subcategory, url, source):
        super().__init__(item_name, price_str, category, subcategory, url, source)

    @property
    def height_cm(self) -> float|None:
        matched_cases = re.findall(r"高度?(\d+\.?\d*)", self.name)
        return float(matched_cases[0]) if matched_cases else None
    
    @property
    def heat_sink_count(self) -> int|None:
        if "雙塔" in self.name:
            return 2
        return 1
    
    @property
    def heat_pipe_count(self) -> int|None:
        matched_cases = re.findall(r"(\d)導管", self.name)
        return int(matched_cases[0]) if matched_cases else None
    
class Motherboard(Product):
    """
    A subclass of Product (for motherboards) to parse additional specs
    - Chipset (ex. B660)
    - Form factor (ex. ATX)
    - Reverse connectors
    """
    def __init__(self, item_name, price_str, category, subcategory, url, source):
        super().__init__(item_name, price_str, category, subcategory, url, source)
    
    @property
    def chipset(self):
        return match_chipset(self.name, CHIPSET_NAMES)
    
    @property
    def form_factor(self) -> str|None:
        for pattern, name in MB_FORM_FACTOR_DICT.items():
            if pattern in self.name.lower():
                return name
        return None
    
    @property
    def reverse_connectors(self) -> bool|None:
        return True if "背插" in self.name else False
    
class Case(Product):
    """
    A subclass of Product (for cases) to parse additional specs
    - Maximum compatible height for CPU cooler
    - Maximum compatible length for GPU
    - Compatible motherboard form factor (ex. E-ATX)
    """
    def __init__(self, item_name, price_str, category, subcategory, url, source):
        super().__init__(item_name, price_str, category, subcategory, url, source)

    @property
    def cpu_height_cm(self) -> float|None:
        for pattern, value in CASE_CPU_HEIGHT_DICT.items():
            matched_cases = re.findall(pattern, self.name.lower())
            if not matched_cases:
                continue
            return float(matched_cases[0]) * value
        return None
    
    @property
    def gpu_length_cm(self) -> float|None:
        for pattern, value in CASE_GPU_LENGTH_DICT.items():
            matched_cases = re.findall(pattern, self.name.lower())
            if not matched_cases:
                continue
            return float(matched_cases[0]) * value
        return None

    @property
    def motherboard_form_factor(self) -> str|None:
        for pattern, name in MB_FORM_FACTOR_DICT.items():
            if pattern in self.name.lower():
                return name
        return None
    
if __name__ == "__main__":

    # print(RAM.find_capacity(r"威剛 單條16GB D5-4800/CL40 (AD5U480016G-S) 支援 XMP, $1699 ◆ ★ 熱賣"))

    # st = re.findall(rf"\d*G", r"金士頓 NV3 500G/Gen4 PCIe 4.0/讀5000/寫3000【五年保】~整組組裝價~, $1200 ◆ ★ None")

    # print(AirCooler.find_height(r"Montech Metal DT24 Premium 6導管/高15.8/雙塔雙扇/全黑化/ARGB鋁質上蓋【WXHZ】, $1890 ◆ ★"))
    # a = RAM.find_capacity
    # d = SSD("MSI 微星 M470PRO 2TB/Gen4/讀6000/寫5000/QLC顆粒, $9890 ◆ ★", None, "", "", "", "")
    # print(d.capacity_gb)

    r = RAM("美光 Micron Crucial PRO 超頻 64GB(雙通32G*2) D5 6000/CL40 黑色散熱片 限組裝, $21999 ◆ ★", None, "", "", "", "")
    print(r.frequency)
    print(r.total_capacity_gb)

    s = SSD("WD 黑標 SN850X 1TB/含散熱片/Gen4 PCIe 4.0/讀7300/寫6300/TLC【五年保】, $4980 ◆ ★", None, "", "", "", "")
    print(s.capacity_gb)
    print(s.memory_type)

    print(match_manufacturers("LG Gram Pro Ultra 5-226V/16G/1T/16吋 灰 16Z90TS-G.AS59C2 超高更新率144Hz, $36900 ◆ ★ 熱賣", MANUFACTURER_NAMES))
    print(re.findall(r"^lg[^0-9a-z]", "LG Gram Pro Ultra 5-226V/16G/1T/16吋 灰 16Z90TS-G.AS59C2 超高更新率144Hz, $36900 ◆ ★ 熱賣".lower()))

    p = Product("WD 黑標 SN850X 1TB/含散熱片/Gen4 PCIe 4.0/讀7300/寫6300/TLC【五年保】, $4980 ◆ ★", None, "", "", "", "Coolpc")
    print(p.display_name)

    # ram = RAM("宏碁 Acer Predator Hermes RGB 32GB(雙通16GBx2)DDR5 6400銀/CL32【AI 雙模】, $7290↗$7990 ◆ ★", None, "", "", "", "")
    # print(ram.total_capacity_gb)
    # print(ram.quantity)
    # print(ram.generation)
    # print(ram.frequency)
    # print(ram.cas_latency)

    # conn = sqlite3.connect("hardware.db")
    
    gpu = GPU("【新春強檔】技嘉 RTX 5060 WINDFORCE OC 8G+雷蛇Razer Orochi V2 八岐大蛇靈刃V2 電競滑鼠 黑【RAZER電競滑鼠只要400元 !】 1      ", "$1500", "", "", "", "")
    print(gpu.model)

    c = Case("曜越 View 290 TG ARGB 白 顯卡長45/U高18/全景曲面玻璃/支援背插/ATX 原價$2690！, $2390 ◆ ★", "$1500", "", "", "", "")
    print(c.cpu_height_cm)