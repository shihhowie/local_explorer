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

parser = argparse.ArgumentParser(description="Process a GeoJSON file.")
parser.add_argument('-i', '--input_file', type=str, help="Path to the GeoJSON file to process")
parser.add_argument('-o', '--output_file', type=str, help="Path to the sql output to process")

args = parser.parse_args()

def parse_json(line):
    # line = line.replace("None", "NA")
    geojson = json.loads(line.strip().rstrip(','))
    coordinates = geojson['geometry']['coordinates']
    placeid = geojson['properties']['id']
    names = geojson['properties']['names']['primary']
    categories = json.dumps(geojson['properties']['categories'])
    websites = json.dumps(geojson['properties'].get('websites', []))
    socials = json.dumps(geojson['properties'].get('socials', []))
    address_obj = json.dumps(geojson['properties']['addresses'][0])

    return f"VALUES ('{placeid}','{coordinates}','{names}','{categories}','{websites}','{socials}','{address_obj}'),\n"

def process_geojson():
    fail_counter = 0
    with open(args.output_file, 'w') as output_file:
        output_file.write('''CREATE TABLE IF NOT EXISTS overture_map_places (
            id SERIAL PRIMARY KEY,
            coordinates TEXT,
            names TEXT,
            categories TEXT,
            websites TEXT,
            socials TEXT,
            address TEXT
        );\n
        '''
        )
        output_file.write(f"INSERT INTO overture_map_places (placeid, coordinates, names, categories, websites, socials, address) \n")
        with open(args.input_file, 'r') as file:
            for line in file:
                try:
                    sql_line = parse_json(line)
                    output_file.write(sql_line)
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON line: {line.strip()}")  
                    fail_counter += 1
                    if fail_counter>10:
                        break
            # handle last line
            line = line.rstrip("}").rstrip("]")
            sql_line = parse_json(line)
            output_file.write(sql_line.rstrip(",\n"))
            output_file.write(f";\n")
        
    
if __name__ == "__main__":
    process_geojson()