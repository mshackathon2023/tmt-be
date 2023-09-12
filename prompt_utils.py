from langchain import LLMChain, PromptTemplate

# applied to each chunk of document
PROMPT_summarize_map_template = """The following is a set of documents
    {docs}
    Based on this list of docs, please identify the main themes 
    Helpful Answer:"""

# applies to whole summary
PROMPT_summarize_reduce_template = """You are a teacher. Your task is to summarize documents to be understandable. The following is set of summaries:
    {doc_summaries}
    Take these and distill it into a final, consolidated summary of the main themes. 
    Helpful Answer:"""

# prompt to generate template from summary
PROMPT_title_template = """Generate short title based on the text below. Short title consists of up to four words.

    Text:
    {docs}
     
    Helpful Title:"""

# prompt to generate assesment quiz from give text
PROMPT_generate_assesment = """Generate a single choice quiz from the text below. 

Text:
{text}

Follow the rules when generating quiz:
- Quiz should contain 5 questions. 
- Answers shoud be more than single word.
- Questions should match high school knowledge level.
- Questions should spark curiosity.
- Questions should not cherry-pick detatils.
- Questions should cover important facts in the test.
- Questions should cover general knowledge. 
- Questions **must** be formated as validlist of JSON documents representing each questions.
- Append a list of correct answer for each question.

==> Example:
[{
    "Q1": "Why did the Maya civilization decline by about 900 CE ?",
    "choices": [
        {"A": "They were invaded by outsiders"},
        {"B": "They abandoned their large population centers"},
        {"C": "They were hit with a deadly virus"},
        {"D": "They lost the ability to grow crops"},
    ],
    "Answer": "B"
}]
<== End of Example

Questions:
"""