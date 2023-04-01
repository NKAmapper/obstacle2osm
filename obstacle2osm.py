#!/usr/bin/env python3
# -*- coding: utf8

# obstacle2osm
# Converts aviation obstacles from Kartverket GML files for import/update in OSM
# Usage: obstacle2.osm <county> [-line]
# Option: "-line" to output power lines
# Creates gojson file with name "Luftfartshinder_" + county + ".osm"


import html
import time
import sys
import urllib.request
import json
import zipfile
from io import BytesIO
from xml.etree import ElementTree

#sys.path.append('../gml/')
import gml2osm
from gml2osm import message


version = "2.0.0"


# Tagging per obstacle type

tagging_table = {
	# Masts (NrlMast)
	'belysningsmast':		['man_made=mast', 'tower:type=lighting'],
	'lavspentmast':			['highway=street_lamp'],	
	'ledningsmast':			['power=pole'],
	'målemast':				['man_made=mast', 'tower:type=monitoring'],
	'radiomast':			['man_made=antenna'],
	'taubanemast':			['aerialway=pylon'],
	'telemast':				['man_made=mast', 'tower:type=communication'],

	# Points (NrlPunkt)
	'bygning':				['building=yes'],
	'flaggstang':			['man_made=flagpole'],
	'forankretBallong':		[],
	'fornøyelsesparkinnretning':	['man_made=tower'],
	'fyrtårn':				['man_made=lighthouse'],
	'hopptårn':				['man_made=tower', 'piste:type=ski_jump'],
	'kjøletårn':			['man_made=tower', 'tower_type=cooling'],
	'kontrolltårn':			['man_made=tower', 'tower:type=airport_control'],
	'kraftverk':			['power=plant'],
	'kran':					['man_made=crane'],
	'kuppel':				['man_made=tower', 'tower:construction=dome'],
	'monument':				['man_made=tower', 'tower:type=monument'],
	'navigasjonshjelpemiddel':	['aeroway=navigationaid'],
	'petroleumsinnretning':	[],
	'pipe':					['man_made=chimney'],
	'raffineri':			['man_made=tower'],
	'silo':					['man_made=silo'],
	'sprengningstårn':		[],
	'tank':					['man_made=storage_tank'],
	'tårn':					['man_made=tower'],
	'vanntårn':				['man_made=storage_tank', 'content=water'],
	'vindturbin':			['power=generator', 'generator:source=wind', 'generator:method=wind_turbine', 'generator:type=horizontal_axis'],

	# Lines (NrlLinje)
	'bru':					['man_made=bridge'],
	'demning':				['waterway=dam'],
	'gjerde':				['barrier=fence'],

	# Aerial lines (NrlLuftspenn)
	'bardun':				['man_made=guy'],
	'gondolbane':			['aerialway=gondola'],	
	'ledning':				['power=line'],
	'løypestreng':			['aerialway=goods'],
	'skitrekk':				['aerialway=draglift'],
	'stolheis':				['aerialway=chairlift'],
	'taubane':				['aerialway=cable_car'],
	'vaier':				['man_made=guy'],
	'zipline':				['aerialway=zip_line'],

	# Flate (NrlFlate)
	'kontaktledning':		['railway=rail'],
	'transformatorstasjon':	['power=substation', 'power=transformer'],

	# Other
	'annet':				[]
}



# Determine obstacle type

def get_obstacle_type(obstacle):

	for object_type in ["punkt", "mast", "luftspenn", "linje", "flate"]:
		if object_type + "Type" in obstacle:
			return obstacle[ object_type + "Type" ]
	return None



# Tag obstacle

