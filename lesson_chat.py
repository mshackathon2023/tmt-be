import logging
import azure.functions as func
import uuid
import json
from azure.cosmos import CosmosClient, PartitionKey
import azure.cosmos.exceptions as cosmos_exceptions
import os


from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema.document import Document

from langchain.chat_models import AzureChatOpenAI
from langchain import LLMChain, PromptTemplate


from prompt_utils import PROMPT_RAG_generate_answer

from faker import Faker

def generate_random_sentence():
    fake = Faker()
    return fake.sentence()



def query_knowledgebase(query:str, chunks: list) -> list[Document]:
    logging.info("-------- QUERYING KNOWLEDGE BASE ------------------")
    embeddings = OpenAIEmbeddings(
        openai_api_base=os.environ["OPENAI_API_BASE"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_api_version=os.environ["OPENAI_API_VERSION"],
        deployment="text-embedding-ada-002")
    
    # get documewnts from chunks
    chunks_docs = []
    # chunk_embeddings = []
    for chunk in chunks:
        for chunk_id,text in chunk.items():
            # chunk_embeddings.append(embeddings.embed_documents([text]))
            chunks_docs.append(Document(page_content=text, metadata={"id":chunk_id}))
    

    # (chunks_text, chunks_embeddings) = calculate_embeddings_on_chunks(chunks)
    # create FAISS index from documents using Azure OpenAI Embeddings
    db = FAISS.from_documents(chunks_docs, embeddings)

    # query = "Who is father of king Charles II?"

    # find similar documents
    docs = db.similarity_search(query)

    logging.info(f"query: {query}")
    for doc in docs:
        logging.info(f'similar document ({doc.metadata["id"]}): {doc.page_content}')

    return docs

def generate_answer_from_docs(query:str, docs: list[Document]) -> str:
    if not docs:
        return "I'm sorry, I don't know the answer to that."
    
    logging.info("-------- GENERATE ANSWER ------------------")
    logging.info(f"query: {query}")
    logging.info(f"docs count: {len(docs)}")

    llm = AzureChatOpenAI(temperature=0.7, 
                      model_name="gpt-35-turbo", 
                      deployment_name="gpt-35-turbo", 
                      openai_api_base=os.getenv("OPENAI_API_BASE"), 
                      openai_api_key=os.getenv("OPENAI_API_KEY"), 
                      openai_api_version=os.getenv("OPENAI_API_VERSION") )

    llm_chain = LLMChain(
        llm=llm,
        prompt=PromptTemplate.from_template(PROMPT_RAG_generate_answer)
    )
    docs_text_only = ""
    for doc in docs:
        docs_text_only += doc.page_content + "\n"
    try:
        res = llm_chain({'docs': docs_text_only, 'question': query})
        answer = res["text"]
        logging.info(answer)
    except Exception as e:  
        logging.warn(f"error: {e}")
        answer = None

    # return the first document's content
    return answer

LessonChat = func.Blueprint()

@LessonChat.route(route="lessonchat/{topic}/{lesson}", methods=["POST"])
def lessonchat(req: func.HttpRequest) -> func.HttpResponse:
    logging.getLogger("azure").setLevel(logging.ERROR)

    # Get topic ID from route parameter
    topic_id = req.route_params.get("topic")
    logging.info(f"Getting topic {topic_id}")

    # Get lesson ID from route parameter
    lesson_id = req.route_params.get("lesson")
    logging.info(f"Getting lesson {lesson_id}")

    # Get messages from request body - provides a chat history
    messages = req.get_json()


    # Connect to Cosmos DB
    client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
    database = client.get_database_client("tmtdb")
    container = database.get_container_client("topics")

    # Query lessons from Cosmos DB
    try:
        items = list(container.query_items(
            query="SELECT c.chunks FROM c WHERE c.id=@topic_id",
            parameters=[
                {"name": "@topic_id", "value": topic_id}
            ],
            enable_cross_partition_query=False
        ))


    except:
        return func.HttpResponse(
            f"Error when quering for topic {topic_id}",
            headers = {"Content-Type": "application/json"},
            status_code=400
        )

    # Prepare chunks
    chunks = items[0]["chunks"]

    # TODO use message history in conversation, chunks to System message

    # get question from messages as last message
    question = messages[-1]["content"]
    logging.info("-------- EXTRACTED Question ------------------")
    logging.info(f"question: {question}")
    
    docs_matching_query = query_knowledgebase(question, chunks)

    answer = generate_answer_from_docs(question,docs_matching_query)

    # Prepare messages - MOCK ONLY
    # messages.append({"role":"assistant", "content": generate_random_sentence()})
    messages.append({"role":"assistant", "content": answer})


    return func.HttpResponse(
        # json.dumps('[{"role":"user", "content":"user said"}, {"role":"assistant", "content":"assistant replied"}]'),
        json.dumps(messages),
        headers = {"Content-Type": "application/json"},
        status_code=200
    )