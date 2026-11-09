from datetime import datetime
from storage import INSERT_VERSION, insert_data, remove_repeating_urls
from crawler_coolpc_sinya import return_data_coolpc, return_data_sinya
from crawler_pchome import return_data_selected_categories, return_data_selected_subcategories
from utils import is_url_allowed
import sqlite3

def main():
    conn = sqlite3.connect("hardware.db")
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(current_time)

    cursor.execute(INSERT_VERSION, (current_time,))
    version_id = cursor.lastrowid
    conn.commit()
    
    if is_url_allowed("https://coolpc.com.tw/", "https://coolpc.com.tw/evaluate.php"):
        coolpc_dataset = return_data_coolpc(return_all_category=True)
        print(f"Inserting the dataset ({len(coolpc_dataset)} items) into the database...")
        insert_data(conn, coolpc_dataset, version_id)
        conn.commit()
    
    if is_url_allowed("https://www.sinya.com.tw/", "https://www.sinya.com.tw/"):
        sinya_dataset = return_data_sinya(crawl_all_category=True)
        print(f"Inserting the dataset ({len(sinya_dataset)} items) into the database...")
        insert_data(conn, sinya_dataset, version_id)
        conn.commit()
    
    if is_url_allowed("https://24h.pchome.com.tw/", "https://24h.pchome.com.tw/"):
        pchome_dataset = return_data_selected_subcategories() + return_data_selected_categories()
        pchome_dataset_filtered = remove_repeating_urls(pchome_dataset)
        insert_data(conn, pchome_dataset_filtered, version_id)
        print(f"Inserting the dataset ({len(pchome_dataset_filtered), len(pchome_dataset)} items) into the database...")
        conn.commit()
    
    conn.close()

if __name__ == "__main__":
    main()