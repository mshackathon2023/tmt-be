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
PROMPT_generate_assesment_old = """Generate a single choice quiz from the text below. 

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

PROMPT_generate_assesment = """Generate a single choice quiz from the text below. 

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
- Each question **must** have indicator (true/false) for the correct answer.

==> Example:
[{{
            "q_id": 0,
            "text": "Why did the Maya civilization decline by about 900 CE ?",
            "answers": [
                {{ "a_id": 0, "text": "They were invaded by outsiders", "correct": false}},
                {{ "a_id": 1, "text": "They abandoned their large population centers", "correct": true}},
                {{ "a_id": 2, "text": "They were hit with a deadly virus", "correct": false}},
                {{ "a_id": 3, "text": "They lost the ability to grow crops", "correct": false}}
             ]
}}]
<== End of Example

Questions:
[{{"""

PROMPT_generate_lesson = """You are a teacher. Your task is to present complex topics in a simple way. Also you generate study plans and lessons texts for learning of various topics.

Generate lesson content from the TEXT bellow:

TEXT:
{text}

Follow the rules when generating lesson content:
- Lesson content chould start with outline which consists of individual topics.
- Lesson content should contain most important parts of text, historic events, civilisations, geographic etc.
- Topics should be easy to read.
- Lesson content should cover and explain the main events.

Lesson content:"""