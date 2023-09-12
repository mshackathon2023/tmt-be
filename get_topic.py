import logging
import azure.functions as func
import uuid
import json
from azure.cosmos import CosmosClient, PartitionKey
import azure.cosmos.exceptions as cosmos_exceptions
import os

GetTopic = func.Blueprint()

@GetTopic.route(route="gettopic/{topic}", methods=["GET"])
def gettopic(req: func.HttpRequest) -> func.HttpResponse:

    # Get topic ID from route parameter
    topic_id = req.route_params.get("topic")
    logging.info(f"Getting topic {topic_id}")

    # Connect to Cosmos DB
    client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
    database = client.get_database_client("tmtdb")
    container = database.get_container_client("topics")

    # Retrieve topic from Cosmos DB
    try:
        topic = container.read_item(
            item=topic_id,
            partition_key=topic_id
        )
    # Handle error of topic not found
    except cosmos_exceptions.CosmosResourceNotFoundError:
        return func.HttpResponse(
            f"Topic {topic_id} not found in database",
            headers = {"Content-Type": "application/json"},
            status_code=400
        )

    return func.HttpResponse(
        json.dumps(topic),
        headers = {"Content-Type": "application/json"},
        status_code=200
    )