def tag_obstacle(feature):

	obstacle = feature['data']
	tags = {}
	obstacle_type = get_obstacle_type(obstacle)

	# Name and id

	if "navn" in obstacle:
		name = obstacle['navn']
		if name == name.upper():
			name = name.title()
		if name and not ("luftfartshinderId" in obstacle and name == obstacle['luftfartshinderId']):
			tags['description'] = name

	tags['OBSTACLE_TYPE'] = obstacle_type
	tags['STATUS'] = obstacle['status']

	if "luftfartshinderId" in obstacle:
		tags['ref:hinder'] = obstacle['luftfartshinderId']

	# Height/elevation, coordinates

	height = None
	if "vertikalAvstand" in obstacle:
		height = float(obstacle['vertikalAvstand'])
		tags['height'] = "%i" % height

	if feature['type'] == "Point":
		z = feature['coordinates'][2]
		feature['coordinates'] = ( feature['coordinates'][0], feature['coordinates'][1] )  # Strip z
	else:
		z = max(point[2] for point in feature['coordinates'])  # List
		feature['coordinates'] = [ ( point[0], point[1] ) for point in feature['coordinates']]

	top_ele = None
	if "høydereferanse" in obstacle:
		if obstacle['høydereferanse'] == "topp":
			if height is not None:
				z = z - height
			else:
				top_ele = z
				z = None

	if z:
		tags['ele'] = "%i" % z
	elif top_ele:
		tags['top_ele'] = "%i" % top_ele

	# Dates

	if "datafangstdato" in obstacle:
		tags['DATE_SURVEY'] = obstacle['datafangstdato'][:10]

	if "registreringsdato" in obstacle:
		tags['DATE_CREATE'] = obstacle['registreringsdato'][:10]

	if "oppdateringsdato" in obstacle:
		tags['DATE_UPDATE'] = obstacle['oppdateringsdato'][:10]

	# Feature tagging (man_made, tower:type etc)

	if obstacle_type in tagging_table:
		for tag in tagging_table[ obstacle_type ]:
			tag_split = tag.split("=")
			tags[ tag_split[0] ] = tag_split[1]
	else:
		message ("Object type '%s' not found in tagging table\n" % obstacle_type)

	# Light tagging

	if "luftfartshinderlyssetting" in obstacle:

		light = obstacle['luftfartshinderlyssetting']

		tags['aeroway:light'] = "obstacle"  # Only light tag if type is "lyssatt"

		if light in ['blinkendeRødt','fastRødt','lavintensitetTypeA','lavintensitetTypeB','mellomintensitetTypeB','mellomintensitetTypeC']:
			tags['aeroway:light:colour'] = "red"
		elif light in ['blinkendeHvitt','fastHvitt','mellomintensitetTypeA','høyintensitetTypeA','høyintensitetTypeB']:
			tags['aeroway:light:colour'] = "white"

		if light in ['fastRødt','fastHvitt','lavintensitetTypeA','lavintensitetTypeB','mellomintensitetTypeC']:
			tags['aeroway:light:character'] = "fixed"
		elif light in ['blinkendeRødt','blinkendeHvitt','mellomintensitetTypeA','mellomintensitetTypeB','høyintensitetTypeA','høyintensitetTypeB']:
			tags['aeroway:light:character'] = "flashing"
		elif light == "belystMedFlomlys":
			tags['aeroway:light:character'] = "floodlight"

		if "lavintensitet" in light:
			tags['aeroway:light:intensity'] = "low"
		elif "mellomintensitet" in light:
			tags['aeroway:light:intensity'] = "medium"
		elif "høyintensitet" in light:
			tags['aeroway:light:intensity'] = "high"

		if "TypeA" in light:
			tags['aeroway:light:icao_type']  = "A"
		elif "TypeB" in light:
			tags['aeroway:light:icao_type']  = "B"
		elif "TypeC" in light:
			tags['aeroway:light:icao_type']  = "C"

	return tags



# Combine connected lines 

