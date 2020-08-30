#!/usr/bin/env python
# -*- coding: utf8

# obstacle2osm
# Converts aviation obstacles from Kartverket WFS/GML files for import/update in OSM
# Usage: obstacle2.osm [county] (county "00" is all of Norway)
# Creates OSM file with name "Luftfartshinder_" + county + ".osm"


import cgi
import time
import sys
import urllib2
import json
import zipfile
import StringIO
from xml.etree import ElementTree
import utm  # Local library


version = "0.1.0"


# Tagging per obstacle type

tagging_table = {
	'Landbruksutstyr':		[],
	'Telemast':				['man_made=mast', 'tower:type=communication'],
	'Bru':					['man_made=tower', 'tower:type=bridge'],
	'Bygning':				['building=yes'],
	'Gondolbane':			['aerialway=gondola'],
	u'Kontrolltårn':		['man_made=tower', 'tower:type=airport_control'],
	u'Kjøletårn':			['man_made=tower', 'tower_type=cooling'],
	'Kran':					['man_made=crane'],
	'Demning':				['waterway=dam'],	
	'Kuppel':				['man_made=tower', 'tower:construction=dome'],
	'EL_Nettstasjon':		['power=substation', 'power=transformer'],
	'Gjerde':				['barrier=fence'],
	u'Fyrtårn':				['man_made=lighthouse'],
	'Monument':				['man_made=tower', 'tower:type=monument'],
	'Terrengpunkt':			['natural=peak'],
	'Navigasjonshjelpemiddel':	['aeroway=navigationaid'],
	'Stolpe':				['man_made=mast'],
	'Kraftverk':			['power=plant'],
	'Raffineri':			['man_made=tower'],
	'Oljerigg':				[],
	'Skilt':				[],
	'Pipe':					['man_made=chimney'],
	'Tank':					['man_made=storage_tank'],
	'Forankret ballong':	[],
	u'Tårn':				['man_made=tower'],
	'Kraftledning':			[],
	'Tre':					['natural=tree'],
	u'Skogsområde':			['natural=wood'],
	u'Vanntårn':			['man_made=storage_tank', 'content=water'],
	u'Vindmølle':			['power=generator', 'generator:source=wind', 'generator:method=wind_turbine', 'generator:type=horizontal_axis'],
	u'Vindmøllepark':		['type=site', 'power=plant', 'plant:source=wind'],
	u'Hopptårn':			['man_made=tower', 'piste:type=ski_jump'],
	u'Vindmåler':			['man_made=mast', 'tower:type=monitoring'],
	'Lysmast':				['man_made=mast', 'tower:type=lighting'],
	'Flaggstang':			['man_made=flagpole'],
	'Petroleumsinnretning':	[],
	'Silo':					['man_made=silo'],
	'Stolheis':				['aerialway=chairlift'],
	'Skitrekk':				['aerialway=draglift'],
	'Taubane':				['aerialway=cable_car'],
	u'Fornøyelsesparkinnretning':	['man_made=tower'],
	'Annet':				[]
}

# Namespace

ns_gml = 'http://www.opengis.net/gml/3.2'
ns_xlink = 'http://www.w3.org/1999/xlink'
ns_app = 'http://skjema.geonorge.no/SOSI/produktspesifikasjon/Luftfartshindre/20180322'

ns = {
		'gml': ns_gml,
		'xlink': ns_xlink,
		'app': ns_app
}


# Produce a tag for OSM file

def make_osm_line(key,value):
    if value:
		encoded_value = cgi.escape(value.encode('utf-8'),True).strip()
		file_out.write ('    <tag k="%s" v="%s" />\n' % (key, encoded_value))


# Main program

