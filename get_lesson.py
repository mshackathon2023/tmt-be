import logging
import azure.functions as func
import uuid
import json
from azure.cosmos import CosmosClient, PartitionKey
import azure.cosmos.exceptions as cosmos_exceptions
import os

GetLesson = func.Blueprint()

@GetLesson.route(route="getlesson/{topic}/{lesson}", methods=["GET"])
def getlesson(req: func.HttpRequest) -> func.HttpResponse:

    # Get topic ID from route parameter
    topic_id = req.route_params.get("topic")
    logging.info(f"Getting topic {topic_id}")

    # Get lesson ID from route parameter
    lesson_id = req.route_params.get("lesson")
    logging.info(f"Getting lesson {lesson_id}")

    # Connect to Cosmos DB
    client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
    database = client.get_database_client("tmtdb")
    container = database.get_container_client("topics")

    # Query lessons from Cosmos DB
    try:
        items = list(container.query_items(
            query="SELECT c.lessons FROM c JOIN l in c.lessons WHERE c.id=@topic_id and l.id=@lesson_id",
            parameters=[
                {"name": "@topic_id", "value": topic_id},
                {"name": "@lesson_id", "value": lesson_id}
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
    output = items[0]["lessons"]

    return func.HttpResponse(
        json.dumps(output),
        headers = {"Content-Type": "application/json"},
        status_code=200
    )