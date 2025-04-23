import psycopg2
import argparse
import os 

from sql_util import generate_sql
from place_retriever import get_places

DB_NAME="testdb"
DB_USER="howardshih"
DB_PASSWORD="howardshih"
DB_PORT="5432"
DB_HOST="database-1.c12cmowoyxgf.eu-north-1.rds.amazonaws.com"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

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

def gather_reviews(place_ids):
    conn, cur = connect_to_db()
    sql = f"""
            select
            names, a.gmap_id, avg_rating, string_agg(text, ';')
            (select id, names, gmap_id
                from overture_to_gmap
                where id in ({','.join(place_ids)})) a
            left join
            (select gmap_id, avg_rating, text 
            from gmap_reviews) b
            on a.gmap_id = b.gmap_id
            group by names, a.gmap_id;
            """
    print(sql)
    # cur.execute(sql)
    # rows = cur.fetchall()
    # cur.close()
    # conn.close()
    # return rows

if __name__=="__main__":
    places = get_places((51.52140, -0.11142), 0.1)
    place_ids = [x[6] for x in places]
    gather_reviews(place_ids)