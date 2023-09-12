
OPENAI_API_TYPE="azure"
OPENAI_API_KEY="5f68487de0d4438ebc77e43d295dde0f"
OPENAI_API_BASE="https://openaimmafc1.openai.azure.com/"
OPENAI_API_VERSION="2023-07-01-preview"


from time import sleep
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.document_loaders import WebBaseLoader
from langchain.chains.summarize import load_summarize_chain

loader = WebBaseLoader("https://lilianweng.github.io/posts/2023-06-23-agent/")
docs = loader.load()


import tiktoken
def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.encoding_for_model(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

# go through the docs and see how many tokens each one has
for doc in docs:
    # for key, value in doc.metadata.items():
    #     print (key)
    print(doc.metadata["title"])
    print(num_tokens_from_string(doc.page_content, "gpt-3.5-turbo"))




# import os 
# # get environment variables
# OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

#todo use env variables
llm = AzureChatOpenAI(temperature=0, 
                      model_name="gpt-35-turbo", 
                      deployment_name="gpt-35-turbo", 
                      openai_api_base=OPENAI_API_BASE, 
                      openai_api_key=OPENAI_API_KEY, 
                      openai_api_version=OPENAI_API_VERSION )


# chain = load_summarize_chain(llm, chain_type="stuff")
# chain.run(docs)

##########################################################################################

from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents.stuff import StuffDocumentsChain

# Define prompt
prompt_template = """Write a concise summary of the following:
"{text}"
CONCISE SUMMARY:"""
prompt = PromptTemplate.from_template(prompt_template)

# Define LLM chain
# llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-16k")
llm_chain = LLMChain(llm=llm, prompt=prompt)

# Define StuffDocumentsChain
stuff_chain = StuffDocumentsChain(
    llm_chain=llm_chain, document_variable_name="text"
)

docs = loader.load()
print(stuff_chain.run(docs))



##########################################################################################

from langchain import LLMChain, PromptTemplate
from langchain.chains.mapreduce import MapReduceChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ReduceDocumentsChain, MapReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain

# llm = ChatOpenAI(temperature=0)

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

# # Note we can also get this from the prompt hub, as noted above
# reduce_prompt = hub.pull("rlm/map-prompt")

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
##########################################################################################
# Combining documents by mapping a chain over them, then combining results
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
split_docs = text_splitter.split_documents(docs)


# go through the docs and see how many tokens each one has
for doc in split_docs:
    # for key, value in doc.metadata.items():
    #     print (key)
    print(doc.metadata["title"])
    print(num_tokens_from_string(doc.page_content, "gpt-3.5-turbo"))


print(map_reduce_chain.run(split_docs))


##########################################################################################

from langchain import PromptTemplate, OpenAI, LLMChain

prompt_template = "What is a good name for a company that makes {product}?"
map_template = """The following is a set of documents
{docs}
Based on this list of docs, please identify the main themes 
Helpful Answer:"""


# llm = OpenAI(temperature=0)
llm_chain = LLMChain(
    llm=llm,
    prompt=PromptTemplate.from_template(map_template)
)

docs_summaries = []
for doc in split_docs:
    print("entering loop")
    # print(doc.metadata["title"])
    # print(num_tokens_from_string(doc.page_content, "gpt-3.5-turbo"))
    r = llm_chain(doc.page_content)
    docs_summaries.append({
            "title":doc.metadata["title"],
            "text":r["text"],
            "docs":r["docs"]
            })
    print("sleeping")
    sleep(5)
    print("woke up")

docs_summaries_prepared = ""
# go through the docs and see how many tokens each one has
for doc in docs_summaries:
    print("title:", doc["title"])
    print("text:", doc["text"])

    docs_summaries_prepared += f"{doc['text']}\n\n"

print(num_tokens_from_string(docs_summaries_prepared, "gpt-3.5-turbo"))

print(docs_summaries_prepared)

# Reduce
reduce_template = """The following is set of summaries:
{doc_summaries}
Take these and distill it into a final, consolidated summary of the main themes. 
Helpful Answer:"""
reduce_prompt = PromptTemplate.from_template(reduce_template)



# llm = OpenAI(temperature=0)
llm_chain = LLMChain(
    llm=llm,
    prompt=PromptTemplate.from_template(reduce_template)
)


doc_summary_final = llm_chain(docs_summaries_prepared)

for key, value in doc_summary_final.items():
    print (key)

print (doc_summary_final["text"])


##########################################################################################

from langchain.chains import (
    StuffDocumentsChain,
    LLMChain,
    ReduceDocumentsChain,
    MapReduceDocumentsChain,
)
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI

# This controls how each document will be formatted. Specifically,
# it will be passed to `format_document` - see that function for more
# details.
document_prompt = PromptTemplate(
    input_variables=["page_content"],
        template="{page_content}"
)
document_variable_name = "context"
# llm = OpenAI()
# The prompt here should take as an input variable the
# `document_variable_name`
prompt = PromptTemplate.from_template(
    "Summarize this content: {context}"
)
llm_chain = LLMChain(llm=llm, prompt=prompt)
# We now define how to combine these summaries
reduce_prompt = PromptTemplate.from_template(
    "Combine these summaries: {context}"
)
reduce_llm_chain = LLMChain(llm=llm, prompt=reduce_prompt)
combine_documents_chain = StuffDocumentsChain(
    llm_chain=reduce_llm_chain,
    document_prompt=document_prompt,
    document_variable_name=document_variable_name
)
reduce_documents_chain = ReduceDocumentsChain(
    combine_documents_chain=combine_documents_chain,
)
chain = MapReduceDocumentsChain(
    llm_chain=llm_chain,
    reduce_documents_chain=reduce_documents_chain,
)







# If we wanted to, we could also pass in collapse_documents_chain
# which is specifically aimed at collapsing documents BEFORE
# the final call.
prompt = PromptTemplate.from_template(
    "Collapse this content: {context}"
)
llm_chain = LLMChain(llm=llm, prompt=prompt)
collapse_documents_chain = StuffDocumentsChain(
    llm_chain=llm_chain,
    document_prompt=document_prompt,
    document_variable_name=document_variable_name
)
reduce_documents_chain = ReduceDocumentsChain(
    combine_documents_chain=combine_documents_chain,
    collapse_documents_chain=collapse_documents_chain,
)
chain = MapReduceDocumentsChain(
    llm_chain=llm_chain,
    reduce_documents_chain=reduce_documents_chain,
)
