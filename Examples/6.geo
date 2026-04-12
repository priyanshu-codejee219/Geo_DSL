define equilateral(cx, cy, r) {
  let h = r * 0.866
  point V1 at (cx, cy + r)
  point V2 at (cx + h, cy - r / 2)
  point V3 at (cx - h, cy - r / 2)
  triangle EquilateralTriangle of V1 V2 V3
  return EquilateralTriangle
}
param t from 1 to 100 step 10
call equilateral(0,0,10*t)
if t>50{circle C with radius=10*t}
sweep t