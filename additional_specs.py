import sqlite3
import pandas
from dbgpu import GPUDatabase
from html_parse import replace_whitespaces, get_chipset_specs, get_hardware_manufacturers, filter_manufacturers
from datetime import datetime
import re
# Intel cpu specs https://github.com/toUpperCase78/intel-processors/tree/master
# AMD cpu specs https://www.amd.com/en/products/specifications/processors.html

CREATE_CHIPSET_SPECS = """
CREATE TABLE chipset_specs (
    chipset_name            TEXT PRIMARY KEY NOT NULL,
    release_date            DATE,
    usb_v2_0_ports          INTEGER,
    usb_v3_2_gen1x1_ports   INTEGER,
    usb_v3_2_gen2x1_ports   INTEGER,
    usb_v3_2_gen2x2_ports   INTEGER,
    sata_iii_ports          INTEGER,
    pcie_graphics           TEXT,
    pcie_nvme               TEXT,
    socket                  TEXT
)
"""

INSERT_CHIPSET_SPECS = """
INSERT INTO chipset_specs (
    chipset_name,
    release_date,
    usb_v2_0_ports,
    usb_v3_2_gen1x1_ports,
    usb_v3_2_gen2x1_ports,
    usb_v3_2_gen2x2_ports,
    sata_iii_ports,
    pcie_graphics,
    pcie_nvme,
    socket
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

CREATE_CPU_SPECS = """
CREATE TABLE IF NOT EXISTS cpu_specs (
    model_name          TEXT PRIMARY KEY NOT NULL,
    release_date        DATE,
    code_name           TEXT,
    core_counts         INTEGER,
    thread_counts       INTEGER,
    lithography         TEXT,
    max_frequency_ghz   REAL,
    base_frequency_ghz  REAL,
    tdp_w               REAL,
    l3_cache_mb         REAL,
    supported_memory    TEXT,
    integrated_graphics TEXT
)
"""

INSERT_CPU_SPECS = """
INSERT INTO cpu_specs (
    model_name,
    release_date,
    code_name,
    core_counts,
    thread_counts,
    lithography,
    max_frequency_ghz,
    base_frequency_ghz,
    tdp_w,
    l3_cache_mb,
    supported_memory,
    integrated_graphics
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

CREATE_MANUFACTURERS = """
CREATE TABLE IF NOT EXISTS manufacturers (
    name TEXT PRIMARY KEY, 
    chinese_name TEXT
)
"""

INSERT_MANUFACTURER = "INSERT INTO manufacturers VALUES (?, ?)"

def format_date(date_str):    
    try:
        return datetime.strptime(date_str, "%m-%d-%y").date()
    except:
        pass

    try:
        return datetime.strptime(date_str, "%m/%d/%Y").date()
    except:
        pass
    
    try:
        q = int(re.findall(r"Q(\d)", date_str)[0])
        year = 2000 + int(date_str[-2:])
        month = (q - 1) * 3 + 1
        return datetime(year, month, 1)
    except:
        return None
    
def get_int(x: str):
    if not x:
        return None
    matched_cases = re.findall(r"(\d+)", str(x))
    return int(matched_cases[0]) if matched_cases else None
    
def get_float(x: str):
    try:
        matched_cases = re.findall(r"\d+\.?\d?", x) 
        return float(matched_cases[0]) if matched_cases else None
    except:
        return None

def insert_gpu_specs(conn: sqlite3.Connection):
    gpu_db = GPUDatabase.default()
    gpu_db.dataframe.to_sql("gpu_specs", conn, index=False)

def insert_cpu_specs(conn: sqlite3.Connection):
    cursor = conn.cursor()

    intel_cpus = pandas.read_csv("Intel_CPU_Specs_Revised.csv")

    intel_cpus = intel_cpus[~intel_cpus["Status"].str.contains("Discontinued")].copy()
    selected_intel_cpus = intel_cpus[["Product", "Release_Date", "Code_Name", "Cores", "Threads", "Lithography(nm)", "Max._Turbo_Freq.(GHz)", "Base_Freq.(GHz)", "TDP(W)", "Cache(MB)", "Memory_Types", "Integrated_Graphics"]].copy()
    selected_intel_cpus["Release_Date"] = selected_intel_cpus["Release_Date"].apply(format_date).astype(str)
    selected_intel_cpus["Threads"] = selected_intel_cpus["Threads"].astype(int)

    amd_cpus = pandas.read_csv("AMD Processor Specifications.csv")

    amd_cpus = amd_cpus[~amd_cpus["Form Factor"].str.contains("Laptop", na=False)]
    selected_amd_cpus = amd_cpus[["Name", "Launch Date", "Series", "# of CPU Cores", "# of Threads", "Processor Technology for CPU Cores", "Max. Boost Clock", "Base Clock", "Default TDP", "L3 Cache", "System Memory Type", "Graphics Model"]].copy()
    selected_amd_cpus["Name"] = selected_amd_cpus["Name"].str.replace("AMD", "")
    selected_amd_cpus["Name"] = selected_amd_cpus["Name"].str.replace("™", "")
    selected_amd_cpus["Name"] = selected_amd_cpus["Name"].str.strip()
    selected_amd_cpus["Launch Date"] = selected_amd_cpus["Launch Date"].apply(format_date)
    selected_amd_cpus["Max. Boost Clock"] = selected_amd_cpus["Max. Boost Clock"].apply(get_float)
    selected_amd_cpus["Base Clock"] = selected_amd_cpus["Base Clock"].apply(get_float)
    selected_amd_cpus["Default TDP"] = selected_amd_cpus["Default TDP"].apply(get_float)
    selected_amd_cpus["L3 Cache"] = selected_amd_cpus["L3 Cache"].apply(get_float)
    
    for value in selected_intel_cpus.itertuples(index=False, name=None):
        cursor.execute(INSERT_CPU_SPECS, value)

    for value in selected_amd_cpus.itertuples(index=False, name=None):
        cursor.execute(INSERT_CPU_SPECS, value)

def insert_chipset_specs(conn: sqlite3.Connection):
    
    cursor = conn.cursor()

    intel_chipsets = pandas.read_csv("Intel_Chipset_Specs_Revised.csv")
    selected_intel_chipsets = intel_chipsets[["Chipset", "Release Date", "USB ports v2.0", "USB ports v3.2 Gen 1x1", "USB ports v3.2 Gen 2x1", "USB ports v3.2 Gen 2x2", "SATA 6 Gbit/s", "PCIe Graphics", "PCIe NVMe", "Socket"]].copy()
    
    selected_intel_chipsets["Release Date"] = selected_intel_chipsets["Release Date"].apply(format_date).astype(str)
    selected_intel_chipsets["USB ports v2.0"] = selected_intel_chipsets["USB ports v2.0"].apply(get_int)
    selected_intel_chipsets["USB ports v3.2 Gen 1x1"] = selected_intel_chipsets["USB ports v3.2 Gen 1x1"].apply(get_int)
    selected_intel_chipsets["USB ports v3.2 Gen 2x1"] = selected_intel_chipsets["USB ports v3.2 Gen 2x1"].apply(get_int)
    selected_intel_chipsets["USB ports v3.2 Gen 2x2"] = selected_intel_chipsets["USB ports v3.2 Gen 2x2"].apply(get_int)
    
    for value in selected_intel_chipsets.itertuples(index=False, name=None):
        cursor.execute(INSERT_CHIPSET_SPECS, value)

    amd_chipsets = pandas.read_csv("AMD_Chipset_Specs_Revised.csv")
    selected_amd_chipsets = amd_chipsets[["Chipset", "Release date", "USB support USB 2.0", "USB support USB 3.2 Gen 1x1", "USB support USB 3.2 Gen 2x1", "USB support USB 3.2 Gen 2x2", "Storage features SATA ports", "PCIe support Graphics", "PCIe support NVMe", "Socket"]].copy()
    
    selected_amd_chipsets["Release date"] = selected_amd_chipsets["Release date"].apply(format_date).astype(str)
    selected_amd_chipsets["Storage features SATA ports"] = selected_amd_chipsets["Storage features SATA ports"].apply(get_int)

    for value in selected_amd_chipsets.itertuples(index=False, name=None):
        cursor.execute(INSERT_CHIPSET_SPECS, value)

def insert_manufacturers_csv(conn: sqlite3.Connection):
    cursor = conn.cursor()
    manufacturers = pandas.read_csv("hardware_manufacturers_revised.csv")
    manufacturers["EnglishName"] = manufacturers["EnglishName"].str.strip()
    manufacturers["ChineseName"] = manufacturers["ChineseName"].str.strip()

    for value in manufacturers.itertuples(index=False, name=None):
        cursor.execute(INSERT_MANUFACTURER, value)

def insert_manufacturers(conn: sqlite3.Connection, new_manufacturer_names: list[tuple[str, str|None]]):
    cursor = conn.cursor()
    for value in new_manufacturer_names:
        cursor.execute(INSERT_MANUFACTURER, value)

def merge_intel_cpu_csv():
    core_ultra_cpus = pandas.read_csv("intel_core_processors_v1_8.csv")
    core_cpus = pandas.read_csv("Intel_Core_Ultra_Processors_v1_9.csv")
    output = pandas.concat([core_ultra_cpus, core_cpus])
    output = replace_whitespaces(output)
    output.to_csv("Intel_CPU_Specs.csv", index=False)

def get_required_specs():
    get_chipset_specs()
    # download csv from https://github.com/toUpperCase78/intel-processors/tree/master
    # download csv from https://www.amd.com/en/products/specifications/processors.html
    merge_intel_cpu_csv()
    
    manufacturers = filter_manufacturers(get_hardware_manufacturers())
    pandas.Series(manufacturers).to_csv("hardware_manufacturers.csv", index=False)