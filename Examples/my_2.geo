# Circle Construction from 3 points using geomteric method

point A at (100, 100)
point B at (300, 100)
point C at (200, 50)

segment AB of A B
segment AC of A C

perpendicular_bisector PB1 of AB
perpendicular_bisector PB2 of AC

intersection P of PB1 PB2

let x = distance(P, B)

circle C with radius = x centered_at P

label AB "Side AB"
label AC "Side AC"
label P "Circumcenter"
label PB1 "Bisector AB"
label PB2 "Bisector AC"
grid