import psycopg2


DB_NAME="testdb"
DB_USER="howardshih"
DB_PASSWORD="howardshih"
DB_PORT="5432"
DB_HOST="database-1.c12cmowoyxgf.eu-north-1.rds.amazonaws.com"

def connect_to_db():
    conn = psycopg2.connect(
                    dbname=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    host=DB_HOST,
                    port=DB_PORT
                )
    cur = conn.cursor()
    return conn, cur

def fetch_places():
    conn, cur = connect_to_db()
    sql = """
            select id, coordinates, names
                from overture_map_places
                where categories::json->>'primary' like '%coffee%';
            """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def fetch_place_ids():
    conn, cur = connect_to_db()
    sql = """
            select id, names, gmap_id
                from overture_to_gmap;
            """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def fetch_photo_ref():
    conn, cur = connect_to_db()
    sql = """
            select gmap_id, photo_ref
                from overture_to_gmap limit 2;
            """
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def format_for_postgresql(input_string):
    if input_string is None:
        return "NULL"
    formatted_string = input_string.replace("'", "''")
    formatted_string = formatted_string.replace("\n", " ")
    return f"'{formatted_string}'"

def generate_sql(table_name, schema, input_list, overwrite=True, prefix=True):
    # scheuma should map colname to type
    sql_str = ""
    if prefix:
        sql_str += f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    dtypes = []
    primary_keys = []
    for col in schema:
        dtype = schema[col]['dtype']
        dtypes.append(dtype)
        is_key = schema[col].get('key', False)
        line = f"{col} {dtype},\n"
        if is_key: 
            primary_keys.append(col)
        if prefix:
            sql_str += line
    if prefix and primary_keys:
        sql_str += f"PRIMARY KEY ({','.join(primary_keys)})\n"
    if prefix:
        sql_str+=");\n"
    
    sql_str += f"INSERT INTO {table_name} ({','.join([col for col in schema])}) VALUES \n"
    first = True
    for input in input_list:
        formatted_input = [format_for_postgresql(x) if dtypes[i]=='TEXT' else str(x) for i, x in enumerate(input)]
        input_str = ",".join(formatted_input)
        line = f"({input_str})"
        if first:
            first = False
        else:
            line = ",\n"+line
        sql_str += line

    if overwrite and primary_keys:
        sql_str += f"\nON CONFLICT ({','.join(primary_keys)}) DO UPDATE SET\n"
        first = True
        for col in schema:
            if col in primary_keys:
                continue
            line = f"{col} = EXCLUDED.{col}"
            if first:
                first = False
            else:
                line = ",\n"+line
            sql_str += line
    elif primary_keys:
        sql_str += f"\nON CONFLICT ({','.join(primary_keys)}) DO NOTHING"
    sql_str += ";\n"
    return sql_str


def build_review_and_photo_script():
    place_ids = fetch_place_ids()
    # place_ids = [("08f194ad3209059d0305cc779903dff2", "WatchHouse Somerset House", "ChIJD3EFm1gFdkgRiPW6GgLcdM0")]
    batch_size = 128
    i = 0

    reviews_schema = {"gmap_id": {"dtype": "TEXT", "key": False},
                "avg_rating": {"dtype": "double precision"},
                "text": {"dtype": "TEXT", "key": False},
                "score": {"dtype": "double precision"}}

    photos_schema = {"gmap_id": {"dtype": "TEXT", "key": False},
                "photo_ref": {"dtype": "TEXT", "key": False}}

    reviews_input = []
    photos_input = []
    for place in place_ids:
        print(place)
        gmap_id = place[2]
        params = {
            "place_id": gmap_id,
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
                # print(data)
                avg_rating = data['rating']
                for review in data['reviews']:
                    text = review['text']
                    review_score = review['rating']
                    reviews_input.append((gmap_id, avg_rating, text, review_score))

                for photo in data['photos']:
                    photos_input.append((gmap_id, photo['photo_reference']))
            except Exception as e:
                print("error: ", e)
        i+=1
        if i%batch_size==0:
            print(f"batch {i//batch_size} * ", batch_size)
            review_sql = generate_sql("gmap_reviews", reviews_schema, reviews_input)
            photo_sql = generate_sql("gmap_photos", photos_schema, photos_input)
            reviews_input = []
            photos_input = []
            with open('write_place_detail_sql.sql', 'a') as f:
                f.write(review_sql)
                f.write(photo_sql)
    with open('write_place_detail_sql.sql', 'a') as f:
        if reviews_input:
            review_sql = generate_sql("gmap_reviews", reviews_schema, reviews_input)
            f.write(review_sql)
        if photos_input:
            photo_sql = generate_sql("gmap_photos", photos_schema, photos_input, overwrite=False)
            f.write(photo_sql)


def build_gmap_place_id_fetch_script():
    # need to add batching to handle memory
    places = fetch_places()
    schema = {
        "id": {"dtype": "TEXT", "key": True},
        "names": {"dtype": "TEXT"},
        "gmap_id": {"dtype": "TEXT"}
    }
    res = []
    counter = 0
    for place in places:
        req = build_place_id_req(place)
        if get_gmap_id(req):
            res.append((req['id'], req['name'], req['gmap_id']))
            counter += 1
    print("processed", counter)
    place_id_sql_str = generate_sql("overture_to_gmap", schema, res)

    with open(args.output_file, 'w') as output_file:
        output_file.write(place_id_sql_str)


if __name__=="__main__":
    schema = {"gmap_id": {"dtype": "TEXT", "key": False},
                "avg_rating": {"dtype": "DOUBLE"},
                "text": {"dtype": "TEXT"},
                "score": {"dtype": "DOUBLE"}}
    input_list = [("ChIJD3EFm1gFdkgRiPW6GgLcdM0", 4.5, "lovely coffee! lovely brunch lovely vibes! i love to come for coffee or food with my friends and the waiters are always so nice and good at their jobs. Especially Germaine who is so sweet and bubbly. One of the most reasonably priced - classy cafes/brunch places in this part of london!", "5"),
("ChIJD3EFm1gFdkgRiPW6GgLcdM0", 4.5, "I've ordered breakfast, which was absolutely delicious, along with hot chocolate for the kids and two vanilla lattes, which were great. The food took a long time to arrive, but they offered us a discount as compensation 🥰. The service was excellent, and the orange juice was super fresh, which is very important to me.  The view was amazing, and the café is just wow—I really love it!", "5")]
    generate_sql("test_table", schema, input_list)
