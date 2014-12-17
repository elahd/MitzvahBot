###############
# DEPENDENCIES
# Needs pyserial, nap, python-dateutil, python-twitter. Use pip to install.
###############

import serial # For serial communication
import serial.tools.list_ports # For spitting out list of ports when Arduino connection fails.
import time # For sleeping
import requests # For processing geocode results
import re # Regex processing
import twitter # Tweeting
from datetime import datetime, timedelta # Convering strings to datetimes, date arithmetic
from nap.url import Url # For Hebcal & Geonames API requests

###############
# VARIABLES
###############

# USER CONFIGURABLE VARIABLES. SET BEFORE RUNNING.
cfg_zipcode = 'ENTER ZIPCODE' # Your United States zipcode. No support for international locations.
cfg_geonames_username = 'ENTER GEONAMES API USERNAME' # Username for geonames.org API.
cfg_twitter = twitter.Api(consumer_key='GET FROM APP.TWITTER.COM',
                      consumer_secret='GET FROM APP.TWITTER.COM',
                      access_token_key='GET FROM APP.TWITTER.COM',
                      access_token_secret='GET FROM APP.TWITTER.COM') # Register your own Twitter app at https://apps.twitter.com/. Twitter will provide these API keys.
cfg_arduino_port = 'ENTER PORT NAME' # Your arduino serial port name. Example: /dev/ttyACM0.
cfg_lighting_offet = 10 # Light candles this many minutes after sunset.
cfg_extinguish_after = 4 # Extinguish candles this many hours after they were lit.

# Debugging variables. Modify as needed.
cfg_debug = False # If True, candle lighting will start 30 seconds from execution now and increment every few seconds seconds.
cfg_debug_noarduino = False # If True, we'll skip communicating with the Arduino. Useful for debugging non-Arduino components on this script.
cfg_debug_notalking = False # If True, tweets will be displayed on console instead of Twitter.

# Internal variables. Do not modify.
dev_arduino = None
cfg_latitude = None
cfg_longitude = None
var_lighting_times = []
var_chanukah_over = False
var_last_night_lit = 0
var_current_night = 0
var_candles_lit = False
var_bracha_all_nights_a = 'Baruch atah adonai eloheinu melech haolam asher kideshanu bemitzvotav vetzivanu lehadlik ner Chanukah.'
var_bracha_all_nights_b = 'Baruch atah adonai eloheinu melech haolam sheasa nisim laavoteinu bayamim haheim bizman hazeh.'
var_bracha_first_night = 'Baruch atah adonai eloheinu melech haolam shehechiyanu vekiyimanu vehigianu lizman hazeh.'

# Custom exceptions
class RemoteFetchError(Exception): pass
class TwitterError(Exception): pass
class CommError(Exception): pass
class ProcessError(Exception): pass

###############
# FUNCTIONS
###############

def sendToArduino (command, device=None):
	if cfg_debug_noarduino is True:
		return

	if device is None:
		device = dev_arduino

	# Try to send command 5 times.
	# We don't want exceptions to derail this loop since we need it to try multiple times.
	# We'll track exceptions in a variable and will raise if the loop exits on failure.
	exception = None
	for times_tried in range(0,5):
		try:
			device.write('<')
			device.write(str(command))
			device.write('>')
		except IOError:
			print "Couldn't write to Arduino on try number " + str(times_tried + 1)
			exception = CommError("Couldn't write to Arduino. Response was %s")
			continue

		time.sleep(2) # Give arduino time to respond with an ACK

		# Check that Arduino returned ACK with sent command.
		response = None
		try:
			response = device.readline()
		except IOError:
			print "Couldn't read from Arduino on try number " + str(times_tried + 1)
			exception = CommError("Couldn't read from Arduino. Response was %s" % e)
			continue

		pattern = re.compile("\<ACK\:" + command + "\>\r\n$")

		if pattern.match(response) is None:
			raise CommError("Unexpected or no ACK from Arduino. Returned data was %s" % response)
			continue
		else:
			break

	if exception is not None:
		raise exception
	else:
		return

