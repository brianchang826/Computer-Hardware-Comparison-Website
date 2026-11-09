import sqlite3
from internal_assessment.specs_parser import CPU, GPU, RAM, SSD, PSU, Motherboard, AIOCooler, AirCooler, Case, Product
from crawler_pchome import return_data_selected_categories, return_data_selected_subcategories
from additional_specs import CREATE_CHIPSET_SPECS, CREATE_CPU_SPECS, CREATE_MANUFACTURERS, insert_chipset_specs, insert_cpu_specs, insert_gpu_specs, insert_manufacturers_csv
from datetime import datetime

SOURCE_DICT = {"Coolpc": (1, "https://www.coolpc.com.tw/evaluate.php"), "Sinya": (2, "https://www.sinya.com.tw/"), "Pchome": (3, "https://24h.pchome.com.tw/")}

CREATE_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    product_id      INTEGER     PRIMARY KEY AUTOINCREMENT,
    name            TEXT        NOT NULL,
    category        TEXT, 
    subcategory     TEXT, 
    price           INTEGER     NOT NULL,
    manufacturer    TEXT,        
    url             TEXT, 
    source_id       INTEGER     NOT NULL REFERENCES sources(source_id),
    version_id      INTEGER     NOT NULL REFERENCES versions(version_id),      
    CONSTRAINT unique_url_version UNIQUE (url, version_id)
)
"""

PRODUCT_P_KEY_REF = "product_id INTEGER PRIMARY KEY REFERENCES Products(product_id)"

INSERT_PRODUCT = "INSERT INTO products (name, category, subcategory, price, manufacturer, url, source_id, version_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

CREATE_VERSIONS = """
CREATE TABLE IF NOT EXISTS versions (
    version_id  INTEGER     PRIMARY KEY AUTOINCREMENT,
    created_at  TIMESTAMP   NOT NULL
)
"""

CREATE_SOURCES = """
CREATE TABLE IF NOT EXISTS sources (
    source_id   INTEGER     PRIMARY KEY AUTOINCREMENT, 
    source_name TEXT        NOT NULL, 
    source_url  TEXT        NOT NULL
)
"""

CREATE_RAMS = f"""
CREATE TABLE IF NOT EXISTS rams (
    {PRODUCT_P_KEY_REF},
    total_capacity_gb   INTEGER,
    quantity            INTEGER,
    generation          TEXT,
    frequency           INTEGER,
    cas_latency         INTEGER
)
"""

CREATE_SSDS = f"""
CREATE TABLE IF NOT EXISTS ssds (
    {PRODUCT_P_KEY_REF},
    capacity_gb     INTEGER,
    generation      INTEGER,
    memory_type     TEXT,
    read_speed      INTEGER,
    write_speed     INTEGER
)
"""

CREATE_PSUS = f"""
CREATE TABLE IF NOT EXISTS psus (
    {PRODUCT_P_KEY_REF},
    wattage             INTEGER,
    efficiency_rating   TEXT,
    atx_standard        TEXT,
    modular             TEXT
)
"""

CREATE_CPUS = f"""
CREATE TABLE IF NOT EXISTS cpus (
    {PRODUCT_P_KEY_REF},
    model TEXT REFERENCES cpu_specs(model_name)
)
"""

CREATE_GPUS = f"""
CREATE TABLE IF NOT EXISTS gpus (
    {PRODUCT_P_KEY_REF},
    model       TEXT REFERENCES gpu_specs(name),
    card_length REAL
)
"""

CREATE_AIO_COOLERS = f"""
CREATE TABLE IF NOT EXISTS aio_coolers (
    {PRODUCT_P_KEY_REF},
    length_mm   REAL,
    thickness   REAL
)
"""

CREATE_AIR_COOLERS = f"""
CREATE TABLE IF NOT EXISTS air_coolers (
    {PRODUCT_P_KEY_REF},
    height_cm       REAL,
    heat_sink_count INTEGER,
    heat_pipe_count INTEGER
)
"""

CREATE_MOTHERBOARDS = f"""
CREATE TABLE IF NOT EXISTS motherboards (
    {PRODUCT_P_KEY_REF},
    chipset             TEXT REFERENCES chipset_specs(chipset_name),
    form_factor         TEXT,
    reverse_connectors  BOOLEAN
)
"""

CREATE_CASES = f"""
CREATE TABLE IF NOT EXISTS cases (
    {PRODUCT_P_KEY_REF},
    cpu_height_cm REAL,
    gpu_length_cm REAL,
    motherboard_form_factor TEXT
)
"""

INSERT_RAMS = "INSERT INTO rams (product_id, total_capacity_gb, quantity, generation, frequency, cas_latency) VALUES (?, ?, ?, ?, ?, ?)"
INSERT_SSDS = "INSERT INTO ssds (product_id, capacity_gb, generation, memory_type, read_speed, write_speed) VALUES (?, ?, ?, ?, ?, ?)"
INSERT_PSUS = "INSERT INTO psus (product_id, wattage, efficiency_rating, atx_standard, modular) VALUES (?, ?, ?, ?, ?)"
INSERT_CPUS = "INSERT INTO cpus (product_id, model) VALUES (?, ?)"
INSERT_GPUS = "INSERT INTO gpus (product_id, model, card_length) VALUES (?, ?, ?)"
INSERT_AIO_COOLERS = "INSERT INTO aio_coolers (product_id, length_mm, thickness) VALUES (?, ?, ?)"
INSERT_AIR_COOLERS = "INSERT INTO air_coolers (product_id, height_cm, heat_sink_count, heat_pipe_count) VALUES (?, ?, ?, ?)"
INSERT_MOTHERBOARDS = "INSERT INTO motherboards (product_id, chipset, form_factor, reverse_connectors) VALUES (?, ?, ?, ?)"
INSERT_CASES = "INSERT INTO cases (product_id, cpu_height_cm, gpu_length_cm, motherboard_form_factor) VALUES (?, ?, ?, ?)"

INSERT_QUERIES_DICT = {
    CPU: INSERT_CPUS,
    GPU: INSERT_GPUS,
    RAM: INSERT_RAMS,
    SSD: INSERT_SSDS,
    PSU: INSERT_PSUS,
    Motherboard: INSERT_MOTHERBOARDS,
    AIOCooler: INSERT_AIO_COOLERS,
    AirCooler: INSERT_AIR_COOLERS,
    Case: INSERT_CASES
}

INSERT_SOURCE = "INSERT INTO sources (source_name, source_url) VALUES (?, ?)"

INSERT_VERSION = "INSERT INTO versions (created_at) VALUES (?)"

def get_values_from_properties(product_id: int, product_instance):
    """ Convert a product specification class instance into a tuple """
    match product_instance:
        case RAM():
            return (product_id, product_instance.total_capacity_gb, product_instance.quantity, product_instance.generation, product_instance.frequency, product_instance.cas_latency)
        case SSD():
            return (product_id, product_instance.capacity_gb, product_instance.generation, product_instance.memory_type, product_instance.read_speed, product_instance.write_speed)
        case PSU():
            return (product_id, product_instance.wattage, product_instance.efficiency_rating, product_instance.atx_standard, product_instance.modular)
        case CPU():
            return (product_id, product_instance.model)
        case GPU():
            return (product_id, product_instance.model, product_instance.card_length_cm)
        case AIOCooler():
            return (product_id, product_instance.length_mm, product_instance.thickness_cm)
        case AirCooler():
            return (product_id, product_instance.height_cm, product_instance.heat_sink_count, product_instance.heat_pipe_count)
        case Motherboard():
            return (product_id, product_instance.chipset, product_instance.form_factor, product_instance.reverse_connectors)
        case Case():
            return (product_id, product_instance.cpu_height_cm, product_instance.gpu_length_cm, product_instance.motherboard_form_factor)
        case _:
            return None

def insert_data(conn: sqlite3.Connection, dataset: list[Product], version_id: int):
    """ Insert a dataset and its extracted info into the database """
    
    cursor = conn.cursor()

    for product in dataset:
        
        cursor.execute(INSERT_PRODUCT, (product.name, product.category, product.subcategory, product.price_int, product.manufacturer, product.url, SOURCE_DICT[product.source][0], version_id))
        product_id = cursor.lastrowid
        query = INSERT_QUERIES_DICT.get(type(product))
        value = get_values_from_properties(product_id, product)
        
        if not (query and value):
            continue
        
        cursor.execute(query, value)
        
def remove_repeating_urls(dataset: list[Product]):
    urls = []
    output = []
    for product in dataset:
        if product.url not in urls:
            output.append(product)
            urls.append(product.url)
    return output

def database_full_setup(filename: str):
    """
    Set up the entire database
    """
    conn = sqlite3.connect(filename)
    
    cursor = conn.cursor()

    cursor.execute(CREATE_PRODUCTS)
    cursor.execute(CREATE_SOURCES)
    cursor.execute(CREATE_VERSIONS)
    
    cursor.execute(CREATE_RAMS)
    cursor.execute(CREATE_SSDS)
    cursor.execute(CREATE_PSUS)
    cursor.execute(CREATE_CPUS)
    cursor.execute(CREATE_GPUS)
    cursor.execute(CREATE_AIO_COOLERS)
    cursor.execute(CREATE_AIR_COOLERS)
    cursor.execute(CREATE_MOTHERBOARDS)
    cursor.execute(CREATE_CASES)

    cursor.execute(CREATE_CHIPSET_SPECS)
    cursor.execute(CREATE_MANUFACTURERS)
    cursor.execute(CREATE_CPU_SPECS)
    conn.commit()

    insert_chipset_specs(conn)
    insert_cpu_specs(conn)
    insert_gpu_specs(conn)
    insert_manufacturers_csv(conn)

    for key, value in SOURCE_DICT.items():
        cursor.execute(INSERT_SOURCE, (key, value[1]))
    
    conn.commit()
    cursor.close()
    conn.close()