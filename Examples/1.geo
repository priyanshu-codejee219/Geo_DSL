# ============================================================
# 01_triangle_centers.geo
# Classical Triangle Centres: circumcircle, incircle,
# medial triangle, and perpendicular bisectors
# Features: primitive shapes, derived constructions,
#           measurements, assertions, labels, grid
# ============================================================

# --- Vertices of the main triangle --------------------------
point A at (60, 40)
point B at (340, 40)
point C at (200, 320)

# --- Main triangle ------------------------------------------
triangle T passes_through A B C
label T "Triangle ABC"

# --- Circumscribed and inscribed circles --------------------
circumcircle CC of T
incircle    IC of T
label CC "Circumcircle"
label IC  "Incircle"
