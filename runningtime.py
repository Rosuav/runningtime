"""
Running times calculator

Processes a series of track sections by their length (meters) and the track speed
limit (entered in km/h, converted to m/s for internal calculations). The ultimate
goal is to calculate how many minutes it will take to proceed from one station to
the next, assuming that the train begins and ends stationary (that's how you're
supposed to be at a station, right?). It presumes upon a driver who knows the
track intimately, and may therefore estimate too low for reality (a more cautious
driver will apply the brakes sooner than the simulator would); in theory, this
could be solved by placing "Brake" posts at the appropriate points, but that is
outside the scope of this project.

Rules:

1) Speed limits may not be masked by other speed limits. If maximum deceleration
   from the beginning of this section will not get the train to the speed of the
   next section, we will throw an error (derailment). This can be resolved, in a
   way, by lowering the track speed limit of the previous section; imperfect but
   may get around the problem. But this should be an abnormal track construct.
2) Track sections must be longer than the train. It is not possible to span
   three sections. This could be fixed, but would require a more complex formula
   for calculating maxspeed.

Corollaries:
* The maximum safe speed for the train is the speed limit for the current
  section, or the speed limit for the previous section if position is less than
  train length (and the previous section was slower).
* The maximum attainable speed can be deduced entirely from the above and from
  the one next track section.

"""

import sys

# Constants
LINESPEED = 400/3.6 # Maximum speed on straight track (used as "infinity"). Weird stuff may happen if curve speed exceeds this, don't do it.
TRAINLENGTH = 264
LEEWAY = 1.0 # Aim to be this many m/s below the speed limit when we hit a curve

# Input
# TODO: Check sys.argv for a script file, or maybe multiple of them, and parse those first/instead
tracksections = []
while True:
	n = input("Enter track length in m: ")
	if not n: break
	d = input("Enter speed limit [400km/h]: ") or 400
	tracksections.append((int(n),int(d)/3.6))
if not tracksections: sys.exit(0)

# As the King of Hearts instructed, we begin at the beginning of the track, go
# on till we come to the end, then stop. To facilitate that last part, we add
# a zero-length track section with a speed limit of zero; we should get to that
# at the very end of the previous section.
tracksections.append((0,0))

# Simulator initialization
t = 0.0
section = iter(tracksections)
prevspeed = LINESPEED # Assume track speed behind us (at start of simulation) is maximum.
cursection, curspeed = next(section)
nextsection, nextspeed = next(section)
posn = 0
mode = "Idle"
speed = 0.0

# And we simulate!
while True:
	"""
	This is like Lunar Lander: first we decide what we're going to do this second,
	then we do it. If the current section doesn't have enough meters in it, we'll
	solve Achilles and the Tortoise by advancing time by less than a second; else
	we advance one entire second each iteration.
	
	First, figure out what our limits are. Then, figure out whether we should be
	powering, cruising, braking gently, or braking hard. Then do it.
	
	Note that powering and braking take time to come to full effect. The first
	second is at 0.2m/s/s, the next second is at 0.425m/s/s, and thereafter the
	effect is full (0.85m/s/s).
	
	To simplify the code, the calculation is done based on iterations, not
	seconds. This introduces a corner case (which may actually not even be
	triggerable due to the rules specified above) whereby beginning acceleration
	or braking just before the end of a section may mistakenly think that the
	effect happens more quickly.
	"""
	maxspeed = min(curspeed, prevspeed if posn<TRAINLENGTH else LINESPEED)
	if curspeed > maxspeed: raise DerailmentError # Stub, will actually raise NameError :)
	"""
	Calculate the speed we would be at when we hit the next section, if we hit
	the brakes now.
	"""
	# Already got the brakes fully on
	if mode=="Brake2": distance_to_full_braking_power, speed_full_brake = 0.0, curspeed
	# The brakes went on one second ago, they're nearly full
	elif mode=="Brake1": distance_to_full_braking_power, speed_full_brake = curspeed - 0.2125, curspeed - 0.425
	# Brakes aren't on.
	else: distance_to_full_braking_power, speed_full_brake = (curspeed - 0.1) + (curspeed - 0.4125), curspeed - 0.625
	# If we hit the brakes now (or already have hit them), we'll go another d meters and be going at s m/s before reaching full braking power.
	distance_left = cursection-posn-distance_to_full_braking_power
	# And we'll have distance_left meters before we hit the next section. (That might be less than zero.)
	distance_left = speed_full_brake*t + -0.85*t*t/2
	# TODO: Solve for t. This will involve a quadratic that might have no solution.
	# If it has no solution, speed_at_next_section is 0.0 (ie you would come to a complete stop).
	speed_at_next_section = curspeed - 0.85*t
	if speed_at_next_section >= nextspeed-LEEWAY:
		# Note that if it's actually greater, we'll probably derail when we hit it
		brake
	elif curspeed < maxspeed:
		accelerate
	else:
		cruise
	# TODO: Figure out how much we change speed by (linac), and if we don't have
	# enough track left in this section, advance time by just enough to get there.
	# Otherwise, advance time 1 second and iterate.

print("Final time:", t, "seconds - %d:%02d" % divmod(int(t), 60))
