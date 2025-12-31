import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
    api_key=os.getenv("API_KEY"),
    azure_deployment=os.getenv("AZURE_DEPLOYMENT"),  # or your deployment
    api_version=os.getenv("API_VERSION"),  # or your api version
)
