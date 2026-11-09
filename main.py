from fastapi import FastAPI, HTTPException
from query import SQLQuery
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import sqlite3
import traceback

KNOWN_PARAMETERS = [
    "keywords",
    "max_price",
    "min_price",
    "source_names",
    "manufacturers",
    "price_sort_method",
    "hardware_type"
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchParameters(BaseModel):
    keywords: Optional[str] = None
    max_price: Optional[int] = None
    min_price: Optional[int] = None
    source_names: Optional[List[str]] = None
    manufacturers: Optional[List[str]] = None
    price_sort_method: Optional[str] = None
    hardware_type: Optional[str] = None
    spec_filters: Optional[List[Dict[str, Any]]] = None

def run_select_query(conn: sqlite3.Connection, query: str):

    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]

    return result

def get_most_recent_version(conn: sqlite3.Connection) -> tuple[int, str]:
    cursor = conn.cursor()
    cursor.execute("SELECT version_id, created_at FROM versions ORDER BY created_at DESC LIMIT 1")
    result = cursor.fetchone()
    return result

def add_multiple_conditions(query: str, column_name: str, conditions: list[str]|str) -> str:
    query += f"AND ("
    for idx, condition in enumerate(conditions):
        if idx == 0:
            query += f"{column_name} = '{condition}' "
        else:
            query += f"OR {column_name} = '{condition}' "
    query += f") "
    return query

def add_spec_constraints(query: str, spec_filters: list[dict]):
    for spec_filter in spec_filters:
        constraint_name = spec_filter.get("constraint_name")
        
        if not constraint_name:
            continue

        match spec_filter["type"]:
            case "match":
                match_value = spec_filter.get("match_value")
                query += f"AND {constraint_name} = '{match_value}' " 
            case "range":
                max_value = spec_filter.get("max_value")
                if max_value:
                    query += f"AND {constraint_name} <= '{spec_filter["max_value"]}' "
                min_value = spec_filter.get("min_value")
                if min_value:
                    query += f"AND {constraint_name} >= '{spec_filter["min_value"]}' "
    return query

@app.post("/search")
async def search(parameters: SearchParameters):
    try:
        
        conn = sqlite3.connect("hardware.db")

        # version info
        VERSION_ID, CREATED_TIME = get_most_recent_version(conn)

        # base select statement
        search_query = "SELECT name, category, subcategory, price, manufacturer, url, source_name FROM products "
        get_manufacturers_query = "SELECT manufacturer, COUNT(*) AS count FROM products "
        get_sources_query = "SELECT sources.source_name, COUNT(*) AS count FROM products "

        # basic inner join 
        clause = """
            INNER JOIN sources ON products.source_id = sources.source_id
            INNER JOIN versions ON products.version_id = versions.version_id
        """
        search_query += clause
        get_manufacturers_query += clause
        get_sources_query += clause

        # more inner joins (hardware type)
        hardware_type = parameters.hardware_type
        if hardware_type:
            search_query = SQLQuery(hardware_type).complete_query
            get_manufacturers_query += SQLQuery(hardware_type).inner_join_clause
            get_sources_query += SQLQuery(hardware_type).inner_join_clause

        """ ------- WHERE CONSTRAINTS -------- """

        # versions
        version_constraint = f"WHERE products.version_id = {VERSION_ID} "
        search_query += version_constraint
        get_manufacturers_query += version_constraint
        get_sources_query += version_constraint
        
        # keywords
        keywords = parameters.keywords
        if keywords:
            for keyword in keywords.split(" "):
                condition = f"AND (LOWER(products.name) LIKE '%{keyword.lower()}%' OR LOWER(products.category) LIKE '%{keywords}%' OR LOWER(products.subcategory) LIKE '%{keywords}%') "
                search_query += condition
                get_manufacturers_query += condition
                get_sources_query += condition

        # maximum price
        max_price = parameters.max_price
        if max_price:
            condition = f"AND price <= {max_price} "
            search_query += condition
            get_manufacturers_query += condition
            get_sources_query += condition

        # minimum price
        min_price = parameters.min_price
        if min_price:
            condition = f"AND price >= {min_price} "
            search_query += condition
            get_manufacturers_query += condition
            get_sources_query += condition

        # sources (ex. Pchome)
        source_names = parameters.source_names
        if source_names:
            search_query = add_multiple_conditions(search_query, "sources.source_name", source_names)
            get_manufacturers_query = add_multiple_conditions(get_manufacturers_query, "sources.source_name", source_names)
        
        # manufacturers (ex. Asus)
        manufacturers = parameters.manufacturers
        if manufacturers:
            search_query = add_multiple_conditions(search_query, "manufacturer", manufacturers)
            get_sources_query = add_multiple_conditions(get_sources_query, "manufacturer", manufacturers)

        # specifications filters
        spec_filters = parameters.spec_filters
        if spec_filters:
            search_query = add_spec_constraints(search_query, spec_filters)
            get_manufacturers_query = add_spec_constraints(get_manufacturers_query, spec_filters)
            get_sources_query = add_spec_constraints(get_sources_query, spec_filters)

        """ ------------------------------- """ 
        
        # results display sorting (by price)
        price_sort_method = parameters.price_sort_method
        if price_sort_method != "off":
            search_query += f"ORDER BY price {price_sort_method} "
                
        # maximum number of displayed results
        search_query += "LIMIT 100"
        
        get_manufacturers_query += f"""
            GROUP BY manufacturer
            ORDER BY count DESC
            LIMIT 8
        """

        get_sources_query += f"""
            GROUP BY sources.source_name
            ORDER BY count DESC
            LIMIT 5
        """

        # query results
        conn.row_factory = sqlite3.Row
        search_results = run_select_query(conn, search_query)
        matched_manufacturers = run_select_query(conn, get_manufacturers_query)
        matched_sources = run_select_query(conn, get_sources_query)
        conn.close()

        return {"search_results": search_results, "manufacturers": matched_manufacturers, "sources": matched_sources, "created_time": CREATED_TIME}
    
    except Exception as e:
        traceback_str = traceback.format_exc()
        raise HTTPException(status_code=400, detail=[{"msg": f"{traceback_str+str(e)}"}])

@app.get("/get_constraint_values") 
async def get_constraint_values(hardware_type: str, column_name: str):
    try:
        
        conn = sqlite3.connect("hardware.db")

        # version info
        VERSION_ID = get_most_recent_version(conn)[0]
        
        # select statement
        query = f"SELECT {column_name}, COUNT(*) AS count FROM products "

        # inner join clause
        clause = """
            INNER JOIN sources ON products.source_id = sources.source_id
            INNER JOIN versions ON products.version_id = versions.version_id
        """
        query += clause
        query += SQLQuery(hardware_type).inner_join_clause

        # where constraint
        query += f"WHERE products.version_id = {VERSION_ID} "

        # order
        query += f"""
            GROUP BY {column_name}
            ORDER BY count DESC
            LIMIT 10
        """

        conn.row_factory = sqlite3.Row
        results = run_select_query(conn, query)
        return results
    
    except Exception as e:
        traceback_str = traceback.format_exc()
        raise HTTPException(status_code=400, detail=[{"msg": f"{traceback_str+str(e)}"}])
        