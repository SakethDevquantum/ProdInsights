# %%
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, PeftConfig
from huggingface_hub import login

from langgraph.graph import StateGraph, START, END
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import Literal, List ,Optional, TypedDict, Any
from pathlib import Path
from asgiref.sync import sync_to_async

import os, sys, threading, json, django, asyncio

# %%
model=ChatOllama(model=' ')

# %%
class InputModel(BaseModel):
    flaws:Optional[List[str]]=Field(default=None, description="Specific problems or issues mentioned in the reviews. Only include what customers actually complained about. Do not include what they told, directly use formal tone only.")
    strengths:Optional[List[str]]=Field(default=None, description="Good features or benefits mentioned in the reviews. Only include what customers actually praised. Do not repeat their words exactly, tell what they liked in product and use FORMAL TONE only.")
    overall_rating:Optional[float]=Field(default=None, description="Rating from 0 to 5. Use 0=very bad, 1=bad, 2=poor, 3=average, 4=good, 5=excellent. Choose one number based on overall sentiment. You can also use decimals eg: 3.5 etc but only to one decimal place")

# %%
class ResponseModel(BaseModel):
    places_to_fix:Optional[List[str]]=Field(default=None, description="List specific areas or components that need improvement. Match these to the flaws mentioned. Use Formal Tone only.")
    Recommendations:Optional[List[str]]=Field(default=None, description="Suggest specific, practical actions to fix each problem. Be clear and direct. Use Formal Tone only.")

# %%
class StateSchema(TypedDict):
    raw_reviews:Optional[str]
    doc_text:Optional[str]=""
    product_name:Optional[str]
    flaws:Optional[List[str]]
    strengths:Optional[List[str]]
    weaknesses:Optional[List[str]]
    product_rating:Optional[float]
    places_to_fix:Optional[List[str]]
    recommendations:Optional[List[str]]

# %%
vector_stores=Chroma(collection_name="model_collections", embedding_function=OllamaEmbeddings(model=" "), persist_directory='vector_stores')
model=ChatOllama(model=" ")

# %%
data_folder=r'D:\SAKETH\Auto_insighter\project\project2\apps\api\app\myApp\Cache'
doc_text=''
files=os.listdir(data_folder)
if(len(files)==1):
    file=files[0]
    print(file)
    loader=None
    if(file.endswith(".pdf")):
        loader=PyPDFLoader(f'{data_folder}/{file}')
    elif(file.endswith(".docx")):
        loader=Docx2txtLoader(f'{data_folder}/{file}')
    elif(file.endswith(".txt")):
        loader=TextLoader(f'{data_folder}/{file}')
    if loader is not None:
        docs=loader.load()
        doc_text="\n".join(doc.page_content for doc in docs)

# %%
def validate(schema:StateSchema):
    llm=model.with_structured_output(InputModel)
    reviews_text = schema['raw_reviews'][:14000]
    
    response=llm.invoke(
        f"""TASK: Extract product information from customer reviews.

PRODUCT: {schema['product_name']}

REVIEWS:
{reviews_text}

INSTRUCTIONS:
1. Read the reviews carefully.
2. Extract FLAWS - what customers complained about (actual problems mentioned)
3. Extract STRENGTHS - what customers liked (actual benefits mentioned)
4. Extract RATING - the overall sentiment rating 0-5 (0=very bad, 5=excellent)
5. USE FORMAL TONE ONLY AND GIVE RESPONSES IN A RESPECTFUL AND DECENT MANNER

Focus ONLY on what is actually mentioned in the reviews. Do not make up information.
If a field is not mentioned, leave it empty.
"""
    )
    print(f"Validate response: {response}")
    schema['flaws']=response.flaws if response.flaws else ["No flaws seen"]
    schema['strengths']=response.strengths if response.strengths else ["The prduct has no strengths"]
    schema['product_rating']=response.overall_rating if response.overall_rating else 0.0

    return schema

