point O at (0,0)
point A at (0,100)
point B at (100,0)

ray Wall of O A
ray Ground of OB

let l = 100

param theta from 89 to 0 step -1
point X at (0,l*sin(theta*3.14/180))
point Y at (l*cos(theta*3.14/180),0)
segment XY of X Y
midpoint MP of XY
sweep theta

label A "Wall"
label B "Ground"

