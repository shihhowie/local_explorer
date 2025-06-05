import requests
import argparse
import os 
import hashlib

import json

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def get_gmap_id(req):
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = req
    rsp = requests.get(url, params=params)
    if rsp.status_code==200:
        data =rsp.json()
        if not data['candidates']:
            print('candidate empty for', req)
            return False
        gmap_id = data['candidates'][0].get('place_id', None)
        if gmap_id:
            req['gmap_id'] = gmap_id
            return True
    return False

def build_place_id_req():
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

def process_coffee_shop_gmap_ids():
    with open("local_data/test_places_EC.geojson") as f:
        data = json.load(f)
    
    count = 0
    with open("local_data/coffee_EC.txt", "w") as f:
        for place in data['features']:
            lon, lat = place['geometry']['coordinates']
            id = place['properties']['id']
            name = place['properties']['names']['primary']
            cats = place['properties']['categories']
            if cats['primary']=='coffee_shop':
                count+=1
            elif cats['alternate'] is not None and 'coffee_shop' in cats['alternate']:
                count+=1
            else:
                continue
            req = {
                "input": name,
                "inputtype": "textquery",
                "fields": "place_id",
                "locationbias": f"point:{lat},{lon}",
                "key": GOOGLE_API_KEY
            }
            # print(req)
            rsp = get_gmap_id(req)
            if rsp:
                result={
                    "id": id,
                    "name": name,
                    "gmap_id": req['gmap_id'],
                    "coord": [lon,lat]
                }
            f.write(f"{json.dumps(result)}\n")
            # if count == 2:
            #     break

def process_photos_and_reviews():
    processed_ids = set()
    with open("local_data/coffee_EC_details.txt") as f:
        for line in f:
            place = json.loads(line)
            processed_ids.add(place['gmap_id'])

    with open("local_data/coffee_EC_details.txt", "a") as fwrite: 
        with open("local_data/coffee_EC.txt") as f:
            for line in f:
                place = json.loads(line)
                if place['gmap_id'] in processed_ids:
                    print("skip", place['name'])
                    continue
                params = {
                    "place_id": place['gmap_id'],
                    "fields": "rating,reviews,photos",
                    "key": GOOGLE_API_KEY
                }
                url = "https://maps.googleapis.com/maps/api/place/details/json"
                rsp = requests.get(url, params=params)
                if rsp.status_code==200:
                    rsp = rsp.json()
                    if rsp['status']!='OK':
                        continue
                    try: 
                        data = rsp['result']
                        if not data:
                            print("empty",place['name'], place['gmap_id'])
                            continue
                        # print(data)

                        avg_rating = data.get('rating', None)
                        review_res = []
                        for review in data.get('reviews', []):
                            text = review['text']
                            review_score = review['rating']
                            review_res.append({"text": text, "score": review_score})
                        
                        attrib = set()
                        photo_ref = []
                        for photo in data.get('photos',[]):
                            attrib.update(photo['html_attributions'])
                            photo_ref.append(photo['photo_reference'])

                        result = {
                            "gmap_id": place['gmap_id'],
                            "name": place["name"],
                            "place_id": place['id'],
                            "avg_rating": avg_rating,
                            "reviews": review_res,
                            "photos": {
                                "attrib": list(attrib),
                                "ref": photo_ref
                            }
                        }
                        fwrite.write(f"{json.dumps(result)}\n")
                        # break
                    except Exception as e:
                        print("error: ", e)
                        print(data)
                        break

if __name__=="__main__":
    # process_coffee_shop_gmap_ids()
    
        