import logging
import azure.functions as func
import uuid
import json
import jsonschema
from azure.cosmos import CosmosClient, PartitionKey
import azure.cosmos.exceptions as cosmos_exceptions
import os

EvalAssessment = func.Blueprint()

@EvalAssessment.route(route="evalassessment/{topic}", methods=["POST"])
@EvalAssessment.service_bus_topic_output(arg_name="message",
                              connection="SERVICEBUS_CONNECTION_STRING",
                              topic_name="assessedtopic")
def evalassessment(req: func.HttpRequest, message: func.Out[str]) -> func.HttpResponse:

    # Get topic ID from route parameter
    topic_id = req.route_params.get("topic")
    logging.info(f"Getting topic {topic_id}")

    # Define the JSON schema
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "q_id": {"type": "integer"},
                "text": {"type": "string"},
                "answers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "a_id": {"type": "integer"},
                            "text": {"type": "string"},
                            "selected": {"type": "boolean"},
                            "correct": {"type": "boolean"}
                        },
                        "required": ["a_id", "selected"]
                    }
                }
            },
            "required": ["q_id", "answers"]
        }
    }

    # Parse answers
    try:
        assessment_eval = req.get_json()
        jsonschema.validate(assessment_eval, schema)
    except:
        return func.HttpResponse(
            "JSON body with assessment could not be parsed",
            status_code=400
        )

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
    
    # Return error if assessment not available
    if topic["assessmentQuestions"] == None:
        return func.HttpResponse(
            f"Assessment for topic {topic_id} not available",
            headers = {"Content-Type": "application/json"},
            status_code=400
        )
    
    # Evaluate stored assessment against submitted assessment
    assessmentQuestions_edited = []
    for question in topic["assessmentQuestions"]:
        correct = False

        # Lookup question in submitted assessment
        question_eval = [q for q in assessment_eval if q["q_id"] == question["q_id"]][0]
        for answer in question["answers"]:

            # Lookup answer in submitted assessment
            answer_eval = [a for a in question_eval["answers"] if a["a_id"] == answer["a_id"]][0]

            # print(f"Q {question['q_id']}, A {answer['a_id']}-{answer_eval['a_id']}, correct {answer['correct']}, selected {answer_eval['selected']}")

            # Check if answer is correct
            if answer["correct"] and answer_eval["selected"]:
                correct = True
        
        # Add correct attribute to question
        question["correct"] = correct

        # Add question to list of questions
        assessmentQuestions_edited.append(question)
 
    # Replace original assessmentQuestions with edited version
    topic["assessmentQuestions"] = assessmentQuestions_edited
    topic["state"] = "assessed"

    # Replace topic in Cosmos DB
    container.replace_item(topic_id, topic)

    # Send message to Service Bus
    message.set(json.dumps({"topic": topic_id}))

    return func.HttpResponse(
        "{}",
        headers = {"Content-Type": "application/json"},
        status_code=200
    )