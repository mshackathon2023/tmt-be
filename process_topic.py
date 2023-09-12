import logging
from time import sleep
import uuid
import json
import os 

import azure.functions as func
from azure.cosmos import CosmosClient

from langchain.chat_models import AzureChatOpenAI
from langchain import LLMChain, PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ReduceDocumentsChain, MapReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.schema.document import Document
import tiktoken

from prompt_utils import PROMPT_summarize_reduce_template, PROMPT_summarize_map_template, PROMPT_title_template

ProcessTopic = func.Blueprint()

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.encoding_for_model(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def get_document_from_db(id: str) -> Document:
      # DBG document
    document = """
1.1 The Americas
By the end of this section, you will be able to:
•Locate on a map the major American civilizations before the arrival of the Spanish
•Discuss the cultural achievements of these civilizations
•Discuss the differences and similarities between lifestyles, religious practices, and
customs among the native peoples
Between nine and fifteen thousand years ago, some scholars believe that a land bridge existed between
Asia and North America that we now call Beringia . The first inhabitants of what would be named the
Americas migrated across this bridge in search of food. When the glaciers melted, water engulfed Beringia,
and the Bering Strait was formed. Later settlers came by boat across the narrow strait. (The fact that
Asians and American Indians share genetic markers on a Y chromosome lends credibility to this migration
theory.) Continually moving southward, the settlers eventually populated both North and South America,
creating unique cultures that ranged from the highly complex and urban Aztec civilization in what is now
Mexico City to the woodland tribes of eastern North America. Recent research along the west coast of
South America suggests that migrant populations may have traveled down this coast by water as well as
by land.
Researchers believe that about ten thousand years ago, humans also began the domestication of plants
and animals, adding agriculture as a means of sustenance to hunting and gathering techniques. With this
agricultural revolution, and the more abundant and reliable food supplies it brought, populations grew
and people were able to develop a more settled way of life, building permanent settlements. Nowhere in
the Americas was this more obvious than in Mesoamerica ( Figure 1.3 ).
Figure 1.2 (credit: modification of work by Architect of the Capitol)8 Chapter 1 The Americas, Europe, and Africa Before 1492
This content is available for free at https:// cnx.org/content/col11740/1.3Figure 1.3 This map shows the extent of the major civilizations of the Western Hemisphere. In South America, early
civilizations developed along the coast because the high Andes and the inhospitable Amazon Basin made the interior
of the continent less favorable for settlement.
THE FIRST AMERICANS: THE OLMEC
        """
    
    logging.info("-------- DOC READ INIT ---------- ")
    sleep(1)
    logging.info(f"processing document: {id}")
    try:
        # test
        # id = "6480eb2d-0a05-43ab-b224-07c57480f88a"
        client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
        database = client.get_database_client("tmtdb")
        container = database.get_container_client("rawdocs")

        topic = container.read_item(
            item=id,
            partition_key=id
        )
        document = topic["text"]


        langchain_document = Document(page_content=document, metadata={"title":"n/a"})
        return langchain_document
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
        chunk_size=3000, chunk_overlap=200
    )
    split_docs = text_splitter.split_documents([document])

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

def update_document(id: str, summary:str, title:str, chunks:list[Document]) -> dict[str, any]:

    logging.info("-------- DOC UPDATE INIT ---------- ")
    # logging.info(id)
    try:
        # test
        # id = "6480eb2d-0a05-43ab-b224-07c57480f88a"
        client = CosmosClient.from_connection_string(os.environ["COSMOSDB_CONNECTION_STRING"])
        database = client.get_database_client("tmtdb")
        container = database.get_container_client("topics")


        read_item = container.read_item(item=id, partition_key=id)
        read_item['state'] = "assessing"
        # read_item['state'] = "ready"
        read_item['summary'] = summary
        read_item['title'] = title
        ch = []
        for chunk in chunks:
            guid = str(uuid.uuid4())
            ch.append({guid:chunk.page_content})
        read_item['chunks'] = ch
        response = container.upsert_item(body=read_item)
    except:
        logging.info("-------- DOC UPDATE ERROR ---------- ")
    return response

@ProcessTopic.function_name(name="processtopic")
@ProcessTopic.service_bus_topic_trigger(arg_name="message", 
                            #    topic_name="SERVICEBUS_TOPIC_NAME", 
                               connection="SERVICEBUS_CONNECTION_STRING", 
                                topic_name="newDocument",
                                subscription_name="process_topic",
                            #    subscription_name="SERVICEBUS_SUBSCRIPTION_NAME"
                               )
def processtopic(message: func.ServiceBusMessage):
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
    document = get_document_from_db(topic_id)
 
    doc_summary = None

    if document is None:
        logging.info("Document doesn't exist")
    else:
        (doc_summary, title, chunks) = summarize_document(llm, document)

    if doc_summary is not None:
        update_document(topic_id, doc_summary, title, chunks)

    logging.info("--------DONE----------")
