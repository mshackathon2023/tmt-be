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

    # Query topics from Cosmos DB
    try:
        items = list(container.query_items(
            query="SELECT c.id, c.state, c.summary, c.title FROM c WHERE c.id=@id",
            parameters=[
                {"name": "@id", "value": topic_id}
            ],
            enable_cross_partition_query=False
        ))
    except:
        return func.HttpResponse(
            f"Error when quering for topic {topic_id}",
            headers = {"Content-Type": "application/json"},
            status_code=400
        )
    
    # Prepare output
    output = items[0]

    return func.HttpResponse(
        json.dumps(output),
        headers = {"Content-Type": "application/json"},
        status_code=200
    )