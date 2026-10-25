Vector map data for this atlas (polity v2 with de facto control and trade).
Coordinates: pixels of the source map, 4401 x 2037, x right, y down, origin top-left; 0.520 miles per pixel.
GeoJSON (load in QGIS as a non-georeferenced layer, or read with any JSON tool):
  dejure_claims            the painted claims, one MultiPolygon per polity
  defacto_held_fillNN      held land for gap fill NN/10 days (00, 05, 10, 20)
  claimed_unheld_fillNN    land a polity claims but does not hold
  contested_fillNN         held land with a rival within half a day
  trade_routes             routes by traffic class (local / regional / main)
  minor_roads              the suggested unmarked roads
  towns                    marked and suggested towns with holder, claimant, port, catchment people,
                           market access
political.svg: the same as Inkscape layers over a blank canvas of the map's size; place the source map
underneath (same pixel size) and restyle freely.
