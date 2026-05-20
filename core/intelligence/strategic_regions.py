from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


STRATEGIC_REGIONS: Dict[str, Dict[str, Any]] = {
    "eastern_mediterranean": {
        "name": "eastern_mediterranean",
        "label": "Eastern Mediterranean",
        "bbox": {"lat_min": 30.0, "lat_max": 42.5, "lon_min": 19.0, "lon_max": 37.5},
        "countries": ["Cyprus", "Greece", "Turkey", "Turkiye", "Israel", "Lebanon", "Syria", "Egypt"],
        "ports": [
            {"name": "Piraeus", "lat": 37.94, "lon": 23.64},
            {"name": "Limassol", "lat": 34.67, "lon": 33.04},
            {"name": "Haifa", "lat": 32.82, "lon": 35.00},
            {"name": "Port Said", "lat": 31.26, "lon": 32.30},
            {"name": "Alexandria", "lat": 31.20, "lon": 29.92},
        ],
        "energy": [
            {"name": "Suez Canal approaches", "lat": 30.45, "lon": 32.35},
            {"name": "Levant Basin gas area", "lat": 33.20, "lon": 34.10},
            {"name": "Ceyhan energy terminal", "lat": 36.88, "lon": 35.92},
        ],
        "logistics": [
            {"name": "Aegean sea lane", "lat": 37.00, "lon": 25.00},
            {"name": "Cyprus air-sea corridor", "lat": 35.20, "lon": 33.30},
        ],
    },
    "black_sea": {
        "name": "black_sea",
        "label": "Black Sea",
        "bbox": {"lat_min": 40.0, "lat_max": 48.5, "lon_min": 27.0, "lon_max": 42.5},
        "countries": ["Ukraine", "Russia", "Turkey", "Turkiye", "Romania", "Bulgaria", "Georgia"],
        "ports": [
            {"name": "Odesa", "lat": 46.49, "lon": 30.74},
            {"name": "Constanta", "lat": 44.17, "lon": 28.65},
            {"name": "Novorossiysk", "lat": 44.72, "lon": 37.78},
            {"name": "Samsun", "lat": 41.29, "lon": 36.33},
        ],
        "energy": [
            {"name": "Trans-Balkan corridor", "lat": 43.20, "lon": 27.90},
            {"name": "Caucasus energy route", "lat": 42.10, "lon": 41.70},
        ],
        "logistics": [
            {"name": "Danube-Black Sea corridor", "lat": 44.25, "lon": 28.10},
            {"name": "Crimea maritime approaches", "lat": 45.20, "lon": 33.90},
        ],
    },
    "south_china_sea": {
        "name": "south_china_sea",
        "label": "South China Sea",
        "bbox": {"lat_min": -2.5, "lat_max": 24.0, "lon_min": 104.0, "lon_max": 123.0},
        "countries": ["China", "Vietnam", "Philippines", "Malaysia", "Brunei", "Indonesia", "Taiwan"],
        "ports": [
            {"name": "Singapore", "lat": 1.29, "lon": 103.85},
            {"name": "Manila", "lat": 14.59, "lon": 120.98},
            {"name": "Ho Chi Minh City", "lat": 10.78, "lon": 106.70},
            {"name": "Hong Kong", "lat": 22.30, "lon": 114.17},
        ],
        "energy": [
            {"name": "Natuna gas area", "lat": 3.80, "lon": 108.20},
            {"name": "Reed Bank area", "lat": 11.50, "lon": 117.30},
        ],
        "logistics": [
            {"name": "Malacca-SCS approach", "lat": 2.20, "lon": 104.30},
            {"name": "Luzon Strait approach", "lat": 20.20, "lon": 121.00},
        ],
    },
    "baltics": {
        "name": "baltics",
        "label": "Baltics",
        "bbox": {"lat_min": 53.0, "lat_max": 61.5, "lon_min": 12.0, "lon_max": 31.5},
        "countries": ["Estonia", "Latvia", "Lithuania", "Poland", "Finland", "Sweden", "Russia", "Belarus"],
        "ports": [
            {"name": "Tallinn", "lat": 59.44, "lon": 24.75},
            {"name": "Riga", "lat": 56.95, "lon": 24.11},
            {"name": "Klaipeda", "lat": 55.70, "lon": 21.13},
            {"name": "Gdansk", "lat": 54.35, "lon": 18.65},
        ],
        "energy": [
            {"name": "Baltic energy corridor", "lat": 55.90, "lon": 21.70},
            {"name": "Gulf of Finland infrastructure", "lat": 59.70, "lon": 25.50},
        ],
        "logistics": [
            {"name": "Suwalki corridor", "lat": 54.10, "lon": 23.20},
            {"name": "Rail Baltica corridor", "lat": 56.90, "lon": 24.30},
        ],
    },
    "persian_gulf": {
        "name": "persian_gulf",
        "label": "Persian Gulf",
        "bbox": {"lat_min": 23.0, "lat_max": 31.5, "lon_min": 47.0, "lon_max": 58.5},
        "countries": ["Iran", "Iraq", "Kuwait", "Saudi Arabia", "Bahrain", "Qatar", "United Arab Emirates", "Oman"],
        "ports": [
            {"name": "Jebel Ali", "lat": 25.01, "lon": 55.06},
            {"name": "Ras Tanura", "lat": 26.64, "lon": 50.16},
            {"name": "Kuwait Shuwaikh", "lat": 29.35, "lon": 47.93},
            {"name": "Bandar Abbas", "lat": 27.18, "lon": 56.28},
        ],
        "energy": [
            {"name": "Strait of Hormuz", "lat": 26.57, "lon": 56.25},
            {"name": "Ras Tanura oil terminal", "lat": 26.64, "lon": 50.16},
            {"name": "South Pars gas area", "lat": 27.50, "lon": 52.20},
        ],
        "logistics": [
            {"name": "Hormuz shipping lane", "lat": 26.30, "lon": 56.40},
            {"name": "Gulf tanker corridor", "lat": 26.10, "lon": 52.50},
        ],
    },
    "taiwan_strait": {
        "name": "taiwan_strait",
        "label": "Taiwan Strait",
        "bbox": {"lat_min": 22.0, "lat_max": 27.5, "lon_min": 117.5, "lon_max": 123.0},
        "countries": ["Taiwan", "China"],
        "ports": [
            {"name": "Kaohsiung", "lat": 22.62, "lon": 120.28},
            {"name": "Taichung", "lat": 24.29, "lon": 120.52},
            {"name": "Xiamen", "lat": 24.48, "lon": 118.09},
            {"name": "Fuzhou", "lat": 26.08, "lon": 119.30},
        ],
        "energy": [
            {"name": "Taiwan LNG corridor", "lat": 24.10, "lon": 120.30},
            {"name": "Fujian coastal energy area", "lat": 25.20, "lon": 119.10},
        ],
        "logistics": [
            {"name": "Taiwan Strait sea lane", "lat": 24.10, "lon": 119.80},
            {"name": "Matsu-Kinmen approaches", "lat": 25.80, "lon": 119.80},
        ],
    },
}


def resolve_strategic_region(name: str | None) -> Optional[Dict[str, Any]]:
    if not name:
        return None
    key = normalize_region_key(name)
    region = STRATEGIC_REGIONS.get(key)
    return deepcopy(region) if region else None


def normalize_region_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def list_strategic_region_names() -> List[str]:
    return sorted(STRATEGIC_REGIONS)


__all__ = ["STRATEGIC_REGIONS", "list_strategic_region_names", "normalize_region_key", "resolve_strategic_region"]
