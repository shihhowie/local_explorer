'''
{"type":"Feature",
"geometry":{"type":"Point","coordinates":[-0.0557508,51.5466126]},
"properties":{"id":"08f194e69a0cba1003f6576e4cfb876f",
"type":"place",
"version":0,
"sources":[{"property":"","dataset":"meta","record_id":"101332822166556","update_time":"2025-02-24T08:00:00.000Z","confidence":0.8941256830601093}],
"names":{"primary":"Omax It Solutions Ltd","common":null,"rules":null},
"categories":{"primary":"it_service_and_computer_repair","alternate":["professional_services","employment_agencies"]},
"confidence":0.8941256830601093,"websites":["http://www.omaxit.com/"],
"socials":["https://www.facebook.com/101332822166556"],
"phones":["+447710671945"],
"addresses":[{"freeform":"238 Graham Road","locality":"London","postcode":"E8 1BP","region":"ENG","country":"GB"}]}}
'''

import json
import os 
import argparse
import geohash2

parser = argparse.ArgumentParser(description="Process a GeoJSON file.")
parser.add_argument('-i', '--input_file', type=str, help="Path to the GeoJSON file to process")
parser.add_argument('-o', '--output_file', type=str, help="Path to the sql output to process")

args = parser.parse_args()

def get_geohash(coordinates):
    lat, lon = coordinates[1], coordinates[0]
    geohash_code = geohash2.encode(lat, lon, precision=8)
    return geohash_code

def parse_json(line):
    # line = line.replace("None", "NA")
    geojson = json.loads(line.strip().rstrip(','))
    coordinates = geojson['geometry']['coordinates']
    geohash_code = get_geohash(coordinates)
    placeid = geojson['properties']['id']
    names = geojson['properties']['names']['primary'].replace("'", "''")
    categories = json.dumps(geojson['properties']['categories']).replace("'", "''")
    websites = json.dumps(geojson['properties'].get('websites', [])).replace("'", "''")
    socials = json.dumps(geojson['properties'].get('socials', [])).replace("'", "''")
    address_obj = json.dumps(geojson['properties']['addresses'][0]).replace("'", "''")

    return f"('{placeid}','{coordinates}','{geohash_code}','{names}','{categories}','{websites}','{socials}','{address_obj}'),\n"

def process_geojson():
    fail_counter = 0
    with open(args.output_file, 'w') as output_file:
        output_file.write('''CREATE TABLE IF NOT EXISTS overture_map_places (
            id TEXT PRIMARY KEY,
            coordinates TEXT,
            geohash TEXT,
            names TEXT,
            categories TEXT,
            websites TEXT,
            socials TEXT,
            address TEXT
        );\n
        '''
        )
        output_file.write(f"INSERT INTO overture_map_places (id, coordinates, geohash, names, categories, websites, socials, address) VALUES \n")
        with open(args.input_file, 'r') as file:
            for line in file:
                try:
                    sql_line = parse_json(line)
                    output_file.write(sql_line)
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON line: {line.strip()}")  
                    fail_counter += 1
                    if fail_counter>10:
                        breaki 
            # handle last line
            line = line.rstrip("}").rstrip("]")
            sql_line = parse_json(line)
            output_file.write(sql_line.rstrip(",\n"))
            # output_file.write(f";\n")
            output_file.write(''' 
                    ON CONFLICT (id) DO UPDATE SET
                    coordinates = EXCLUDED.coordinates,
                    geohash = EXCLUDED.geohash,
                    names = EXCLUDED.names,
                    categories = EXCLUDED.categories,
                    websites = EXCLUDED.websites,
                    socials = EXCLUDED.socials,
                    address = EXCLUDED.address;
                ''')
            
if __name__ == "__main__":
    process_geojson()