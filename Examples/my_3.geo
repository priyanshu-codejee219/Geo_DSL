param theta from 0 to 6.28 step 0.2

let cx = 250
let cy = 250
let r = 100
let px = cx + r * cos(theta)
let py = cy + r * sin(theta)

point Center at (cx, cy)
point RotatingPoint at (px, py)
circle C with radius = r centered_at Center
segment Radius of Center RotatingPoint

sweep theta

label Center "Center"
label RotatingPoint "Rotating"
label C "Circle"