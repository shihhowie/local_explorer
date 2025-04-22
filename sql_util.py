def format_for_postgresql(input_string):
    if input_string is None:
        return "NULL"
    formatted_string = input_string.replace("'", "''")
    formatted_string = formatted_string.replace("\n", " ")
    return f"'{formatted_string}'"

def generate_sql(table_name, schema, input_list, overwrite=True):
    # scheuma should map colname to type
    sql_str = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    id_col = None
    dtypes = []
    for col in schema:
        dtype = schema[col]['dtype']
        dtypes.append(dtype)
        is_key = schema[col].get('key', False)
        line = f"{col} {dtype}"
        if is_key: 
            id_col = col
            line += " PRIMARY KEY,\n"
        else:
            line += ",\n"
        sql_str += line
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

    if overwrite and id_col is not None:
        sql_str += f"\nON CONFLICT ({id_col}) DO UPDATE SET\n"
        first = True
        for col in schema:
            if col==id_col:
                continue
            line = f"{col} = EXCLUDED.{col}"
            if first:
                first = False
            else:
                line = ",\n"+line
            sql_str += line
    sql_str += ";\n"
    return sql_str

if __name__=="__main__":
    schema = {"gmap_id": {"dtype": "TEXT", "key": False},
                "avg_rating": {"dtype": "DOUBLE"},
                "text": {"dtype": "TEXT"},
                "score": {"dtype": "DOUBLE"}}
    input_list = [("ChIJD3EFm1gFdkgRiPW6GgLcdM0", 4.5, "lovely coffee! lovely brunch lovely vibes! i love to come for coffee or food with my friends and the waiters are always so nice and good at their jobs. Especially Germaine who is so sweet and bubbly. One of the most reasonably priced - classy cafes/brunch places in this part of london!", "5"),
("ChIJD3EFm1gFdkgRiPW6GgLcdM0", 4.5, "I've ordered breakfast, which was absolutely delicious, along with hot chocolate for the kids and two vanilla lattes, which were great. The food took a long time to arrive, but they offered us a discount as compensation 🥰. The service was excellent, and the orange juice was super fresh, which is very important to me.  The view was amazing, and the café is just wow—I really love it!", "5")]
    generate_sql("test_table", schema, input_list)