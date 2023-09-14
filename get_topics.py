import logging
import azure.functions as func
import uuid
import json
from azure.cosmos import CosmosClient, PartitionKey
import azure.cosmos.exceptions as cosmos_exceptions
import os

GetTopics = func.Blueprint()

@GetTopics.route(route="gettopics", methods=["GET"])
def gettopics(req: func.HttpRequest) -> func.HttpResponse:
    
    # Connect to Cosmos DB
    client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
    database = client.get_database_client("tmtdb")
    container = database.get_container_client("topics")

    # Query topics from Cosmos DB
    try:
        items = list(container.query_items(
            query="SELECT c.id, c.state, c.summary, c.title FROM c",
            parameters=[],
            enable_cross_partition_query=True
        ))
    except:
        return func.HttpResponse(
            f"Error when quering topics",
            headers = {"Content-Type": "application/json"},
            status_code=400
        )
    
    # Prepare output
    output = items
    
    return func.HttpResponse(
        json.dumps(output),
        headers = {"Content-Type": "application/json"},
        status_code=200
    )