import azure.functions as func
import logging
import uuid
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="CreateTopic", methods=["POST"])
@app.cosmos_db_output(arg_name="rawDocuments", 
                      database_name="tmtdb",
                      container_name="rawDocuments",
                      create_if_not_exists=True,
                      connection="COSMOSDB_CONNECTION_STRING")
@app.service_bus_topic_output(arg_name="message",
                              connection="SERVICEBUS_CONNECTION_STRING",
                              topic_name="newDocument")
def CreateTopic(req: func.HttpRequest, rawDocuments: func.Out[func.Document], message: func.Out[str]) -> func.HttpResponse:
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

    # Store document in Cosmos DB
    rawDocuments.set(func.Document.from_dict({"id":guid, "text": text}))
    
    # Send message to Service Bus
    message.set(json.dumps({"topic": guid}))

    return func.HttpResponse(
        f"Created topic {guid}",
        headers = {"Content-Type": "application/json"},
        status_code=202
    )