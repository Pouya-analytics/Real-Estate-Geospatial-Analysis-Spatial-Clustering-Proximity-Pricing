# -*- coding: utf-8 -*-
"""
build_map.py
--------------
Builds the interactive Folium map: a multi-layer deliverable a
freelance client could actually open and click through, not just a
static screenshot. Layers:
  1. Property markers, colored by price (a real choropleth-style
     circle marker layer, not just one undifferentiated color)
  2. K-means cluster boundaries (convex hulls) with cluster stats
  3. A toggleable layer control so the client can switch between views
"""
import os
import sys

import pandas as pd
import folium
from folium.plugins import HeatMap
import branca.colormap as cm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_map():
    df = pd.read_csv(os.path.join(OUTPUT_DIR, "properties_for_map.csv"))

    center_lat = df["latitude"].mean()
    center_lon = df["longitude"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="cartodbpositron")

    # ---------------------------------------------------------------
    # LAYER 1: individual property markers, colored by price
    # ---------------------------------------------------------------
    price_colormap = cm.LinearColormap(
        colors=["#2166ac", "#92c5de", "#fddbc7", "#d6604d", "#b2182b"],
        vmin=df["price_per_unit_area"].min(),
        vmax=df["price_per_unit_area"].max(),
    )
    price_colormap.caption = "Price per unit area (higher = more expensive)"

    price_layer = folium.FeatureGroup(name="Properties (colored by price)", show=True)
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color=price_colormap(row["price_per_unit_area"]),
            fill=True,
            fill_color=price_colormap(row["price_per_unit_area"]),
            fill_opacity=0.8,
            weight=1,
            popup=folium.Popup(
                f"<b>Property #{row['id']}</b><br>"
                f"Price/unit area: {row['price_per_unit_area']:.1f}<br>"
                f"Distance to MRT: {row['dist_to_mrt_m']:.0f}m<br>"
                f"Cluster: {row['cluster_kmeans']}<br>"
                f"Distance band: {row['distance_band']}",
                max_width=250,
            ),
        ).add_to(price_layer)
    price_layer.add_to(m)
    price_colormap.add_to(m)

    # ---------------------------------------------------------------
    # LAYER 2: price density heatmap (weighted by price, so this shows
    # WHERE the expensive areas concentrate, not just where any
    # properties are -- a plain point-density heatmap would just show
    # the same shape as the property locations, adding no information)
    # ---------------------------------------------------------------
    heat_data = [[row["latitude"], row["longitude"], row["price_per_unit_area"]]
                 for _, row in df.iterrows()]
    heat_layer = folium.FeatureGroup(name="Price-weighted heatmap", show=False)
    HeatMap(heat_data, radius=18, blur=22, max_zoom=14).add_to(heat_layer)
    heat_layer.add_to(m)

    # ---------------------------------------------------------------
    # LAYER 3: K-means cluster markers (cluster centroids, sized by
    # property count, colored by average cluster price)
    # ---------------------------------------------------------------
    cluster_summary = pd.read_csv(os.path.join(OUTPUT_DIR, "kmeans_cluster_summary.csv"))
    cluster_layer = folium.FeatureGroup(name="Cluster centroids (K-means)", show=False)
    for _, row in cluster_summary.iterrows():
        folium.CircleMarker(
            location=[row["centroid_lat"], row["centroid_lon"]],
            radius=8 + row["n_properties"] / 10,
            color="black",
            weight=2,
            fill=True,
            fill_color=price_colormap(row["avg_price"]),
            fill_opacity=0.9,
            popup=folium.Popup(
                f"<b>Cluster {int(row['cluster_kmeans'])}</b><br>"
                f"{int(row['n_properties'])} properties<br>"
                f"Avg price: {row['avg_price']:.1f}<br>"
                f"Avg distance to MRT: {row['avg_dist_to_mrt']:.0f}m",
                max_width=250,
            ),
        ).add_to(cluster_layer)
    cluster_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    out_path = os.path.join(OUTPUT_DIR, "property_map.html")
    m.save(out_path)
    print(f"Map saved to {out_path}")
    return m


if __name__ == "__main__":
    build_map()
