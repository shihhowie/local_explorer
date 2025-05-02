import psycopg2
import argparse
import os 

from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import login
from openai import OpenAI


from sql_util import generate_sql
from place_retriever import get_places


DB_NAME="testdb"
DB_USER="howardshih"
DB_PASSWORD="howardshih"
DB_PORT="5432"
DB_HOST="database-1.c12cmowoyxgf.eu-north-1.rds.amazonaws.com"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
HUGGING_FACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
OPENAI_TOKEN = os.getenv("OPENAIKEY")
client = OpenAI(api_key=OPENAI_TOKEN)

# login(HUGGING_FACE_TOKEN)

def load_model_openai(review):
    response = client.responses.create(model="gpt-3.5-turbo",  #
        instructions="You are a helpful assistant that describes a shop based on its reviews.",
        input=f"Aggregate these reviews into one short summary paragraph: {review}",
        temperature=0.7)
    return response.output_text

def load_model_hf():
    model_name = "meta-llama/Llama-2-7b-hf"
    load_model_path = "./local_model"
    tokenizer = AutoTokenizer.from_pretrained(load_model_path)
    print("tokenizer loaded")
    model = AutoModelForCausalLM.from_pretrained(load_model_path)
    print("model loaded")
    return model, tokenizer

def download_model():
    model_name = "meta-llama/Llama-2-7b-hf"
    save_directory = "./local_model"
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=True)
    tokenizer.save_pretrained(save_directory)
    model = AutoModelForCausalLM.from_pretrained(model_name, use_auth_token=True)
    model.save_pretrained(save_directory)

def aggregate_reviews(review):
    model, tokenizer = load_model()
    prompt = f"Summarize the following reviews : {review}"
    inputs = tokenizer(prompt, return_tensors="pt")
    print("tokenized")
    outputs = model.generate(**inputs, max_new_tokens=100)
    print(tokenizer.decode(outputs[0],skip_special_tokens=True))

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
    place_ids_str = ",".join([f"'{x}'" for x in place_ids])
    sql = f"""
            select
            names, a.gmap_id, avg(avg_rating) as rating, string_agg(b.text, '|') as review 
            from (
                (
                    select id, names, gmap_id
                    from overture_to_gmap
                    where id in ({place_ids_str})
                ) a
                left join
                (
                    select gmap_id, avg_rating, text 
                    from gmap_reviews
                ) b
                on a.gmap_id = b.gmap_id
            )
            group by names, a.gmap_id;
            """
    print(sql)
    # cur.execute(sql)
    # rows = cur.fetchall()
    # cur.close()
    # conn.close()
    # return rows

if __name__=="__main__":
    # places = get_places((51.52140, -0.11142), 0.3)
    # place_ids = [x[6] for x in places]
    # gather_reviews(place_ids)
    review = """The atmosphere in this place is amazing. And that doesn’t even cover how good the drin
ks and food were. Ozzie Joe really brought the vibes and clearly have a passion for what they do.  Thanks for the hang, mates! Until next time ✌️|Great coffee, ha
d a flat white which tasted very smooth and mild, not bitter at all. I also ordered a croissant which unfortunately was a huge let down and I very disappointed w
ith. It was stale and felt like I was having cardboard. Had to throw it away in the end. The service was polite and friendly, and I have popped in a few times be
fore - it has good vibes, great clothing range on sale|What a gem 💎 of a find! A warm welcome into vibes of great music, coffee and pre-loved apparel.  They wer
e due to close shortly but when ordered my coffee I was still  offered it in a proper ceramic cup ☕️ & to enjoy in store.  Which is rare - usually paper cups onl
y and 👋🏼 bye) . I also took advantage of an offer to purchase a hat from a selection for £5 when purchase a coffee … deal 🙌|Solid spot. Great tasting Coffee :
)  The owner Opened & served for us on a sunday even though he was off shift and not working!!|Lovely staff and even better coffee and clothing! Definitely will 
be coming in again to try the fresh pastries!"""
    resp = load_model_openai(review)
    print(resp)
