import logging
from time import sleep
import uuid
import json
import os 
import random

import azure.functions as func
from azure.cosmos import CosmosClient

from langchain.chat_models import AzureChatOpenAI
from langchain import LLMChain, PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ReduceDocumentsChain, MapReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.schema.document import Document
import tiktoken

from prompt_utils import PROMPT_summarize_reduce_template, PROMPT_summarize_map_template, PROMPT_title_template, PROMPT_generate_assesment, PROMPT_generate_lesson

GenerateLesson = func.Blueprint()

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.encoding_for_model(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def get_topic(id: str) -> dict:
    """
    Retrieves a topic document from a Cosmos DB container.

    Args:
        id (str): The ID of the topic document to retrieve.

    Returns:
        dict: The retrieved topic document, or None if it was not found.
    """
    logging.info("-------- DOC READ INIT ---------- ")
    sleep(1) # TODO remove or fix with async / consistency
    logging.info(f"processing document: {id}")
    # id = "ee448ef4-69ca-4ec8-92e1-a1b566e5bb85"
    # logging.info(f"processing document (hard-coded): {id}")
    try:
        client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
        database = client.get_database_client("tmtdb")
        container = database.get_container_client("topics")

        topic = container.read_item(
            item=id,
            partition_key=id
        )
        # document = topic["text"]
        # tokens = num_tokens_from_string(document, "gpt-3.5-turbo")
        # logging.info(f'INFO: whole document has {tokens} tokens')

        # langchain_document = Document(page_content=document, metadata={"title":"n/a"})
        # return langchain_document

        return topic
    except:
        logging.info("document not found: "+ id)
        return None

def summarize_document(llm:AzureChatOpenAI, document:Document) -> tuple:
    # Get Summary as map-reduce patttern from LangChain
    # Map
    map_prompt = PromptTemplate.from_template(PROMPT_summarize_map_template)
    map_chain = LLMChain(llm=llm, prompt=map_prompt)

    # Reduce
    reduce_prompt = PromptTemplate.from_template(PROMPT_summarize_reduce_template)


    # Run chain
    reduce_chain = LLMChain(llm=llm, prompt=reduce_prompt)

    # Takes a list of documents, combines them into a single string, and passes this to an LLMChain
    combine_documents_chain = StuffDocumentsChain(
        llm_chain=reduce_chain, document_variable_name="doc_summaries"
    )

    # Combines and iteravely reduces the mapped documents
    reduce_documents_chain = ReduceDocumentsChain(
        # This is final chain that is called.
        combine_documents_chain=combine_documents_chain,
        # If documents exceed context for `StuffDocumentsChain`
        collapse_documents_chain=combine_documents_chain,
        # The maximum number of tokens to group documents into.
        token_max=4000,
    )

    map_reduce_chain = MapReduceDocumentsChain(
        # Map chain
        llm_chain=map_chain,
        # Reduce chain
        reduce_documents_chain=reduce_documents_chain,
        # The variable name in the llm_chain to put the documents in
        document_variable_name="docs",
        # Return the results of the map steps in the output
        return_intermediate_steps=False,
    )


    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=2000, 
        chunk_overlap=200,
        separator = "\n",
    )
    # logging.info(len(document.page_content))
    # logging.info(document.page_content)
    # split_docs = text_splitter.create_documents(document.page_content)
    split_docs = text_splitter.split_documents([document])
    # logging.info("-------- SPLITTING OUTPUT ------------------")
    logging.info(f"INFO: document split in {len(split_docs)} chunks")
    # for doc in split_docs:
    #     # for key, value in doc.metadata.items():
    #     #     print (key)
    #     logging.info("Chunk:")
    #     # logging.info(doc.metadata["title"])
    #     logging.info(num_tokens_from_string(doc.page_content, "gpt-3.5-turbo"))
    logging.info("-------- MAP REDUCE OUTPUT ----------")
    doc_summary = map_reduce_chain.run(split_docs)
    logging.info(doc_summary)

    logging.info("-------- GEN TITLE ------------------")

    llm_chain = LLMChain(
        llm=llm,
        prompt=PromptTemplate.from_template(PROMPT_title_template)
    )
    r = llm_chain(doc_summary)
    title = r["text"]
    logging.info(title)


    return (doc_summary, title, split_docs)

def generate_lesson(llm:AzureChatOpenAI, topic:dict) -> str:
    
    llm_chain = LLMChain(
        llm=llm,
        prompt=PromptTemplate.from_template(PROMPT_generate_lesson)
    )
    for chunk in topic["chunks"]:
        # logging.info(chunk)
        # TODO more complex logic, currently only from first chunk
        for guid,chunk_text in chunk.items():
            res = llm_chain(chunk_text)
            logging.info(res["text"])
            return res["text"]
    return "n/a"

