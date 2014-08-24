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
accel = {"Brake":-0.85, "Cruise":0.0, "Power":0.85}
print() # A blank line will make the display look tidier with redirection

def residual_speed(speed, distance):
	# Linear acceleration states that d = vt + at²/2
	# In this case:
	# distance_left = speed_full_brake*t + -0.85*t*t/2
	# Reorganizing that gives us:
	# 0.425*t*t - speed_full_brake*t + distance_left = 0
	# This is a quadratic equation that might have no solution. If it has
	# no solution, speed_at_next_section is 0.0 (ie you would come to a
	# complete stop). So we calculate the discriminant first.
	# Let's use names that match the quadratic formula, at least for the moment :)
	a, b, c = 0.425, -speed, distance
	discriminant = b*b - 4*a*c
	if discriminant < 0:
		# No solutions to the quadratic!
		return 0.0
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
		return speed - 0.85*t

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

	maxspeed = min(curspeed, prevspeed if posn<TRAINLENGTH else LINESPEED)
	if speed > maxspeed:
		print("[%6.2f] Derailed! %d km/h through %d km/h curve"%(t, int(speed*3.6+.5), int(maxspeed*3.6+.5)))
		break
	# Calculate the speed we would be at when we hit the next section, if we hit
	# the brakes now.
	if mode=="Brake":
		# Already got the brakes on. Figure out what would happen if we cruised.
		distance_to_full_braking_power = 2 * (speed - 0.85/2)
		speed_full_brake = speed - 0.85
	elif mode=="Power":
		# We need to slow to cruise before braking.
		# This involves two seconds of backing off the acceleration (during which
		# we'll gain 0.85 m/s, so we'll average speed+.85/2 for those two secs),
		# followed by two more seconds of beginning the deceleration, which are
		# exactly like the third case, only speed will be 0.85 higher. Add it
		# all up and you get a target speed equal to current speed, and an average
		# speed of 0.85/2 higher than that speed.
		# This decision is made such that one more second of powering would cause
		# us to miss the curve speed, so it assumes that additional second first.
		distance_to_full_braking_power = (speed + 0.85/2) + 4 * (speed + 0.85 + 0.85/2)
		speed_full_brake = speed + 0.85
	else:
		# Brakes aren't on.
		# As above, assume one more second at current speed.
		distance_to_full_braking_power = speed + 2 * (speed - 0.85/2)
		speed_full_brake = speed - 0.85
	# If we hit the brakes now (or already have hit them), we'll go another d meters and be going at s m/s before reaching full braking power.
	distance_left = cursection - posn - distance_to_full_braking_power
	# And we'll have distance_left meters before we hit the next section. (That might be less than zero.)
	# print("Speed next sec: %.2f / %.2f"%(residual_speed(speed_full_brake, distance_left), nextspeed))

	if mode=="Brake":
		nextmode = "Cruise" if speed<nextspeed+0.85 else "Brake"
	elif residual_speed(speed_full_brake, distance_left) >= nextspeed - LEEWAY and speed > nextspeed - LEEWAY:
		# Note that if it's actually greater, we'll probably derail when we hit it
		# If we were powering, drop into cruise for an iteration.
		nextmode = "Cruise" if mode=="Power" else "Brake"
	elif speed < maxspeed:
		# Apply power only if we can do so for ten estimated seconds
		# Note that this doesn't guarantee that we *will* power for ten seconds,
		# only that current estimates show that we probably can.
		if mode=="Cruise" and speed >= maxspeed - 8.5: nextmode = "Cruise"
		else: nextmode = "Cruise" if mode=="Brake" else "Power"
	else:
		nextmode = "Cruise"
	if mode != nextmode:
		advance = 2.0
		print("[%6.2f] %s"%(t, nextmode))
	else:
		advance = 1.0
	# Applying full power when the current speed is over 200kph can't actually manage
	# the ideal 0.85m/s/s acceleration. The actual acceleration possible is given by a
	# graph of a circle tangent to 0.85 at 200kph and to 0.0 at 400kph.
	if speed > 200/3.6:
		maxpower = sqrt((1280/3.6+speed)*(400/3.6-speed))/(speed+440/3.6)
	else:
		maxpower = 0.85
	# When we change modes, the effective acceleration is the average of the previous
	# and the new. Obviously when the modes are the same, we end up back where we started.
	actual_accel = (min(accel[mode],maxpower) + min(accel[nextmode],maxpower)) / 2
	print("[%6.2f] Speed %.2f kph, goal %s, mp %.2f, actual accel %.2f"%(t,speed*3.6,nextmode,maxpower,actual_accel))
	distance = advance * (speed + actual_accel/2)
	# print("[%6.2f] %s -> %s, spd %.2f, pos %f"%(t, mode, nextmode, speed, posn))
	if speed + actual_accel < 0:
		# We come to a complete halt. This should only happen at the end of the line,
		# and we simply end the simulation.
		halt_time = speed / -actual_accel * advance
		posn += distance * halt_time / advance
		t += halt_time
		print("[%6.2f] Halt at end of line."%t)
		break
	if posn + distance > cursection:
		# We'll reach the end of the section.
		# Grab the next section, and figure out at what exact time point we hit it.
		cross_time = t + (cursection - posn) / distance * advance
		print("[%6.2f] Enter next section (%dm speed %d)"%(cross_time, nextsection, int(nextspeed*3.6+.5)))
		posn -= cursection
		cursection, curspeed = nextsection, nextspeed
		nextsection, nextspeed = next(section)
	t += advance
	posn += distance
	speed += actual_accel * advance
	mode = nextmode

print("Final time:", t, "seconds - %d:%02d" % divmod(int(t), 60))