def combine_lines(line_groups):

	# Connect power lines

	lines = []

	for group, segments in iter(line_groups.items()):
		remaining = segments[:]
		new_line = []

		while remaining:
			next_feature = remaining.pop()
			new_line = next_feature['coordinates'][:]

			min_ele = min(point[2] for point in next_feature['coordinates'])
			max_ele = max(point[2] for point in next_feature['coordinates'])
			if "vertikalAvstand" in next_feature['data']:
				min_height = float(next_feature['data']['vertikalAvstand'])
				max_height = float(next_feature['data']['vertikalAvstand'])
				no_height = False
			else:
				min_height = 9999
				max_height = -9999
				no_height = True

			if "høydereferanse" in next_feature['data']:
				ele_reference = next_feature['data']['høydereferanse']
				no_reference = False
			else:
				ele_reference = ""
				no_reference = True

			found = True

			while remaining and found and not ("luftspennType" in next_feature['data'] and next_feature['data']['luftspennType'] == "bardun"):
				found = False
				new_line_set = set({new_line[0], new_line[-1]})
				for i, segment in enumerate(remaining[:]):
					if new_line_set.intersection(segment['coordinates']):

						# Match without z coordinate, which in rare cases might differ
						if segment['coordinates'][0] == new_line[-1]:
							new_line.extend(segment['coordinates'][1:])
						elif segment['coordinates'][-1] == new_line[-1]:
							new_line.extend(list(reversed(segment['coordinates']))[1:])
						elif segment['coordinates'][-1] == new_line[0]:
							new_line = segment['coordinates'] + new_line[1:]
						elif segment['coordinates'][0] == new_line[0]:
							new_line = list(reversed(segment['coordinates'])) + new_line[1:]

						min_ele = min(min_ele, min(point[2] for point in segment['coordinates']))
						max_ele = max(max_ele, max(point[2] for point in segment['coordinates']))
						if "vertikalAvstand" in segment['data']:
							min_height = min(min_height, float(segment['data']['vertikalAvstand']))
							max_height = max(max_height, float(segment['data']['vertikalAvstand']))
						else:
							no_height = True
						if "høydereferanse" not in segment['data'] or segment['data']['høydereferanse'] != ele_reference:
							no_reference = True

						del remaining[i]
						found = True
						break

			tags = {}
			if not no_height and min_height == max_height:
				tags['height'] = "%i" % min_height
			if not no_reference and min_ele == max_ele:
				if ele_reference == "topp":
					if not no_height and min_height == max_height:
						tags['ele'] = "%i" % (min_ele - min_height)
					else:
						tags['top_ele'] = "%i" % min_ele
				else:
					tags['ele'] = "%i" % min_ele

			new_feature = {
				'object': next_feature['object'],
				'type': 'LineString',
				'data': next_feature['data'],
				'tags': tags,
				'coordinates': new_line
			}
			lines.append(new_feature)

	return lines



# Create collection of obstacles, excluding power lines and power masts

def create_obstacles(features):

	line_groups = {}
	obstacle_points = []
	last_date = ""

	# Find all point obstacles

	for feature in features:
		obstacle = feature['data']
		obstacle_type = get_obstacle_type(obstacle)

		if obstacle['status'] in ["eksisterende", "planlagtOppført"] and obstacle_type not in ["ledning", "ledningsmast"]:
			if feature['type'] == "Point":
				feature['tags'] = tag_obstacle(feature)
				obstacle_points.append(feature)

			else:
				ref = obstacle_type
				if "luftfartshinderId" in feature:
					ref += obstacle['luftfartshinderId'].strip()
				if ref not in line_groups:
					line_groups[ ref ] = []
				line_groups[ ref ].append(feature)
				
			last_date = max(last_date, obstacle['oppdateringsdato'])

	# Concatenate features from same id
	obstacle_lines = combine_lines(line_groups)

	for line in obstacle_lines:
		tags = tag_obstacle(line)
		for key in ['ele', 'top_ele', 'height']:
			if key in tags:
				del tags[ key ]
		line['tags'].update(tags)  # Keep existing ele/height tags

	message ("\t%i obstacle lines, %i points\n" % (len(obstacle_lines), len(obstacle_points)))
	message ("\tLast update: %s\n" % last_date[:10])

	return obstacle_points + obstacle_lines



