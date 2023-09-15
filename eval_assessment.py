import logging
import azure.functions as func
import uuid
import json
import jsonschema
from azure.cosmos import CosmosClient, PartitionKey
import azure.cosmos.exceptions as cosmos_exceptions
import os

from langchain.chat_models import AzureChatOpenAI
from langchain import LLMChain, PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ReduceDocumentsChain, MapReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.schema.document import Document
import tiktoken

from prompt_utils import PROMPT_generate_eval_text, PROMPT_generate_eval_areas

EvalAssessment = func.Blueprint()

def generate_eval_text(answers) -> str:
    text = ""
    for answer in answers:
        if answer["correct"]:
            text += f"CORRECT: {answer['text']}\n"
        else:
            text += f"INCORRECT: {answer['text']}\n"

    llm = AzureChatOpenAI(temperature=0.7, 
                      model_name="gpt-35-turbo", 
                      deployment_name="gpt-35-turbo", 
                      openai_api_base=os.getenv("OPENAI_API_BASE"), 
                      openai_api_key=os.getenv("OPENAI_API_KEY"), 
                      openai_api_version=os.getenv("OPENAI_API_VERSION") )
    
    logging.info("-------- GEN EVAL TEXT ------------------")

    llm_chain = LLMChain(
        llm=llm,
        prompt=PromptTemplate.from_template(PROMPT_generate_eval_text)
    )
    try:
        r = llm_chain(answers)
        eval_text = r["text"]
        logging.info(eval_text)
    except Exception as e:  
        logging.warn(f"error probably Content Filtering: {e}")
        eval_text = "Not available due to content filtering"
        
    return eval_text

def generate_eval_areas(answers) -> str:
    text = ""
    for answer in answers:
        if answer["correct"]:
            text += f"CORRECT: {answer['text']}\n"
        else:
            text += f"INCORRECT: {answer['text']}\n"

    llm = AzureChatOpenAI(temperature=0.7, 
                      model_name="gpt-35-turbo", 
                      deployment_name="gpt-35-turbo", 
                      openai_api_base=os.getenv("OPENAI_API_BASE"), 
                      openai_api_key=os.getenv("OPENAI_API_KEY"), 
                      openai_api_version=os.getenv("OPENAI_API_VERSION") )
    
    logging.info("-------- GEN AREAS ------------------")

    llm_chain = LLMChain(
        llm=llm,
        prompt=PromptTemplate.from_template(PROMPT_generate_eval_areas)
    )

    eval_areas = '[{"name":'

    try:
        r = llm_chain(answers)
        eval_areas = eval_areas + r["text"]
        eval_areas = json.loads(eval_areas)
        logging.info(eval_areas)
    except Exception as e:  
        logging.warn(f"error probably Content Filtering or JSON parsing: {e}")
        eval_areas = []

    return eval_areas


@EvalAssessment.route(route="evalassessment/{topic}", methods=["POST"])
@EvalAssessment.service_bus_topic_output(arg_name="message",
                              connection="SERVICEBUS_CONNECTION_STRING",
                              topic_name="assessedtopic")
def evalassessment(req: func.HttpRequest, message: func.Out[str]) -> func.HttpResponse:

    logging.getLogger("azure").setLevel(logging.ERROR)

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
        logging.error("JSON body with assessment could not be parsed")
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

    # Calculate total score
    correct_answers = 0
    incorrect_answers = 0
    for question in assessmentQuestions_edited:
        if question["correct"]:
            correct_answers += 1
        else:
            incorrect_answers += 1
    total_score = 100 * correct_answers / (correct_answers + incorrect_answers)

    # Prepare output
    output = {}
    output["totalScore"] = total_score
    output["evaluation"] = generate_eval_text(assessmentQuestions_edited)
    output["areas"] = generate_eval_areas(assessmentQuestions_edited)
    
    logging.info(f"FINAL RESPONSE:\n{output}")

    return func.HttpResponse(
        json.dumps(output),
        headers = {"Content-Type": "application/json"},
        status_code=200
    )