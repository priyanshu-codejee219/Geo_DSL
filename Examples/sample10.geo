define equilateral(cx, cy, r) {
  let h = r * 0.866
  point V1 at (cx, cy + r)
  point V2 at (cx + h, cy - r / 2)
  point V3 at (cx - h, cy - r / 2)
  triangle EquilateralTriangle of V1 V2 V3
  return EquilateralTriangle
}
param t from 10 to 100 step 20
call equilateral(0,0,t)
sweep t