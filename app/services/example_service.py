from app.db.mongo import db
from app.models.example_model import Example

collection = db["examples"]

async def create_example(example: Example):
    result = await collection.insert_one(example.dict())
    return str(result.inserted_id)

async def get_all_examples():
    docs = await collection.find().to_list(100)
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs
