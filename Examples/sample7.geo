param t from 0 to 15.7 step 0.2

let r = 100

let wheel_cx = r * t
let wheel_cy = r

let point_x = r * t - r * sin(t)
let point_y = r - r * cos(t)

point A at (-20,r)
point B at (1600,r)
segment Ground of A B

point P at (wheel_cx, wheel_cy)  
circle Wheel with radius = r centered_at P
hide Wheel

point CycloidPoint at (point_x, point_y)

point A1 at (wheel_cx, wheel_cy)
point B1 at (point_x, point_y)
segment Spoke of A B

sweep t

label Wheel "Wheel"
label CycloidPoint "Traced Point"
label Ground "Rolling Surface"
