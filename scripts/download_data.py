from __future__ import annotations

import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATASET_URL = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
EXPECTED_FILES = {
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
}


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    present = {p.name for p in RAW_DIR.glob("*.csv")}
    if EXPECTED_FILES.issubset(present):
        print(f"Les 9 fichiers CSV existent déjà dans {RAW_DIR}.")
        return

    with tempfile.TemporaryDirectory(prefix="olist-download-") as tmp:
        archive = Path(tmp) / "olist.zip"
        request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "data-quality-monitor/1.0"})
        print("Téléchargement du jeu Olist depuis Kaggle…")
        with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        with zipfile.ZipFile(archive) as bundle:
            available = {Path(name).name for name in bundle.namelist() if name.lower().endswith(".csv")}
            missing = EXPECTED_FILES - available
            if missing:
                raise RuntimeError("Archive Kaggle incomplète : " + ", ".join(sorted(missing)))
            for member in bundle.infolist():
                if Path(member.filename).name in EXPECTED_FILES:
                    destination = RAW_DIR / Path(member.filename).name
                    with bundle.open(member) as src, destination.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
    print(f"Jeu prêt : 9 fichiers CSV dans {RAW_DIR}.")
    print("Consultez le README pour l’attribution et la licence CC BY-NC-SA 4.0 du dataset.")


if __name__ == "__main__":
    main()