def generate_test_from_lesson(llm:AzureChatOpenAI, lesson_text:str) -> list[dict]:
    llm_chain = LLMChain(
        llm=llm,
        prompt=PromptTemplate.from_template(PROMPT_generate_assesment)
    )
    # random_chunks = random.sample(chunks, 5)
    
    # assessments = []
    # for chunk in topic["chunks"]:
    #     # logging.info(chunk)
    #     for guid,chunk_text in chunk.items():
    #         r = llm_chain(chunk_text)
    #         # logging.info("[{"+r["text"])
    #         assessment = json.loads("[{"+r["text"])
    #         assessments.extend(assessment)
    r = llm_chain(lesson_text)
    assessment = json.loads("[{"+r["text"])
    return assessment

def update_document(id: str, lessonText:str, lessonAssessment:dict) -> dict[str, any]:

    logging.info("-------- DOC UPDATE INIT ---------- ")
    # logging.info(id)
    try:
        # test
        # id = "6480eb2d-0a05-43ab-b224-07c57480f88a"
        client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
        database = client.get_database_client("tmtdb")
        container = database.get_container_client("topics")


        read_item = container.read_item(item=id, partition_key=id)
        # read_item['state'] = "assessing"
        read_item['state'] = "ready"

        # TODO: update lesson text and assessment
        lessons = [{ "id": str(uuid.uuid4()), "title":"Lesson 1","text": lessonText, "state":"NEW", "lessonQuestions": lessonAssessment }]
        read_item['lessons'] = lessons
        response = container.upsert_item(body=read_item)
    except:
        logging.info("-------- DOC UPDATE ERROR ---------- ")
    return response

@GenerateLesson.function_name(name="generatelesson")
@GenerateLesson.service_bus_topic_trigger(arg_name="message", 
                            #    topic_name="SERVICEBUS_TOPIC_NAME", 
                               connection="SERVICEBUS_CONNECTION_STRING", 
                                topic_name="assessedTopic",
                                subscription_name="generate_lesson",
                            #    subscription_name="SERVICEBUS_SUBSCRIPTION_NAME"
                               )
def generatelesson(message: func.ServiceBusMessage):
    logging.info("-------- ServiceBus trigger function starterd --------")
    logging.getLogger("azure").setLevel(logging.ERROR)
    topic_id = None
    try:
        message_body = message.get_body().decode("utf-8")
        # logging.info("Message Body: " + message_body)
        message_body_json = json.loads(message_body)
        # logging.info("Message Body: " + json.dumps(message_body_json))
        topic_id = message_body_json["topic"]
    
    except ValueError:
        return func.HttpResponse(
             "Vaule Error",
             status_code=400
        )

    # initialize LLM
    llm = AzureChatOpenAI(temperature=0, 
                      model_name="gpt-35-turbo", 
                      deployment_name="gpt-35-turbo", 
                      openai_api_base=os.getenv("OPENAI_API_BASE"), 
                      openai_api_key=os.getenv("OPENAI_API_KEY"), 
                      openai_api_version=os.getenv("OPENAI_API_VERSION") )

    # get document from DB based on GUID
    topic = get_topic(topic_id)
 
    doc_summary = None

    if topic is None:
        logging.info("Document doesn't exist")
    else:
        # (doc_summary, title, chunks) = summarize_document(llm, topic)
        logging.info("-------- TOPIC DETAILS ---------- ")
        logging.info(topic)

    llm = AzureChatOpenAI(temperature=0.7, 
                      model_name="gpt-4", 
                      deployment_name="gpt-4", 
                      openai_api_base=os.getenv("OPENAI_API_BASE"), 
                      openai_api_key=os.getenv("OPENAI_API_KEY"), 
                      openai_api_version=os.getenv("OPENAI_API_VERSION") )

    logging.info(f"----- GEN LESSON --------")
    lesson_text = generate_lesson(llm, topic)

    llm = AzureChatOpenAI(temperature=0.7, 
                      model_name="gpt-35-turbo", 
                      deployment_name="gpt-35-turbo", 
                      openai_api_base=os.getenv("OPENAI_API_BASE"), 
                      openai_api_key=os.getenv("OPENAI_API_KEY"), 
                      openai_api_version=os.getenv("OPENAI_API_VERSION") )

    logging.info(f"----- GEN LESSON ASSESSMENT --------")
    lessson_assessments = generate_test_from_lesson(llm, topic)

    update_document(topic_id, lesson_text, lessson_assessments)

    logging.info("--------DONE----------")
