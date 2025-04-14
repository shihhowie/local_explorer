import psycopg2

DB_NAME="testdb"
DB_USER="howardshih"
DB_PASSWORD="howardshih"

DB_HOST="database-1.c12cmowoyxgf.eu-north-1.rds.amazonaws.com"

try:
    conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )

    sql = """
            (select * 
            from overture_map_places) 
            where categories::json->>'primary' like '%coffee%');
        """