def fix(schema:StateSchema):
    llm=model.with_structured_output(ResponseModel)
    prompt=f"""TASK: Generate solutions to fix product problems.

PRODUCT: {schema.get('product_name')}

THESE ARE THE FLAWS THAT THE PRODUCT HAS, USE THESE FLAWS TO DELIVER THE PLACES TO FIX AND IT SHOULD BE FROM THE FLAWS ONLY, THE "places_to_fix" must contain all the flaws that you will see below:
{schema.get('flaws')}

USE THE ABOVE FLAWS TO ALSO GIVE RECOMMENDATIONS ON WHAT TO DO TO FIX THE FLAWS AND THEY SHOULD BE REALISTIC

POSITIVE ASPECTS TO MAINTAIN(STRENGTHS):
{schema.get('strengths')}

CURRENT RATING OF THE PRODUCT: {schema.get('product_rating')}/5

INSTRUCTIONS:
1. For each problem listed, suggest a specific fix or improvement and whatever the problem that is spoken off in the flaws, they must be included. If the field for flaws is empty then ignore it.
2. Write clear, actionable recommendations for the recommendations section based on what flaws you saw.
3. Focus on realistic solutions based on the problems mentioned based on what is asked,
4. Address all those in a formal tone only.

Generate fixes that directly address the listed problems."""
    
    response=llm.invoke(prompt)
    print(f"Fix response: {response}")
    schema['places_to_fix']=response.places_to_fix if response.places_to_fix else ["No place to fix, the product is just fine"]
    schema['recommendations']=response.Recommendations if response.Recommendations else ["Not much recommendations are neccessary as the product is already heavily optimized"]
    return schema

# %%
graph=StateGraph(StateSchema)
graph.add_node("validate", validate)
graph.add_node("fix", fix)

graph.add_edge(START, "validate")
graph.add_edge("validate", "fix")
graph.add_edge("fix", END)

workflow=graph.compile()

# %%
import asyncio

async def main():
    from apps.api.app.myApp.app_views.rough import get_rows
    from apps.scrapper.review_scraper import get_product_reviews

    table_rows = await sync_to_async(get_rows)()
    last_row = table_rows[-1]
    product_name = last_row.human_query
    eg_product = "PS5 gaming console"
    scraped_content = await sync_to_async(get_product_reviews)(product_name)
    
    print(f"Product name: {product_name}")
    print(f"Scraped content length: {len(scraped_content)}")
    print(f"First 500 chars of scraped content: {scraped_content[:500]}")
    
    model_response = workflow.invoke({'raw_reviews':scraped_content, 'product_name':product_name, 'doc_text':""})
    print(model_response)
    
    return model_response, last_row.id

if __name__ == "__main__":

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    MYAPP_ROOT = PROJECT_ROOT / 'apps' / 'api' / 'app' / 'myApp'
    if str(MYAPP_ROOT) not in sys.path:
        sys.path.insert(0, str(MYAPP_ROOT))
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myApp.settings')
    django.setup()

    model_response, last_row_id = asyncio.run(main())
    
    

    # %%
    print(model_response['flaws'])
    print(model_response['places_to_fix'])
    print(model_response['product_rating'])
    print(model_response['recommendations'])
    print(model_response['strengths'])

    # %%
    model_text = f"""

PRODUCT NAME: {model_response["product_name"]}

PRODUCT RATING: {model_response["product_rating"]}/5.0

PROS:

{chr(10).join("➤ "+pro for pro in model_response["strengths"])}

CONS:

{chr(10).join("➤ "+con for con in model_response['flaws'])}

PLACES THAT YOU NEED TO LOOK AFTER:

{chr(10).join("➤ "+place for place in model_response['places_to_fix'])}

FURTHER RECOMMENDATIONS:

{chr(10).join("➤ "+recomm for recomm in model_response['recommendations'])}
"""

    model_text

    # %%
    print(model_text)

    Chats = django.apps.apps.get_model('app_views', 'Chats')
    model_response_json = json.dumps(model_text)
    Chats.objects.filter(id=last_row_id).update(model_response=model_response_json)
    print(f"Successfully edited in the database (ID: {last_row_id})")
