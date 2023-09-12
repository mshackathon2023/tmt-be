import logging
import azure.functions as func
import uuid
import json
from azure.cosmos import CosmosClient, PartitionKey
import azure.cosmos.exceptions as cosmos_exceptions
import os

GetAssessment = func.Blueprint()

@GetAssessment.route(route="getassessment/{topic}", methods=["GET"])
def getassessment(req: func.HttpRequest) -> func.HttpResponse:

    topic_id = req.route_params.get("topic")

    logging.info(f"Getting topic {topic_id}")

    client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
    database = client.get_database_client("tmtdb")
    container = database.get_container_client("topics")

   
    try:
        topic = container.read_item(
            item=topic_id,
            partition_key=topic_id
        )
    except cosmos_exceptions.CosmosResourceNotFoundError:
        return func.HttpResponse(
            f"Topic {topic_id} not found in database",
            headers = {"Content-Type": "application/json"},
            status_code=400
        )
    
    if topic["assessmentQuestions"] == None:
        return func.HttpResponse(
            f"Assessment for topic {topic_id} not available",
            headers = {"Content-Type": "application/json"},
            status_code=400
        )
    
    assessmentQuestions = []
    for question in topic["assessmentQuestions"]:
        question_record = {}
        question_record["q_id"] = question["q_id"]
        question_record["text"] = question["text"]
        question_record["answers"] = []
        for answer in question["answers"]:
            answer_record = {}
            answer_record["a_id"] = answer["a_id"]
            answer_record["text"] = answer["text"]
            question_record["answers"].append(answer_record)
        assessmentQuestions.append(question_record)

    return func.HttpResponse(
        json.dumps(assessmentQuestions),
        headers = {"Content-Type": "application/json"},
        status_code=200
    )