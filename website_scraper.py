import requests
import argparse
import os 

DB_NAME="testdb"
DB_USER="howardshih"
DB_PASSWORD="howardshih"
DB_PORT="5432"
DB_HOST="database-1.c12cmowoyxgf.eu-north-1.rds.amazonaws.com"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

parser = argparse.ArgumentParser(description="enrich data with gmap id.")
parser.add_argument('-o', '--output_file', type=str, help="Path to the sql output to process")

def get_url(rsps):
    urls = []
    for rsp in rsps:
        # print(rsp[3].strip("[]").split(","))
        url = rsp[3].strip("[]").replace('"', '').split(",")
        url = [u for u in url if u != '']
        if url:
            # print(url)
            urls.extend(url)
    return urls

def get_gmap_id(req):
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = req["params"]
    rsp = requests.get(url, params=params)
    if rsp.status_code==200:
        data =rsp.json()
        gmap_id = data['candidates'][0].get('place_id', None)
        if gmap_id:
            req['gmap_id'] = gmap_id
            return True
    return False


def build_req(place_rsp):
    id = place_rsp[0]
    coord = place_rsp[1].strip('[]').replace(' ','').split(",")
    lat, lon = coord[1], coord[0]
    name = place_rsp[2]
    req = {
        "input": place_rsp[2],
        "inputtype": "textquery",
        "fields": "place_id",
        "locationbias": f"point:{lat},{lon}",
        "key": GOOGLE_API_KEY
    }
    return {"id":id, "name": name, "params": req}

def fetch_places():
    conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
    cur = conn.cursor()
    sql = """select id, coordinates, names
                from overture_map_places
                where categories::json->>'primary' like '%coffee%';
            """
    cur.execute(sql)
    rows = cur.fetchall()
    return rows

def process():
    places = fetch_places()
    rsp = []
    for place in places:
        req = build_req(place)
        if get_gmap_id(req):
            line_val = f"({req['id']},{req['name']},{req['gmap_id']})"
            rsp.append(line_val)
    with open(args.output_file, 'w') as output_file:
        output_file.write('''CREATE TABLE IF NOT EXISTS overture_to_gmap (
            id TEXT PRIMARY KEY,
            names TEXT,
            gmap_id TEXT
        );\n''')
        output_file.write(f"INSERT INTO overture_map_places (id, name, gmap_id) VALUES \n")
        output_file.write(f',\n'.join(rsp))
        output_file.write(''' 
                    ON CONFLICT (id) DO UPDATE SET
                    names = EXCLUDED.names,
                    gmap_id = EXCLUDED.gmap_id;
                ''')

