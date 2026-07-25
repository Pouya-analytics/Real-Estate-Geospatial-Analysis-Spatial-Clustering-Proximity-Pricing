# Real Estate Geospatial Analysis — Spatial Clustering & Proximity Pricing

I built this because most "geospatial" portfolio projects are just
scatter plots with latitude and longitude as x and y axes. That's not
geospatial analysis — it's a scatter plot. I wanted to show I can
work with actual coordinate systems, projections, and spatial
operations correctly.

---

## What I built

K-means and DBSCAN clustering on 414 real property transactions in
Xindian District, New Taipei City, plus an interactive multi-layer
Folium map with toggleable layers.

---

## The detail most people get wrong

K-means and DBSCAN both use Euclidean distance. Running them on raw
latitude/longitude treats one degree of longitude as the same physical
distance as one degree of latitude. At this dataset's latitude (~25°N),
that's wrong by about 9% — cos(25°) ≈ 0.906.

I reprojected every coordinate to EPSG:3826 (Taiwan's official
projected coordinate system, in meters) before running any clustering.
The result is geometrically correct. Running on raw degrees would have
produced silently wrong cluster shapes.

---

## Findings

**Price vs. distance to MRT:** r = -0.674. Properties closest to
transit cost nearly 3x more than the farthest.

| Distance band | Avg price |
|---|---|
| 0–250m | 48.53 |
| 250–500m | 44.87 |
| 500m–1km | 39.52 |
| 1–2km | 26.59 |
| 4km+ | 17.06 |

**DBSCAN** found 8 dense sub-clusters and flagged 27 properties (6.5%)
as genuine spatial outliers — properties K-means would have silently
folded into the nearest cluster.

---

## Dataset

Real UCI Real Estate Valuation dataset (Yeh & Hsu, 2018), sourced
from the plotly/datasets repository. 414 transactions, 0 nulls. Real
data, no synthetic disclosure needed.

---

## How to run it

```bash
pip install -r requirements.txt
python scripts/spatial_analysis.py
python scripts/build_map.py
```

Open `output/property_map.html` in any browser for the interactive map.

---

## Stack

GeoPandas · Shapely · Folium · scikit-learn · pandas · matplotlib
