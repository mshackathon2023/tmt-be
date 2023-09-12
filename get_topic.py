import logging
import azure.functions as func
import uuid
import json
from azure.cosmos import CosmosClient, PartitionKey
import os

GetTopic = func.Blueprint()

@GetTopic.route(route="gettopic/{topic}", methods=["GET"])
def gettopic(req: func.HttpRequest) -> func.HttpResponse:

    topic_id = req.route_params.get("topic")

    logging.info(f"Getting topic {topic_id}")

    client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
    database = client.get_database_client("tmtdb")
    container = database.get_container_client("topics")

    topic = container.read_item(
        item=topic_id,
        partition_key=topic_id
    )

    return func.HttpResponse(
        json.dumps(topic),
        headers = {"Content-Type": "application/json"},
        status_code=200
    )