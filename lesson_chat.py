import logging
import azure.functions as func
import uuid
import json
from azure.cosmos import CosmosClient, PartitionKey
import azure.cosmos.exceptions as cosmos_exceptions
import os


from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.document_loaders import TextLoader

from faker import Faker

def generate_random_sentence():
    fake = Faker()
    return fake.sentence()



def calculate_embeddings_on_chunks(chunks: list) -> list:
    embeddings = OpenAIEmbeddings(
        openai_api_base=os.environ["OPENAI_API_BASE"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_api_version=os.environ["OPENAI_API_VERSION"],
        deployment="text-embedding-ada-002")

    # Calculate embeddings on chunks
    chunk_embeddings = []
    for chunk in chunks:
        chunk_embeddings.append(embeddings.embed_documents([chunk]))
        
    # text = "This is a test document."
    # query_result = embeddings.embed_query(text)
    # doc_result = embeddings.embed_documents([text])
    return chunk_embeddings

LessonChat = func.Blueprint()

@LessonChat.route(route="lessonchat/{topic}/{lesson}", methods=["POST"])
def lessonchat(req: func.HttpRequest) -> func.HttpResponse:
    logging.getLogger("azure").setLevel(logging.ERROR)

    # Get topic ID from route parameter
    topic_id = req.route_params.get("topic")
    logging.info(f"Getting topic {topic_id}")

    # Get lesson ID from route parameter
    lesson_id = req.route_params.get("lesson")
    logging.info(f"Getting lesson {lesson_id}")

    messages = req.get_json()
    # messages = req.get_body().decode("utf-8")
    # lo

    # Connect to Cosmos DB
    client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
    database = client.get_database_client("tmtdb")
    container = database.get_container_client("topics")

    # Query lessons from Cosmos DB
    try:
        items = list(container.query_items(
            query="SELECT c.chunks FROM c WHERE c.id=@topic_id",
            parameters=[
                {"name": "@topic_id", "value": topic_id}
            ],
            enable_cross_partition_query=False
        ))


    except:
        return func.HttpResponse(
            f"Error when quering for topic {topic_id}",
            headers = {"Content-Type": "application/json"},
            status_code=400
        )

    # Prepare chunks
    chunks = items[0]["chunks"]

    # init faiss index
    import faiss
    import numpy as np
    index = faiss.IndexFlatL2(768)

    messages.append({"role":"assistant", "content": generate_random_sentence()})


    return func.HttpResponse(
        # json.dumps('[{"role":"user", "content":"user said"}, {"role":"assistant", "content":"assistant replied"}]'),
        json.dumps(messages),
        headers = {"Content-Type": "application/json"},
        status_code=200
    )