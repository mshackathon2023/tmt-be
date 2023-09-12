import logging
import azure.functions as func
import uuid
import json

import os 

from time import sleep
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.document_loaders import WebBaseLoader
from langchain.chains.summarize import load_summarize_chain


from langchain import LLMChain, PromptTemplate
from langchain.chains.mapreduce import MapReduceChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ReduceDocumentsChain, MapReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain

from langchain.schema.document import Document

ProcessTopic = func.Blueprint()

import tiktoken
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

    langchain_document = Document(page_content=document, metadata={"title":"n/a"})
    return langchain_document

@ProcessTopic.function_name(name="processtopic")
@ProcessTopic.service_bus_topic_trigger(arg_name="message", 
                            #    topic_name="SERVICEBUS_TOPIC_NAME", 
                               connection="SERVICEBUS_CONNECTION_STRING", 
                                topic_name="newDocument",
                                subscription_name="process_topic",
                            #    subscription_name="SERVICEBUS_SUBSCRIPTION_NAME"
                               )
# def processtopic(message: func.ServiceBusMessage) -> func.HttpResponse:
def processtopic(message: func.ServiceBusMessage):
    logging.info('Python ServiceBus trigger function processed a request.')
    message_body = None
    try:
        message_body = message.get_body().decode("utf-8")
        logging.info("Python ServiceBus topic trigger processed message.")
        logging.info("Message Body: " + message_body)
        # logging.info("OpenaAI:"+os.getenv("OPENAI_API_BASE"))

    
    except ValueError:
        return func.HttpResponse(
             "Vaule Error",
             status_code=400
        )

    # Generate a unique ID for the new document
    guid = str(uuid.uuid4())

    # initialize LLM
    llm = AzureChatOpenAI(temperature=0, 
                      model_name="gpt-35-turbo", 
                      deployment_name="gpt-35-turbo", 
                      openai_api_base=os.getenv("OPENAI_API_BASE"), 
                      openai_api_key=os.getenv("OPENAI_API_KEY"), 
                      openai_api_version=os.getenv("OPENAI_API_VERSION") )

  
    # get document from DB based on GUID
    document = get_document_from_db(message_body)
    # logging.info("---------------------------")
    # logging.info(num_tokens_from_string(document, "gpt-3.5-turbo"))


    # Get Summary as map-reduce patttern from LangChain
    # Map
    map_template = """The following is a set of documents
    {docs}
    Based on this list of docs, please identify the main themes 
    Helpful Answer:"""
    map_prompt = PromptTemplate.from_template(map_template)
    map_chain = LLMChain(llm=llm, prompt=map_prompt)

    # Reduce
    reduce_template = """The following is set of summaries:
    {doc_summaries}
    Take these and distill it into a final, consolidated summary of the main themes. 
    Helpful Answer:"""
    reduce_prompt = PromptTemplate.from_template(reduce_template)


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
    # go through the docs and see how many tokens each one has
    for chunk in split_docs:
        logging.info("---------------------------")
        logging.info(chunk.metadata["title"])
        logging.info(num_tokens_from_string(chunk.page_content, "gpt-3.5-turbo"))

    

    logging.info("----------------- MAP REDUCE OUTPUT ----------")
    logging.info(map_reduce_chain.run(split_docs))

    # # Store raw document in Cosmos DB
    # rawDocuments.set(func.Document.from_dict({"id":guid, "text": text}))

    # # Create new topic record in Cosmos DB
    # topics.set(func.Document.from_dict({"id":guid, "state": "pending"}))

    # # Send message to Service Bus
    # message.set(json.dumps({"topic": guid}))

    # return func.HttpResponse(
    #     json.dumps({"topic": guid, "state":"assessing", "body": message_body}),
    #     headers = {"Content-Type": "application/json"},
    #     status_code=202
    # )