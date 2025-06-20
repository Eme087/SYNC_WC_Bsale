import requests
from woocommerce import API
from dotenv import load_dotenv
import os

load_dotenv()
WC_URL = os.getenv("WC_URL")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=30
)

BSALE_TOKEN = "f33bc19ae54eb12d58050f79ca22f105edd6bc32"
HEADERS = {"access_token": BSALE_TOKEN}

def obtener_stock_bsale():
    stock = {}
    offset = 0
    while True:
        url = f"https://api.bsale.cl/v1/stocks.json?expand=[variant]&limit=50&offset={offset}"
        print(f"🔄 Consultando Bsale: página con offset {offset}")
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            print("❌ Error al consultar Bsale:", resp.text)
            break
        data = resp.json().get("items", [])
        if not data:
            break
        for item in data:
            variant = item.get("variant", {})
            code = variant.get("code")
            qty = item.get("quantityAvailable", 0)
            if code:
                sku = str(code).strip()
                stock[sku] = stock.get(sku, 0) + qty
        offset += 50
    return stock

def obtener_stock_woocommerce():
    stock_wc = {}
    page = 1
    while True:
        print(f"📥 Cargando productos WooCommerce (página {page})...")
        productos = wcapi.get("products", params={"per_page": 100, "page": page}).json()
        if not productos or not isinstance(productos, list):
            break
        for p in productos:
            sku = p.get("sku")
            if sku:
                stock_wc[sku.strip()] = {
                    "id": p["id"],
                    "stock": int(p.get("stock_quantity") or 0)
                }
        page += 1
    return stock_wc

def sincronizar_inventario(bsale_data, woocommerce_data):
    actualizados = 0
    for sku, stock_bsale in bsale_data.items():
        if sku not in woocommerce_data:
            continue
        wc_entry = woocommerce_data[sku]
        stock_wc = wc_entry["stock"]
        stock_bsale = int(stock_bsale)
        if stock_wc == stock_bsale:
            continue
        wcapi.put(f"products/{wc_entry['id']}", {
            "stock_quantity": stock_bsale,
            "manage_stock": True
        })
        print(f"✅ SKU {sku} | WooCommerce: {stock_wc} → {stock_bsale}")
        actualizados += 1
    print(f"\n🔁 Total productos actualizados: {actualizados}")

def main():
    print("📦 Obteniendo stock desde Bsale...")
    bsale_stock = obtener_stock_bsale()

    print("🛒 Obteniendo catálogo desde WooCommerce...")
    wc_stock = obtener_stock_woocommerce()

    print("🧮 Comparando y actualizando diferencias...")
    sincronizar_inventario(bsale_stock, wc_stock)

if __name__ == "__main__":
    main()
