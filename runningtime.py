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
from math import sqrt

# Constants
LINESPEED = 400/3.6 # Maximum speed on straight track (used as "infinity"). Section speeds are capped at this.
TRAINLENGTH = 264
LEEWAY = 1.0 # Aim to be this many m/s below the speed limit when we hit a curve

# Input
# TODO: Check sys.argv for a script file, or maybe multiple of them, and parse those first/instead
tracksections = []
while True:
	n = input("Enter track length in m: ")
	if not n: break
	d = input("Enter speed limit [400km/h]: ") or 400
	tracksections.append((int(n),min(int(d)/3.6, LINESPEED)))
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
mode = "Cruise" # or "Brake" or "Power"
speed = 0.0

# And we simulate!
while True:
	# This is like Lunar Lander: first we decide what we're going to do this second,
	# then we do it. If the current section doesn't have enough meters in it, we'll
	# solve Achilles and the Tortoise by advancing time by less than a second; else
	# we advance one entire second each iteration.
	
	# First, figure out what our limits are. Then, figure out whether we should be
	# powering, cruising, or braking. Then do it.
	
	# Note that powering and braking take time to come to full effect. The transition
	# from cruise to either of the above will advance time by two seconds (rather
	# than the usual one second per iteration), or by whatever it takes to reach the
	# end of the track section, whichever is shorter; after that iteration, it is
	# assumed that the gentle acceleration is complete. (The difference won't be much
	# even in the worst case. Maybe like 0.05m/s of speed difference.)

	# TODO: Require a minimum 10s cruise time between powering and braking
	maxspeed = min(curspeed, prevspeed if posn<TRAINLENGTH else LINESPEED)
	if curspeed > maxspeed: raise DerailmentError # Stub, will actually raise NameError :)
	# Calculate the speed we would be at when we hit the next section, if we hit
	# the brakes now.
	# NOTE: Technically the train doesn't follow three separate parts of linear
	# acceleration, but a curve. However, the error from using this simplified
	# estimate is insignificant compared to other inaccuracy in the system (eg
	# measurement error).
	if mode=="Brake2":
		# Already got the brakes fully on.
		distance_to_full_braking_power = 0.0
		speed_full_brake = curspeed
	elif mode=="Brake1":
		# The brakes went on one second ago, they're nearly full.
		distance_to_full_braking_power = curspeed - 0.6375/2
		speed_full_brake = curspeed - 0.6375
	else:
		# Brakes aren't on.
		distance_to_full_braking_power = 2 * (curspeed - 0.85/2)
		speed_full_brake = curspeed - 0.85
	# If we hit the brakes now (or already have hit them), we'll go another d meters and be going at s m/s before reaching full braking power.
	distance_left = cursection - posn - distance_to_full_braking_power
	# And we'll have distance_left meters before we hit the next section. (That might be less than zero.)
	# Linear acceleration states that d = vt + at²/2
	# In this case:
	# distance_left = speed_full_brake*t + -0.85*t*t/2
	# Reorganizing that gives us:
	# 0.425*t*t - speed_full_brake*t + distance_left = 0
	# This is a quadratic equation that might have no solution. If it has
	# no solution, speed_at_next_section is 0.0 (ie you would come to a
	# complete stop). So we calculate the discriminant first.
	# Let's use names that match the quadratic formula, at least for the moment :)
	a, b, c = 0.425, -speed_full_brake, distance_left
	discriminant = b*b - 4*a*c
	if discriminant < 0:
		# No solutions to the quadratic!
		speed_at_next_section = 0.0
	else:
		# There's at least one solution. (If the discriminant's exactly zero,
		# its square root is zero, and the two roots are the same. Given that
		# we're working with IEEE floating point, rather than real numbers,
		# the possibility of this happening is pretty insignificant; and the
		# difference between a discriminant of -1e7, 0.0, and 1e7 is not at all
		# significant to us - all will result in a speed_at_next_section of
		# practically zero, which will have the same effect.) One of those
		# solutions is the time we want; the other is the time at which the
		# train would come all the way past the next section *and back again*
		# if it continued the same negative acceleration all the way past a
		# complete stop and into reverse travel, which makes absolutely no
		# physics sense, even if it makes good algebraic sense.
		
		# So! We need to prove that only one of the solutions matters - and,
		# more importantly, *which one*. As it turns out, this is pretty easy;
		# the negative root will bring the numbers back toward zero (since we
		# work with negative b, and b is less than zero), and the positive will
		# take us further away. But what if the negative root actually came to
		# a below-zero result? That would make, again, perfect algebraic sense
		# and no physics sense (what, you could reach it in a negative amount
		# of time??), but fortunately it's provably impossible:
		
		# 1) The discriminant squares b and then subtracts the product 4*a*c
		# 2) a and b are both positive (a being a constant and c being distance)
		# 3) This guarantees that the discriminant is less than b*b, therefore
		#    that its square root is less than b. QED.
		
		# Consequently, the negative root is guaranteed to be the one we want.
		t = (-b - sqrt(discriminant)) / (2 * a)
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