if __name__ == '__main__':

	start_time = time.time()
	today = time.strftime("%Y-%m-%d", time.localtime())

	# Load county id's and names from Kartverket api

	file = urllib2.urlopen("https://ws.geonorge.no/kommuneinfo/v1/fylker")
	county_data = json.load(file)
	file.close()

	county = {}
	for coun in county_data:
		county[coun['fylkesnummer']] = coun['fylkesnavn'].strip()
	county['21'] = "Svalbard"
	county['00'] = "Norge"

	# Load obstacle gml from GeoNorge

	if (len(sys.argv) > 1) and (sys.argv[1] in county):
		county_id = sys.argv[1]
		county_name = county[county_id].replace(u"Ø", "O").replace(u"ø", "o").replace(" ", "_")
		if county_id == "21":
			county_id = "2100"  # Svalbard
		elif county_id == "00":
			county_id = "0000"  # Norway
	else:
		sys.exit ("County code not found")

	print ("Loading %s..." % county_name)

	url = "https://nedlasting.geonorge.no/geonorge/Samferdsel/Luftfartshindre/GML/Samferdsel_%s_%s_6173_Luftfartshindre_GML.zip" % (county_id, county_name)

	in_file = urllib2.urlopen(url)
	zip_file = zipfile.ZipFile(StringIO.StringIO(in_file.read()))
	filename = zip_file.namelist()[0]
	file = zip_file.open(filename)

	tree = ElementTree.parse(file)
	file.close()

	root = tree.getroot()
	feature_collection = root

	obstacles = []

	# Pass 1:
	# Find all point obstacles (excluding lines)

	for feature_member in feature_collection.iter('{%s}featureMember' % ns_gml):

		vertical_object = feature_member.find('app:VertikalObjekt', ns)
		if vertical_object != None:

			xlink = vertical_object.find(u'app:bestårAvVertikalobjKompPunkt', ns)
			status = vertical_object.find('app:status', ns).text
			valid_date = vertical_object.find('app:gyldigTil', ns)

			if (xlink != None) and (status in ["E", "P"]) and ((valid_date == None) or (valid_date.text > today)):

				xlink_ref = xlink.get('{%s}href' % ns_xlink)

				update_date = vertical_object.find('app:oppdateringsdato', ns).text[:10]
				name = vertical_object.find('app:vertikalObjektNavn', ns).text
				object_id = vertical_object.find('app:identifikasjonObjekt/app:IdentifikasjonObjekt/app:lokalId', ns).text
				object_type = vertical_object.find('app:vertikalObjektType', ns).text

				obstacle = {
					'status': status,
					'date_update': update_date,
					'type': object_type,
					'name': name,
					'ref:hinder': object_id,
					'xlink': xlink_ref
				}

				create_date = vertical_object.find('app:datafangstdato', ns)
				if create_date != None:
					obstacle['date_create'] = create_date.text[:10]

				if valid_date != None:
					obstacle['date_valid'] = valid_date.text[:10]

				obstacles.append(obstacle)

	# Pass 2:
	# Find obstacle coordinates

	print ("Matching coordinates for %i obstacles..." % len(obstacles))

	for feature_member in feature_collection.iter('{%s}featureMember' % ns_gml):

		point = feature_member.find('app:VertikalObjektKomponentPunkt', ns)
		if point != None:

			point_id = point.get('{%s}id' % ns_gml)

			for obstacle in obstacles:
				if obstacle['xlink'] == point_id:

					coordinates = point.find('app:posisjon/gml:Point/gml:pos', ns).text
					coordinates_split = coordinates.split(" ")
					x = float(coordinates_split[0])
					y = float(coordinates_split[1])
					z = float(coordinates_split[2])

					latitude, longitude = utm.UtmToLatLon(x, y, 33, "N")

					obstacle['latitude'] = latitude
					obstacle['longitude'] = longitude

					height = point.find('app:vertikalUtstrekning', ns)
					if height != None:
						height = float(height.text)
						obstacle['height'] = "%.0f" % height

					z_ref = point.find('app:href', ns).text
					top_ele = None

					if z_ref == "TOP":
						if height != None:
							z = z - height
						else:
							top_ele = z
							z = None

					if z:
						if z == round(z,0):
							obstacle['ele'] = "%.0f" % z
						else:
							obstacle['ele'] = "%.1f" % z
					elif top_ele:
						if top_ele == round(top_ele,0):
							obstacle['top_ele'] = "%.0f" % top_ele
						else:
							obstacle['top_ele'] = "%.1f" % top_ele

					light = point.find('app:lyssetting', ns).text

					obstacle['light'] = light

					break

	# Pass 3:
	# Output file

	filename = "Luftfartshindre_" + county_name + ".osm"
	print ("Writing file '%s'..." % filename)
	file_out = open(filename, "w")

	file_out.write ('<?xml version="1.0" encoding="UTF-8"?>\n')
	file_out.write ('<osm version="0.6" generator="obstacle2osm v%s">\n' % version)

	node_id = -1000

	for obstacle in obstacles:

		node_id -= 1
		file_out.write ('  <node id="%i" lat="%f" lon="%f">\n' % (node_id, obstacle['latitude'], obstacle['longitude']))

		name = obstacle['name']
		if name == obstacle['ref:hinder']:
			name = ""
		elif name == name.upper():
			name = name.title()

		make_osm_line ("ref:hinder", obstacle['ref:hinder'])
		make_osm_line ("description", name)

		make_osm_line ("OBSTACLE_TYPE", obstacle['type'])
		make_osm_line ("STATUS", obstacle['status'])

		if "height" in obstacle:
			make_osm_line ("height", obstacle['height'])

		if "ele" in obstacle:
			make_osm_line ("ele", obstacle['ele'])
		elif "top_ele" in obstacle:
			make_osm_line ("top_ele", obstacle['top_ele'])

		if not("date_create" in obstacle) or (obstacle['date_update'] != obstacle['date_create']):
			make_osm_line ("DATE_UPDATE", obstacle['date_update'])

		if "date_create" in obstacle:
			make_osm_line ("DATE_CREATE", obstacle['date_create'])

		if "date_valid" in obstacle:
			make_osm_line ("end_date", obstacle['date_valid'])

		# Feature tagging (man_made, tower:type etc)

		tag_found = False
		for object_type, tags in tagging_table.iteritems():
			if object_type == obstacle['type']:
				for tag in tags:
					tag_split = tag.split("=")
					make_osm_line (tag_split[0], tag_split[1])
				tag_found = True
				break

		if not(tag_found):
			print ("Object type '%s' not found in tagging table " % obstacle['type'])

		# Light tagging

		light = obstacle['light']

		if not(light in ['IL', 'UKJ']):

			colour = ""
			character = ""
			intensity = ""
			icao_type = ""

			make_osm_line ("aeroway:light", "obstacle")

			if light in ['BR','FR','LIA','LIB','MIB','MIC']:
				colour = "red"
			elif light in ['BH','FH','MIA','HIA','HIB']:
				colour = "white"
			make_osm_line ("aeroway:light:colour", colour)

			if light in ['FR','FH','LIA','LIB','MIC']:
				character = "fixed"
			elif light in ['BR','BH','MIA','MIB','HIA','HIB']:
				character = "flashing"
			elif light == "FLO":
				character = "floodlight"
			make_osm_line ("aeroway:light:character", character)

			if light in ['LIA','LIB']:
				intensity = "low"
			elif light in ['MIA','MIB','MIC']:
				intensity = "medium"
			elif light in ['HIA','HIB']:
				intensity = "high"
			make_osm_line ("aeroway:light:intensity", intensity)

			if light in ['LIA','MIA','HIA']:
				icao_type = "A"
			elif light in ['LIB','MIB','HIB']:
				icao_type = "B"
			elif light == "HIC":
				icao_type = "C"
			make_osm_line ("aeroway:light:icao_type", icao_type)

		file_out.write ('  </node>\n')

	# Wrap up

	file_out.write ('</osm>\n')
	file_out.close()

	print ("Done in %i seconds" % (time.time() - start_time))
