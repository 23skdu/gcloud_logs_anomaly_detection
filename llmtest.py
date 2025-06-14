#!/usr/bin/env python3
import os,argparse
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import create_extraction_chain
from langchain_core.runnables import chain
modelname = os.environ.get("MODELNAME","smollm2:135m")
parser = argparse.ArgumentParser(description="ask a question to a local Ollama LLM.")
parser.add_argument("question")
args = parser.parse_args()
question = (args.question)
template = """Question: {question} """
prompt = PromptTemplate(template=template, input_variables=["question"])
llm = OllamaLLM(model=modelname)
runnable = prompt | llm
response = runnable.invoke({"question": question}) 
print(response)