def lightCandles(night):
	# If we get a night number, light candles.
	if (night >= 1) and (night <= 8):
		try:
			sendToArduino('10') # Light shamash

			bracha_a = var_bracha_all_nights_a + ' #night' + str(night)
			bracha_b = var_bracha_all_nights_b + ' #night' + str(night)

 			# Say brachot
			tweet(cfg_twitter, bracha_a)
			tweet(cfg_twitter, bracha_b)
			if (night == 1):
				tweet(cfg_twitter, var_bracha_first_night)

			# Light candles
			sendToArduino(str(night))
			return
		except CommError as e:
			raise ProcessError("Issue sending light candles command to Arduino.\n%s" % e)
			return
		except RemoteFetchError as e:
			raise ProcessError("Issue saying bracha.\n%s" % e)
			return
	else:
		raise ProcessError("Invalid light candles command. Received command %s" % night)
		return

def extinguishCandles():
	try:
		sendToArduino('9')
	except CommError as e:
		raise ProcessError("Could not send extinguish command to Arduino.")
		return

def getLatLong (p_zipcode):
	# Get lat and long from zipcode using geocoder.us.
	try:
		geodata = requests.get('http://geocoder.us/service/csv/geocode?zip=' + p_zipcode) #returns lat, long, city, st, zip
	except requests.exceptions.RequestException as e:
		raise RemoteFetchError("Completely failed to get data from Geocoder. Response was %s" % e)
	else:
		var_geodata = geodata.content.split(',')

	# Make sure we got data that looks like lat/long. Should probably use a regex for this.
	try:
		isinstance(var_geodata[0], (long, int))
		isinstance(var_geodata[1], (long, int))
	except TypeError:
		raise RemoteFetchError("Got bad coordinate data from Geocoder. Response was %s" % e)
	else:
		print ('Using US zipcode ' + p_zipcode + ', located at ' + var_geodata[0] + ',' + var_geodata[1] + '.')
		return var_geodata[0], var_geodata[1]

def getLightingTimes (p_zipcode, p_latitude, p_longitude, p_lightingOffset):
	# Get all holidays for current year from hebcal.com
	try:
		api_hebcal = Url('http://www.hebcal.com/')
		response_hebcal = api_hebcal.get('hebcal',
			params={
				'v': '1'
				,'cfg': 'json'
				,'nh': 'on'
				,'nx': 'off'
				,'year': 'now'
				,'month': 'x'
				,'ss': 'off'
				,'mf': 'off'
				,'c': 'on'
				,'zip': p_zipcode
				,'m': '0'
				,'s': 'off'
			})
	except requests.exceptions.HTTPError as e:
	    raise RemoteFetchError("Completely failed to get data from Hebcal. Response was %s" % e)
	    return
	else:
		obj_holidays = response_hebcal.json();

	candle_lighting = []
	# Find all nights of Chanukah (by searching holiday titles)...
	# print 'Candle lighting schedule:'
	for obj_holiday in obj_holidays['items']:
		if re.match('^Chanukah[a-zA-Z0-9_: ]*Candle[s]?$', obj_holiday['title']):
			# ...and get sunset times for those nights from geonames.
			try:
				api_geonames = Url('http://api.geonames.org/')
				response_geonames = api_geonames.get('timezoneJSON', params={
						'lat': p_latitude
						,'lng': p_longitude
						,'date': obj_holiday['date']
						,'username': cfg_geonames_username
					})
			except requests.exceptions.HTTPError as e:
			    raise RemoteFetchError("Completely failed to get sunset data from Geonames. Response was %s" % e)
			    return
			else:
				# Status indicates that Geonames is returning an error.
				if 'status' in response_geonames.json():
					raise RemoteFetchError("Geonames returned an error message. Response was %s" % (response_geonames.json()['status'] + '\n' + params_used))
					return
				else:
					# Store candle lighting time, calculated by adding p_lightingOffset to sunset time.
					datetime_sunset = datetime.strptime(response_geonames.json()['dates'][0]['sunset'], '%Y-%m-%d %H:%M')
					lighting_time = datetime_sunset + timedelta(minutes=p_lightingOffset)
					candle_lighting.append(lighting_time)
					# print lighting_time
	return candle_lighting

