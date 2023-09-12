import azure.functions as func
import logging
import uuid
import json

from create_topic import CreateTopic
from get_topics import GetTopics
from get_topic import GetTopic
from process_topic import ProcessTopic

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

app.register_functions(CreateTopic) 
app.register_functions(GetTopics) 
app.register_functions(GetTopic) 
app.register_functions(ProcessTopic)

