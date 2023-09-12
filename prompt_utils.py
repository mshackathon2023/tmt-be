from langchain import LLMChain, PromptTemplate

# applied to each chunk of document
PROMPT_summarize_map_template = """The following is a set of documents
    {docs}
    Based on this list of docs, please identify the main themes 
    Helpful Answer:"""

# applies to whole summary
PROMPT_summarize_reduce_template = """You are a good high school teacher. The following is set of summaries:
    {doc_summaries}
    Take these and distill it into a final, consolidated summary of the main themes. 
    Helpful Answer:"""

# prompt to generate template from summary
PROMPT_title_template = """Generate short title based on the text below. Short title consists of up to four words.

    Text:
    {docs}
     
    Helpful Title:"""