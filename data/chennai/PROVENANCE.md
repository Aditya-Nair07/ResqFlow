# Chennai fixtures provenance

Copied from the friend reference project `ResqFlow-main/data/` for demonstration and review demos.

These are **demonstration fixtures** inspired by publicly described Chennai flood contexts (including 2015). They are **not** verified municipal operational feeds.

| File | Role |
|---|---|
| chennai_shelters.csv | Sample shelter locations/capacity |
| chennai_roads.geojson | Sample road network geometry |
| chennai_wards.geojson | Sample ward polygons |
| chennai_*_rainfall.csv | Historical-style rainfall series |
| chennai_*_river_levels.csv | River-level series |
| citizen_reports_2015.json | Synthetic/news-derived citizen-style reports |
| chennai_elevation.npy | Elevation grid sample |

Coordinate model for the live plant remains the deterministic scenario grid in `scenarios/`. Lat/lng from fixtures are mapped via nearest-node snapping in the API, not `% 50` heuristics.