# Create network of power lines including pylons

def create_powerlines(features):

	# Sort all lines according to name

	message ("Combine power lines ...\n")

	line_groups = {}
	power_masts = []
	last_date = ""

	for feature in features:
		obstacle = feature['data']
		obstacle_type = get_obstacle_type(obstacle)

		if obstacle['status'] in ["eksisterende", "planlagtOppført"]:
			if obstacle_type == "ledning":
				name = ""
				if "navn" in obstacle:
					name = obstacle['navn'].strip()

				if name not in line_groups:
					line_groups[ name ] = []

				line_groups[ name ].append(feature)
				last_date = max(last_date, obstacle['oppdateringsdato'])

			elif obstacle_type == "ledningsmast":
				feature['tags'] = tag_obstacle(feature)
				tags = {}
				for key, value in iter(feature['tags'].items()):
					if key in ["power", "height", "ele", "top_ele"] or "light" in key:  # Only most important tags
						tags[ key ] = value

				feature['tags'] = tags
				power_masts.append(feature)
				last_date = max(last_date, obstacle['oppdateringsdato'])

	power_lines = combine_lines(line_groups)

	for line in power_lines:
		line_name = ""
		if "navn" in line['data']:
			line_name = line['data']['navn']
		if "luftfartshinderId" in line['data'] and line_name == line['data']['luftfartshinderId']:
			line_name = ""
		if line_name == line_name.upper():
			line_name = line_name.title()

		line['tags'] = {
			'power': 'line',
			'name': line_name,
			'STATUS': line['data']['status'],
			'OBSTACLE_TYPE': line['data']['luftspennType']
		}

		for key in [("DATE_SURVEY", "datafangstdato"), ("DATE_CREATE", "registreringsdato"), ("DATE_UPDATE", "oppdateringsdato")]:
			if key[1] in line['data']:
				line['tags'][ key[0] ] = line['data'][ key[1] ][:10]

	message ("\t%i power lines, %i masts\n" % (len(power_lines), len(power_masts)))
	message ("\tLast update: %s\n" % last_date[:10])

	return power_masts + power_lines



# Main program

if __name__ == '__main__':

	message ("\n--- obstacle2osm ---\n")

	# Load county id's and names from Kartverket api

	if len(sys.argv) > 1 and "-" not in sys.argv[1]:
		gml2osm.load_municipalities(area_filter="county")
		county = gml2osm.get_municipality(sys.argv[1])
		if county is None:
			sys.exit("*** County '%s' not found\n\n" % sys.argv[1])
		else:
			county_id, county_name = county
	else:
		county_id = "0000"
		county_name = "Norge"  # Default

	message ("Area: %s\n" % county_name)

	# Load obstacle gml from GeoNorge, process and output

	county_name = gml2osm.clean_url(county_name)
	url = "https://nedlasting.geonorge.no/geonorge/Samferdsel/Luftfartshindre/GML/Samferdsel_%s_%s_4258+3855_Luftfartshindre_GML.zip" % \
			 (county_id, county_name)
	out_filename = gml2osm.clean_url("luftfartshindre_%s_%s.geojson" % (county_id[:2], county_name))

	if "-line" in sys.argv or "-power" in sys.argv:
		features = gml2osm.load_gml(url, object_filter=["NrlMast", "NrlLuftspenn"], elevations=True, verbose=True)
		features = create_powerlines(features)
		out_filename = out_filename.replace(".geojson", "") + "_powerlines.geojson"
	else:
		features = gml2osm.load_gml(url, elevations=True, verbose=True)
		features = create_obstacles(features)

	gml2osm.save_geojson(features, out_filename, verbose=True)

	message ("\n")