def tweet (api, message):
	#https://github.com/bear/python-twitter
	try:
		if cfg_debug_notalking is True:
			print "DEBUG TWEET: " + message
			return
		else:
			api.PostUpdate(message)
			return
	except Exception as e:
		raise RemoteFetchError("Failed to tweet. Response was %s" % e)

###############
# CONTROLLER
###############

def main():
	global var_candles_lit
	global var_current_night
	global cfg_extinguish_after
	global var_last_night_lit
	global dev_arduino
	global cfg_latitude
	global cfg_longitude
	global cfg_zipcode
	global cfg_lighting_offet
	global var_lighting_times

	###############
	# SETUP
	###############

	# Open serial connection to Arduino

	if cfg_debug_noarduino is False:
		try:
			dev_arduino = serial.Serial(port=cfg_arduino_port, baudrate=9600)
		except Exception:
			print ('Failed to connect to Arduino on port ' + cfg_arduino_port + '. Exiting.')
			print ('Available ports are:')
			print(list(serial.tools.list_ports.comports()))
			print ('Update your cfg_arduino_port setting.')
			exit()
		
		print ("Connected to Arduino on port " + cfg_arduino_port + "\n")

		time.sleep(2) # Arduino hangs after opening serial port. Wait for port to settle.

	# Get lighting times
	if cfg_debug is True:
		for index in range(0,8):
			var_lighting_times.append(datetime.now() + timedelta(seconds=(16*index)))
	else:
		try:
			cfg_latitude, cfg_longitude = getLatLong(cfg_zipcode)
			var_lighting_times = getLightingTimes(cfg_zipcode, cfg_latitude, cfg_longitude, cfg_lighting_offet)
		except RemoteFetchError as e:
			print ("%s.\nFailed to initialize dates. Exiting." % e)
			exit()

	# Print lighting schedule

	print ("** CANDLE LIGHTING SCHEDULE **")

	for i, lighting_time in enumerate(var_lighting_times):
		print "Night " + str(i+1) + ": " + lighting_time.strftime("%B %d, %Y at %I:%M %p")

	###############
	# MAIN LOOP
	###############

	while True:
		# Main program loop here

		# Light candles as needed.
		if var_candles_lit is False:
			# Starts chanukah at first lighting time.
			if (datetime.now() >= var_lighting_times[0]) and (var_last_night_lit == 0):
				var_current_night = 1
			# If it's lighting time and we haven't lit candles, light candles
			if (datetime.now() >= var_lighting_times[var_current_night-1]) and (var_last_night_lit < var_current_night):
				try:
					lightCandles(var_current_night)
					print ("Lit candles for night " + str(var_current_night) + ".")
					var_last_night_lit = var_current_night
					var_candles_lit = True
				except ProcessError as e:
					print "Failed to light candles. Errors were:\n%s.\nExiting." % e
					exit()

		# Extinguishes candles as needed.
		if var_candles_lit is True:
			# If we've reached turn off time
			if (
				((cfg_debug is False) and datetime.now() >= (var_lighting_times[var_current_night-1]+timedelta(hours=cfg_extinguish_after)))
				or ((cfg_debug is True) and datetime.now() >= (var_lighting_times[var_current_night-1]+timedelta(seconds=5)))
				):
				try:
					extinguishCandles()
					print "Candles for night " + str(var_current_night) + " blew out."
					var_current_night += 1
					var_candles_lit = False
				except ProcessError as e:
					print "Failed to extinguish candles. Errors were:\n%s.\nExiting." % e
					exit()

		# Exit if Chanukah is over
		if var_current_night is 9:
			print "Chanukah is over. Exiting."
			exit()

main()