# --- Centre of symmetry ------------------------------------
point O at (250, 250)

# --- Three mirror axes through O ----------------------------
line Ax1 passes_through O
line Ax2 passes_through O
line Ax3 passes_through O

# Ax2 is 60 degrees from Ax1, Ax3 is 120 degrees from Ax1
angle ax12 = 60 deg
angle ax13 = 120 deg

# --- Seed triangle (fundamental domain) --------------------
point P1 at (250, 180)
point P2 at (310, 250)
point P3 at (250, 250)
triangle Seed passes_through P1 P2 P3
label Seed "Seed"

# --- First reflection (over Ax1) ----------------------------
reflect Seed over Ax1
label Seed "R1"

# --- Rotate seed by 60 deg to fill the ring -----------------
rotate Seed by 60 deg about O
label Seed "R2"

rotate Seed by 120 deg about O
label Seed "R3"

rotate Seed by 180 deg about O
label Seed "R4"

rotate Seed by 240 deg about O
label Seed "R5"

rotate Seed by 300 deg about O
label Seed "R6"

# --- Enclosing regular hexagon ------------------------------
regular_poly Hex with radius=100 centered_at O
label Hex "Hexagonal frame"

# --- Circumcircle of the hexagon ----------------------------
circumcircle HexCC of Hex
label HexCC "Circumcircle"

# --- Central decorative circle ------------------------------
circle Hub with radius=18 centered_at O
label Hub "Hub"

rotate Hex by 60 deg about O
rotate Hex by 60 deg about O
rotate Hex by 60 deg about O
rotate Hex by 60 deg about O
rotate Hex by 60 deg about O
rotate Hex by 60 deg about O

# --- Parallelism assertion between axes ---------------------
# line L and a translated copy should remain parallel
# line L and a translated copy should remain parallel
point Q1a at (200, 100)
point Q2a at (200, 180)
line L passes_through Q1a Q2a
line L1 passes_through Q1a Q2a
translate L1 by (10,20)
assert L1 parallel_to L



point Q1 at (280, 180)
point Q2 at (280, 320)
line ParallelAx passes_through Q1 Q2

# --- Perpendicularity assertion: Ax2 perp to ParallelAx -----
assert Ax2 perpendicular_to ParallelAx


hide Ax1 Ax2 Ax3
