import argparse
import os 
import json

import tiktoken
import openai 

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
HUGGING_FACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
OPENAI_TOKEN = os.getenv("OPENAIKEY")
# client = OpenAI(api_key=OPENAI_TOKEN)
openai.api_key = OPENAI_TOKEN

def calculate_tokens(text, model="text-embedding-ada-002"):
    # Use the appropriate encoding for the model
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)


def fetch_embedding(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding
    # return response["data"][0]["embedding"]

if __name__=="__main__":
    tokens_count = 0
    processed_ids = set()
    with open("local_data/coffee_EC_embeddings.txt") as f:
        for line in f:
            place = json.loads(line)
            processed_ids.add(place['place_id'])
    with open("local_data/coffee_EC_embeddings.txt", "a") as fwrite:
        with open("local_data/coffee_EC_details.txt") as f:
            for line in f:
                place = json.loads(line)
                gmap_id = place['gmap_id']
                name = place["name"]
                place_id = place['place_id']
                if place_id in processed_ids:
                    print("skip", name)
                    continue
                try:
                    aggregated_review = f"{name}'s reviews - ratings: "
                    for review in place["reviews"]:
                        rating = review['score']
                        text = review['text']
                        aggregated_review += f"{text} - {rating} stars. \n"
                    # print(aggregated_review)
                    tcount = calculate_tokens(aggregated_review)
                    tokens_count += tcount
                    print(name, tcount, len(place["reviews"]))
                    embedding = fetch_embedding(aggregated_review)
                    result = {
                        "place_id": place_id,
                        "embedding": embedding
                    }
                    fwrite.write(f"{json.dumps(result)}\n")
                except Exception as e:
                    print("error", e, place)
                    break
        print(tokens_count)