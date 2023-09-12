import azure.functions as func
import logging
import uuid
import json

from create_topic import CreateTopic
from get_topics import GetTopics

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

app.register_functions(CreateTopic) 
app.register_functions(GetTopics) 