if __name__=="__main__":
    # rsps = [("Fabrizio's", '[-0.1093812, 51.5205546]', '{"primary": "coffee_shop", "alternate": ["restaurant"]}', '[""]', '[]', '{"freeform": "30 Street Cross Street", "locality": "London", "postcode": "EC1N 8UH", "region": "", "country": "GB"}'), ('Catalyst', '[-0.112027, 51.5197541]', '{"primary": "coffee_shop", "alternate": ["cafe", "restaurant"]}', '["http://catalyst.cafe/"]', '["https://www.facebook.com/1784722045117889"]', '{"freeform": "48 Gray\'s Inn Road", "locality": "London", "postcode": "WC1X 8LT", "region": "ENG", "country": "GB"}'), ('Milk and honey', '[-0.1121532, 51.519894]', '{"primary": "coffee_shop", "alternate": ["greek_restaurant", "smoothie_juice_bar"]}', '[]', '["https://www.facebook.com/107075711945357"]', '{"freeform": "52 Gray\'s Inn Road", "locality": "London", "postcode": "WC1X 8LT", "region": "ENG", "country": "GB"}'), ('The Dayrooms Cafe', '[-0.113717, 51.521539]', '{"primary": "coffee_shop", "alternate": ["cafe", "restaurant"]}', '["https://thedayroomscafe.com"]', '["https://www.facebook.com/273557969812210"]', '{"freeform": "10 Theobalds Road", "locality": "London", "postcode": "WC1X 8", "region": "ENG", "country": "GB"}'), ('Pret A Manger', '[-0.1132088, 51.5213574]', '{"primary": "coffee_shop", "alternate": ["sandwich_shop", "food", "restaurant"]}', '["https://www.pret.co.uk/?utm_source=bing_places&utm_medium=98&utm_campaign=bing_website"]', '[]', '{"freeform": "100-108 Gray\'s Inn Road", "locality": "London", "postcode": "WC1X 8AJ", "region": "", "country": "GB"}'), ("Andrew's Restaurant", '[-0.1141132, 51.5223932]', '{"primary": "coffee_shop", "alternate": ["cafe", "restaurant"]}', '["http://standrewscentre.org.uk/index.php/cafe"]', '["https://www.facebook.com/155259641168835"]', '{"freeform": "83 Gray\'s Inn Road", "locality": "London", "postcode": "WC1X 8", "region": "ENG", "country": "GB"}'), ('Kitchen8', '[-0.1140483, 51.5227348]', '{"primary": "coffee_shop", "alternate": ["cafe", "restaurant"]}', '["http://www.kitchen8.co.uk/"]', '["https://www.facebook.com/1515699411982809"]', '{"freeform": "17 Elm Street", "locality": "London", "postcode": "WC1X 0BQ", "region": "ENG", "country": "GB"}'), ('Hopper Coffee', '[-0.1145634, 51.5229053]', '{"primary": "coffee_shop", "alternate": ["cafe", "fast_food_restaurant"]}', '[]', '["https://www.facebook.com/1684526505095236"]', '{"freeform": "81b Roger Street", "locality": "London", "postcode": "WC1X 8", "region": "ENG", "country": "GB"}'), ('Attendant Coffee Roasters', '[-0.1099291, 51.5211455]', '{"primary": "coffee_shop", "alternate": ["cafe", "restaurant"]}', '["http://www.the-attendant.com/"]', '["https://www.facebook.com/703835266486677"]', '{"freeform": "75 Leather Lane", "locality": "London", "postcode": "EC1N 7TJ", "region": "ENG", "country": "GB"}'), ('Londons Roastery', '[-0.1118, 51.52356]', '{"primary": "coffee_shop", "alternate": ["breakfast_and_brunch_restaurant", "cafe"]}', '[]', '["https://www.facebook.com/185340921325203"]', '{"freeform": "Warner Street XXX, ", "locality": "London", "postcode": null, "region": null, "country": "GB"}'), ('Dynasty Of Coffee', '[-0.1103353, 51.5238124]', '{"primary": "coffee_shop", "alternate": ["smoothie_juice_bar"]}', '["http://www.dynastyofcoffee.com/"]', '["https://www.facebook.com/102578329365510"]', '{"freeform": "1 Coldbath Square", "locality": "London", "postcode": "EC1R 5HL", "region": "ENG", "country": "GB"}'), ('The Artifacts Coffee and Culture', '[-0.1089486, 51.5193875]', '{"primary": "coffee_shop", "alternate": ["clothing_store", "smoothie_juice_bar"]}', '["http://www.artifactsapparel.co.uk/"]', '["https://www.facebook.com/168981319639756"]', '{"freeform": "14 Leather Lane", "locality": "London", "postcode": "EC1N 7SU", "region": "ENG", "country": "GB"}'), ('Prufrock Coffee', '[-0.1094769, 51.5199218]', '{"primary": "coffee_shop", "alternate": ["cafe", "restaurant"]}', '["http://www.prufrockcoffee.com/"]', '["https://www.facebook.com/186075031423150"]', '{"freeform": "23-25 Leather Lane", "locality": "London", "postcode": "EC1N 7", "region": "ENG", "country": "GB"}'), ('Oasis', '[-0.1094057, 51.5199997]', '{"primary": "coffee_shop", "alternate": ["cafe", "restaurant"]}', '["http://www.oasis-blinds.co.uk/"]', '["https://www.facebook.com/206306872741750"]', '{"freeform": "27 Leather Lane", "locality": "London", "postcode": "EC1N 7TE", "region": "ENG", "country": "GB"}'), ('Dejava Coffee', '[-0.10811, 51.51995]', '{"primary": "coffee_shop", "alternate": ["shopping", "food_beverage_service_distribution"]}', '["http://www.williamscoffee.company/"]', '["https://www.facebook.com/253834375355008"]', '{"freeform": "67-68 Hatton Garden", "locality": "London", "postcode": "EC1N 8", "region": "ENG", "country": "GB"}')]
    # for rsp in rsps:
    #     req = build_req(rsp)
    #     print(req)
    #     if get_gmap_id(req):
    #         print(req)
    #     break
    process()
