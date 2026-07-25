# -*- coding: utf-8 -*-
"""
spatial_analysis.py
----------------------
Core geospatial analysis: spatial clustering of properties (using
projected, meters-based coordinates -- NOT raw lat/lon, which would
silently distort cluster shapes since a degree of longitude isn't a
fixed physical distance), and proximity-to-MRT pricing analysis.

WHY PROJECT BEFORE CLUSTERING (this is not a cosmetic detail): K-means
and DBSCAN both rely on Euclidean distance. Running them directly on
(latitude, longitude) treats one degree of latitude and one degree of
longitude as equivalent distances, which is wrong -- at this latitude
(~25°N), one degree of longitude is shorter than one degree of latitude
by a factor of cos(25°) ≈ 0.91. Over a dataset spanning ~9km, that
distortion is small but real, and "small but real" is exactly the kind
of error that's invisible in a quick plot and wrong in a client
deliverable. This script always clusters on the EPSG:3826 projected
coordinates (in meters), never on raw degrees.
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_geodata import load_geodataframe, TAIWAN_PROJECTED_CRS

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def add_kmeans_clusters(gdf, n_clusters=5, random_state=42):
    """K-means clustering on PROJECTED coordinates (meters), giving
    geographically compact clusters suitable for a "neighborhood
    segmentation" type of analysis."""
    projected = gdf.to_crs(TAIWAN_PROJECTED_CRS)
    coords = np.column_stack([projected.geometry.x, projected.geometry.y])

    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    gdf = gdf.copy()
    gdf["cluster_kmeans"] = km.fit_predict(coords)
    return gdf, km


def add_dbscan_clusters(gdf, eps_meters=400, min_samples=5):
    """DBSCAN on projected coordinates -- unlike K-means, DBSCAN finds
    DENSITY-based clusters and naturally labels sparse, isolated
    properties as noise (-1) rather than forcing them into a cluster.
    This is the more honest clustering choice when the actual question
    is "where are the dense pockets of transactions," since K-means
    would force outlier properties into whichever centroid is nearest,
    even if they're genuinely isolated."""
    projected = gdf.to_crs(TAIWAN_PROJECTED_CRS)
    coords = np.column_stack([projected.geometry.x, projected.geometry.y])

    db = DBSCAN(eps=eps_meters, min_samples=min_samples)
    gdf = gdf.copy()
    gdf["cluster_dbscan"] = db.fit_predict(coords)
    return gdf


def proximity_price_analysis(gdf):
    """Bins properties by distance-to-MRT and computes price stats per
    bin -- the direct, interpretable version of the -0.67 correlation
    that's much easier to explain to a non-technical client than a
    correlation coefficient alone."""
    bins = [0, 250, 500, 1000, 2000, 4000, gdf["dist_to_mrt_m"].max() + 1]
    labels = ["0-250m", "250-500m", "500m-1km", "1-2km", "2-4km", "4km+"]
    gdf = gdf.copy()
    gdf["distance_band"] = pd.cut(gdf["dist_to_mrt_m"], bins=bins, labels=labels)

    summary = gdf.groupby("distance_band").agg(
        n_properties=("id", "count"),
        avg_price=("price_per_unit_area", "mean"),
        median_price=("price_per_unit_area", "median"),
        avg_age=("house_age_years", "mean"),
    ).round(2)
    return gdf, summary


if __name__ == "__main__":
    gdf = load_geodataframe()

    print("=" * 70)
    print("SPATIAL CLUSTERING")
    print("=" * 70)
    gdf_clustered, kmeans_model = add_kmeans_clusters(gdf, n_clusters=5)
    cluster_summary = gdf_clustered.groupby("cluster_kmeans").agg(
        n_properties=("id", "count"),
        avg_price=("price_per_unit_area", "mean"),
        avg_dist_to_mrt=("dist_to_mrt_m", "mean"),
        centroid_lat=("latitude", "mean"),
        centroid_lon=("longitude", "mean"),
    ).round(2)
    print("\nK-means cluster summary (5 clusters, on projected meters):")
    print(cluster_summary.to_string())
    cluster_summary.to_csv(os.path.join(OUTPUT_DIR, "kmeans_cluster_summary.csv"))

    gdf_clustered = add_dbscan_clusters(gdf_clustered, eps_meters=400, min_samples=5)
    n_dbscan_clusters = len(set(gdf_clustered["cluster_dbscan"])) - (1 if -1 in gdf_clustered["cluster_dbscan"].values else 0)
    n_noise = (gdf_clustered["cluster_dbscan"] == -1).sum()
    print(f"\nDBSCAN (eps=400m, min_samples=5): {n_dbscan_clusters} dense clusters found, "
          f"{n_noise} properties classified as noise/isolated ({n_noise/len(gdf_clustered)*100:.1f}%)")

    print("\n" + "=" * 70)
    print("PROXIMITY-TO-MRT PRICING ANALYSIS")
    print("=" * 70)
    gdf_banded, proximity_summary = proximity_price_analysis(gdf_clustered)
    print(proximity_summary.to_string())
    proximity_summary.to_csv(os.path.join(OUTPUT_DIR, "proximity_price_summary.csv"))

    correlation = gdf["dist_to_mrt_m"].corr(gdf["price_per_unit_area"])
    print(f"\nCorrelation (distance to MRT vs. price): {correlation:.3f}")

    # Save the full clustered/banded dataset for the map-building script
    gdf_banded.drop(columns="geometry").to_csv(
        os.path.join(OUTPUT_DIR, "properties_with_clusters.csv"), index=False)
    gdf_banded[["id", "latitude", "longitude", "price_per_unit_area", "dist_to_mrt_m",
                "cluster_kmeans", "cluster_dbscan", "distance_band"]].to_csv(
        os.path.join(OUTPUT_DIR, "properties_for_map.csv"), index=False)

    print(f"\nResults saved to {OUTPUT_DIR}/")
