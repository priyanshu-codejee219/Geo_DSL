#origin
point O at (0,0)

#intitalising param varible for animating
param n from 3 to 30 step 3

#
point Y at (200*n,200*n)
regular_poly P with radius=100*n, sides=n centered_at Y
sweep n 