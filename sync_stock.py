import requests
import json
from woocommerce import API
from dotenv import load_dotenv
import os

# === Cargar variables desde .env ===
load_dotenv()
WC_URL = os.getenv("WC_URL")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# === WooCommerce Config ===
wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=30
)

# === Bsale Config ===
BSALE_TOKEN = "f33bc19ae54eb12d58050f79ca22f105edd6bc32"
HEADERS = {"access_token": BSALE_TOKEN}

def obtener_stock_bsale():
    stock = {}
    offset = 0
    while True:
        url = "https://api.bsale.cl/v1/stocks.json?expand=[variant]&limit=50&offset={}".format(offset)
        print("🔄 Consultando:", url)
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            print("❌ Error al consultar Bsale:", resp.text)
            break
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        for item in items:
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
        print("📥 Cargando productos WooCommerce página", page)
        productos = wcapi.get("products", params={"per_page": 100, "page": page}).json()
        if not productos or not isinstance(productos, list):
            break
        for p in productos:
            sku = p.get("sku")
            if sku:
                sku = sku.strip()
                stock_wc[sku] = {
                    "id": p["id"],
                    "stock": int(p.get("stock_quantity") or 0)
                }
        page += 1
    return stock_wc

def sincronizar_inventario(bsale_data, woocommerce_data):
    actualizados = 0
    for sku, stock_bsale in bsale_data.items():
        if sku not in woocommerce_data:
            continue  # SKU no existe en Woo

        wc_entry = woocommerce_data[sku]
        stock_wc = wc_entry["stock"]
        stock_bsale = int(stock_bsale)

        if stock_wc == stock_bsale:
            continue  # sin cambios

        # Actualizar en WooCommerce
        wcapi.put("products/{}".format(wc_entry["id"]), {
            "stock_quantity": stock_bsale,
            "manage_stock": True
        })
        print("✅ SKU {} | WooCommerce: {} → {}".format(sku, stock_wc, stock_bsale))
        actualizados += 1

    print("\n🔁 Total productos actualizados: {}".format(actualizados))

def main():
    print("📦 Obteniendo stock desde Bsale...")
    bsale_stock = obtener_stock_bsale()

    print("📦 Obteniendo catálogo desde WooCommerce...")
    wc_stock = obtener_stock_woocommerce()

    print("🔧 Comparando y actualizando diferencias...")
    sincronizar_inventario(bsale_stock, wc_stock)

if __name__ == "__main__":
    main()
