from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputparser
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

# Using LCL chain. LCL: LangChain Language Model Chain which is a wrapper around the LLM that allows you to define a prompt template and output parser for structured output.
# Writer chain

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research wirter. Wirte clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.
    
Topic {topic}

Research Gathered:
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list all URLs found in the research)

Be detailed, factual, and professional.""")
])