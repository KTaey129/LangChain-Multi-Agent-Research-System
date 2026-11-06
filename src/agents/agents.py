from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.tools.tools import web_search, scrape_url
from dotenv import load_dotenv

load_dotenv()

# model initialization
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 1st agent: Search Agent
def build_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search],
    )

# 2nd agent: Reader Agent
def build_reader_agent():
    return create_agent(
        model=llm,
        tools=[scrape_url],
    )

# Using LCL chain. LCEL: LangChain Execution Language which is a language for defining the execution flow of LangChain agents and tools. It allows you to specify how agents and tools should interact with each other to achieve a specific goal.
# Writer chain
writer_prompt = ChatPromptTemplate.from_messages([
    # builds a prompt with a system message (the persona) and a human message (the task).
    ("system", "You are an expert research wirter. Wirte clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.
    
Topic: {topic}

Research Gathered:
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list all URLs found in the research)

Be detailed, factual, and professional.""")
])

writer_chain = writer_prompt | llm | StrOutputParser()
# StrOutputParser turns the reply object into a plain str.

# critic chain
critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    ("human", """Review the research report below and evaluate it strictly.
    
Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to improve:
- ...
- ...

One line verdict:
..."""),
])

critic_chain = critic_prompt | llm | StrOutputParser()