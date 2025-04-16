import psycopg2
import geohash2
from math import *

DB_NAME="testdb"
DB_USER="howardshih"
DB_PASSWORD="howardshih"

DB_HOST="database-1.c12cmowoyxgf.eu-north-1.rds.amazonaws.com"

geohash_cell_size = {
        4: (39, 19.5),    # ~39 km x 19.5 km
        5: (4.9, 4.9),    # ~4.9 km x 4.9 km
        6: (1.2, 0.6),    # ~1.2 km x 0.6 km
        7: (0.15, 0.15),  # ~150 m x 150 m
        8: (0.038, 0.019) # ~38 m x 19 m
    }

def get_bounding_box(curr_location, r):
    # make sure its lat, lon, r in km

    for prec in geohash_cell_size:
        dlat, dlon = geohash_cell_size[prec]
        if r > dlat:
            prec-=1
            break
    print(prec+1)
    lat, lon = curr_location[0], curr_location[1]

    C = 40075
    dY = r / C * 360
    print(dY*cos(radians(lat)))
    dX = dY*cos(radians(lat))
    print(dX, dY)
    lat_min = lat - dX
    lat_max = lat + dX

    lon_min = lon - dY
    lon_max = lon + dY

    NW = geohash2.encode(lat_max, lon_min, precision=prec)
    NE = geohash2.encode(lat_max, lon_max, precision=prec)
    SW = geohash2.encode(lat_min, lon_min, precision=prec)
    SE = geohash2.encode(lat_min, lon_max, precision=prec)
    print(f"NW: {NW}{lat_max, lon_min}, NE: {NE}{lat_max, lon_max}, SW: {SW}{lat_min, lon_min}, SE: {SE}{lat_min, lon_max}")

    return  (lat_min, lat_max, lon_min, lon_max), prec

def get_geohashes(bounding_box, prec):
    lat_min, lat_max, lon_min, lon_max = bounding_box
    step = 0.02 # 20m
    C = 40075
    dlat = 0.02 / C * 360
    dlon = 0.04 / C*cos(radians(lat_min)) *360
    print(dlat, dlon)
    geohashes = set()
    lat = lat_min
    while lat <= lat_max:
        lon = lon_min
        while lon <= lon_max:
            geohashes.add(geohash2.encode(lat, lon, precision=prec))
            lon += dlon
        lat += dlat
    return list(geohashes)

def fetch_places(geohashes):
    try:
        conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
        geo_hashes_str = ",".join(geohashes)
        sql = f"""
            select 
                b.names,
                b.coordinates, 
                b.categories, 
                b.websites, 
                b.socials, 
                b.address
            from 
            (   select 
                id 
                from places_geohash 
                where geohash in ('gcpvjk', 'gcpvjs', 'gcpvje', 'gcpvj7', 'gcpvjd', 'gcpvj6')
            ) a inner join
            (   select * 
                from overture_map_places
                where categories::json->>'primary' like '%coffee%'
            ) b on a.id=b.id
            ;
            """
        cur.execute(sql)
        rows = cur.fetchall()
        return rows
        results = []
        
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return []

def fine_tune(coordinates, rows, radius):
    lat, lon = coordinates[0], coordinates[1]
    res = []
    for row in rows:
        lon2, lat2 = row[1]
        dlat = radians(lat2 - lat)
        dlon = radians(lon2 - lon)

        a = sin(dlat/2)**2 + cos(radians(lat)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        if distance <= radius:
            res.append(row)
    return res

def get_places(curr_location, radius):
    # get the biggest bounding box that contains the radius
    bounding_box, prec = get_bounding_box(curr_location, radius)
    # get all the geohashes in the bounding box
    geohashes = get_geohashes(bounding_box, prec)
    # make query to psql for the places in the geohashes
    rows = fetch_places(geohashes)
    # return fine_tune(curr_location, rows, radius)
    return rows

if __name__ == "__main__":
    places = get_places((51.52140, -0.11142), 1)
    print(places)