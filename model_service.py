from fastapi import FastAPI
from transformers import AutoTokenizer, AutoModelForCausalLM

app = FastAPI()

model_name = "./local_model"
tokenizer = AutoTokenizer.from_pretrained(load_model_path)
print("tokenizer loaded")
model = AutoModelForCausalLM.from_pretrained(load_model_path)
print("model loaded")

@app.post("/summarize")
async def summarize(review: str):
    promt = f"Summarize the following reviews: {review}"
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=100)
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return {"summary": summary}