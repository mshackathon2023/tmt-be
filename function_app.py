import azure.functions as func
import logging
import uuid
import json

from create_topic import CreateTopic

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

app.register_functions(CreateTopic) 
