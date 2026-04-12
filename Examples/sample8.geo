# --- Two focal points ---------------------------------------
point F1 at (100, 0)
point F2 at (35, 0)
label F1 "Focus F1"
label F2 "Focus F2"

# --- Segment joining the foci (the major axis base) ---------
segment Focal_axis passes_through F1 F2
label Focal_axis "Focal axis"

# --- The sum-of-distances constant (2a for the ellipse) -----
let two_a = 240

# --- Locus: all points P where dist(P,F1)+dist(P,F2) = 240 -
# This traces the ellipse exactly
locus of point P {
    constraint distance(P,F1) +distance(P,F2) = two_a / 2
}
# --- Secondary locus: circle (special case of ellipse F1=F2)-
point FC at (250, 450)
circle Ref_circle with radius=80 centered_at FC
locus of point Q {
    constraint distance(Q,FC) +distance(Q,FC) = 160
}
label Ref_circle "Circle locus (F1=F2)"

note "Locus of P: dist(P,F1)+dist(P,F2)=const traces an ellipse"
grid