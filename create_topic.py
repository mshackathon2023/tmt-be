import logging
import azure.functions as func
import uuid
import json

CreateTopic = func.Blueprint()
# @CreateTopic.route(route="createtopic")
# def createtopic(req: func.HttpRequest) -> func.HttpResponse:
#     logging.info('Python HTTP trigger function processed a request.')

#     name = req.params.get('name')
#     if not name:
#         try:
#             req_body = req.get_json()
#         except ValueError:
#             pass
#         else:
#             name = req_body.get('name')

#     if name:
#         return func.HttpResponse(
#             f"Hello, {name}. This HTTP-triggered function "
#             f"executed successfully.")
#     else:
#         return func.HttpResponse(
#             "This HTTP-triggered function executed successfully. "
#             "Pass a name in the query string or in the request body for a"
#             " personalized response.",
#             status_code=200
#         )

@CreateTopic.route(route="createtopic", methods=["POST"])
@CreateTopic.cosmos_db_output(arg_name="rawDocuments",
                      database_name="tmtdb",
                      container_name="rawDocuments",
                      create_if_not_exists=True,
                      connection="COSMOSDB_CONNECTION_STRING")
@CreateTopic.cosmos_db_output(arg_name="topics",
                      database_name="tmtdb",
                      container_name="topics",
                      create_if_not_exists=True,
                      connection="COSMOSDB_CONNECTION_STRING")
@CreateTopic.service_bus_topic_output(arg_name="message",
                              connection="SERVICEBUS_CONNECTION_STRING",
                              topic_name="newDocument")
def createtopic(req: func.HttpRequest, rawDocuments: func.Out[func.Document], topics: func.Out[func.Document], message: func.Out[str]) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
        text = req_body.get("text")
    except ValueError:
        return func.HttpResponse(
             "JSON body with text is required.",
             status_code=400
        )

    # Generate a unique ID for the new document
    guid = str(uuid.uuid4())

    # Store raw document in Cosmos DB
    rawDocuments.set(func.Document.from_dict({"id":guid, "text": text}))

    # Create new topic record in Cosmos DB
    topics.set(func.Document.from_dict({"id":guid, "state": "pending"}))

    # Send message to Service Bus
    message.set(json.dumps({"topic": guid}))

    return func.HttpResponse(
        json.dumps({"topic": guid}),
        headers = {"Content-Type": "application/json"},
        status_code=202
    )