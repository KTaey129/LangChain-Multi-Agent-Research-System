from src.tools.tools import web_search, scrape_url

# results = scrape_url("https://ai.google/research")
# print(results)

# you can also invoke the tool directly with a query
# invoke is a method provided by the LangChain tool decorator that allows you to call the tool as if it were a regular function, passing in the required parameters.
r = web_search.invoke("What is the latest research on AI for climate change mitigation?")
print(r)