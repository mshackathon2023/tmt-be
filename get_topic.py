import logging
import azure.functions as func
import uuid
import json

GetTopic = func.Blueprint()

@GetTopic.route(route="gettopic", methods=["GET"])
def gettopic(req: func.HttpRequest) -> func.HttpResponse:
    
    return func.HttpResponse(
        "",
        headers = {"Content-Type": "application/json"},
        status_code=200
    )