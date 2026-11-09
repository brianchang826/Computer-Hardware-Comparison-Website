import sqlite3

SELECT_STATEMENT_CPUS = "SELECT name, category, subcategory, price, manufacturer, url, sources.source_name, cpu_specs.* FROM products "

INNER_JOIN_CLAUSE_CPUS = """
    INNER JOIN cpus ON products.product_id = cpus.product_id
    INNER JOIN cpu_specs ON cpus.model = cpu_specs.model_name
"""

SELECT_STATEMENT_GPUS = """
SELECT name, category, subcategory, price, manufacturer, url, sources.source_name, gpus.card_length, 
    gpu_specs.gpu_manufacturer,
    gpu_specs.gpu_name,
    gpu_specs.core_name, 
    gpu_specs.generation, 
    gpu_specs.boost_clock_mhz, 
    gpu_specs.release_date, 
    gpu_specs.bus_interface, 
    gpu_specs.memory_size_gb, 
    gpu_specs.memory_bus_bits, 
    gpu_specs.memory_type, 
    gpu_specs.shading_units, 
    gpu_specs.thermal_design_power_w
    FROM products
"""

INNER_JOIN_CLAUSE_GPUS = """
    INNER JOIN gpus ON products.product_id = gpus.product_id
    INNER JOIN gpu_specs ON gpus.model = gpu_specs.gpu_name
"""

SELECT_STATEMENT_MBS = """
    SELECT name, category, subcategory, price, manufacturer, url, 
    sources.source_name, motherboards.chipset, motherboards.form_factor, motherboards.reverse_connectors, chipset_specs.* FROM products
"""

INNER_JOIN_CLAUSE_MBS = """
    INNER JOIN motherboards ON products.product_id = motherboards.product_id
    INNER JOIN chipset_specs ON motherboards.chipset = chipset_specs.chipset_name
"""

class SQLQuery:
    def __init__(self, hardware_type: str):
        self._hardware_type = hardware_type

    @property
    def select_statement(self):
        match self._hardware_type:
            case "cpus":
                return SELECT_STATEMENT_CPUS
            case "gpus":
                return SELECT_STATEMENT_GPUS
            case "motherboards":
                return SELECT_STATEMENT_MBS
            case "psus" | "cases" | "air_coolers" | "aio_coolers" | "ssds" | "rams":
                return f"SELECT name, category, subcategory, price, manufacturer, url, sources.source_name, {self._hardware_type}.* FROM products "
            case _:
                return None
    @property
    def inner_join_clause(self):
        match self._hardware_type:
            case "cpus":
                return INNER_JOIN_CLAUSE_CPUS
            case "gpus":
                return INNER_JOIN_CLAUSE_GPUS
            case "motherboards":
                return INNER_JOIN_CLAUSE_MBS
            case "psus" | "cases" | "air_coolers" | "aio_coolers" | "ssds" | "rams":
                return f"INNER JOIN {self._hardware_type} ON products.product_id = {self._hardware_type}.product_id "
            case _:
                return None
            
    @property
    def complete_query(self):
        return self.select_statement + self.inner_join_clause + "INNER JOIN sources ON products.source_id = sources.source_id "

def run_select_query(query: str):
    
    conn = sqlite3.connect("hardware.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(query)
    rows = cursor.fetchall()

    result = [dict(row) for row in rows]

    conn.close()
    return result

