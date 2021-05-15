# 4D Net Tilings

## Running
Install the prerequisite packages:
`pip install -r requirements.txt`

To find tilings
`python compute.py`

To display those tilings
`python display.py`

## How it works
* Selects a net to try.
* Generates all variants of the net using the 24 cube rotations
* Discards duplicates
* Generates a box of a given size (currently only trying 4,4,4) that will become our tiling unit
* Discards variants that do not fit in the box
* Generates a SAT problem that will be satisfied iff the box is filled completely by the net units
* Sends the SAT problem to a sat solver
* Interprets the solution as a list of net units

## Results
238/261 Found

Remaining: 18, 21, 38, 43, 68, 73, 82, 92, 94, 98, 128, 139, 140, 145, 162, 169, 176, 180, 194, 197, 201, 238, 239
