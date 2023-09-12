import logging
import azure.functions as func
import uuid
import json

GetTopics = func.Blueprint()

@GetTopics.route(route="gettopics", methods=["GET"])
@GetTopics.cosmos_db_input(arg_name="documents", 
                     database_name="tmtdb",
                     container_name="topics",
                     connection="COSMOSDB_CONNECTION_STRING")
def gettopics(req: func.HttpRequest, documents: func.DocumentList) -> func.HttpResponse:
    
    # Go throw list of documents and convert to dict
    output = []
    for doc in documents:
        output.append(doc.to_dict())
    
    return func.HttpResponse(
        json.dumps(output),
        headers = {"Content-Type": "application/json"},
        status_code=200
    )