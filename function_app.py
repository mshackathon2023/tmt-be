import azure.functions as func
import logging
import uuid
import json

from create_topic import CreateTopic
from get_topics import GetTopics
from get_topic import GetTopic
from process_topic import ProcessTopic
from get_assessment import GetAssessment
from eval_assessment import EvalAssessment
from generate_lesson import GenerateLesson
from get_lessons import GetLessons
from get_lesson import GetLesson
from lesson_chat import LessonChat

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

app.register_functions(CreateTopic) 
app.register_functions(GetTopics) 
app.register_functions(GetTopic) 
app.register_functions(ProcessTopic)
app.register_functions(GetAssessment)
app.register_functions(EvalAssessment)
app.register_functions(GenerateLesson)
app.register_functions(GetLessons)
app.register_functions(GetLesson)
app.register_functions(LessonChat)
