import os
# Importing the necessary packages
import ast
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI
from flask import *


api_key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

mysql_uri = 'mysql+mysqlconnector://root:admin@127.0.0.1/assets'

db = SQLDatabase.from_uri(mysql_uri)

llm = ChatOpenAI(model = "gpt-3.5-turbo", temperature=0)

app = Flask(__name__)

examples = [
    {
        "input": "What are the total CBM (Cubic Meters) for each fulfillment in 2023 from cat4",
        "query": "SELECT LINE_KEY, SUM(TOTAL_CBM) AS Total_CBM FROM `cat4_sample (1)` WHERE YEAR = 2023 GROUP BY LINE_KEY",
    },
    {
        "input": "How many cartons were shipped for each fulfillment in 2023 from cat9",
        "query": "SELECT LINE_KEY, SUM(NUMBER_OF_CARTONS) AS Total_Cartons_Shipped FROM `cat9_sample (1)` WHERE YEAR = 2023 GROUP BY LINE_KEY",
    },
    {
        "input": "What is the total weight of freight (in kg) shipped via sea transport mode in 2023 from cat4",
        "query": "SELECT SUM(WEIGHT_OF_FREIGHT_KG) AS Total_Weight_Freigh FROM `cat4_sample (1)` WHERE YEAR = 2023 AND TRANSPORT_MODE = 'Sea'",
    },
    {
        "input": "How many assets were supplied by each supplier in 2024 from the asset table?",
        "query": "SELECT ASSET_SUPPLIERS, COUNT(*) AS Asset_Count FROM asset WHERE YEAR = 2024 GROUP BY ASSET_SUPPLIERS",
    },
    {
        "input": "What are the distinct loading ports used in 2023 for cat9",
        "query": "SELECT DISTINCT LOADING_PORT FROM `cat9_sample (1)` WHERE YEAR = 2023",
    },
    {
        "input": "Retrieve the client names and corresponding asset family from fulfilled orders in 2024.",
        "query": "SELECT a.CLIENT_NAME, a.ASSET_FAMILY FROM asset a INNER JOIN `cat4_sample (1)` c4 ON a.LINE_KEY = c4.LINE_KEY WHERE c4.YEAR = 2024",
    },
    {
        "input": "Show the loading and discharging ports along with the associated asset descriptions for fulfilled orders in 2023.",
        "query": "SELECT c9.LOADING_PORT, c9.DISCHARGING_PORT, a.ASSET_DESCRIPTION FROM `cat9_sample (1)` c9 INNER JOIN asset a ON c9.LINE_KEY = a.LINE_KEY WHERE c9.YEAR = 2023",
    },
    {
        "input": "List the asset names and corresponding gross weights per carton for fulfilled orders in 2023.",
        "query": "SELECT a.ASSET_NAME, c9.GROSS_WEIGHT_PER_CARTON FROM asset a INNER JOIN `cat9_sample (1)` c9 ON a.LINE_KEY = c9.LINE_KEY WHERE c9.YEAR = 2023",
    },
    {
        "input": "Show the fulfillment dates, client names, and associated raw material names for all fulfilled orders in 2022.",
        "query": "SELECT c4.FULFILL_DATE, c4.CLIENT, am.RAW_MATERIAL_NAME FROM `cat4_sample (1)` c4 INNER JOIN `asset material` am ON c4.LINE_KEY = am.LINE_KEY AND c4.YEAR = am.YEAR WHERE c4.YEAR = 2022",
    },
    {
        "input": "Retrieve the loading and discharging countries along with the asset subfamily for fulfilled orders in 2023.",
        "query": "SELECT c9.LOADING_COUNTRY, c9.DISCHARGING_COUNTRY, a.ASSET_SUBFAMILY FROM `cat9_sample (1)` c9 INNER JOIN asset a ON c9.LINE_KEY = a.LINE_KEY WHERE c9.YEAR = 2023",
    }
]

example_prompt = PromptTemplate.from_template("User_input: {input} \n SQL Query: {query}")
prompt = FewShotPromptTemplate(
    examples=examples,
    example_prompt = example_prompt,
    prefix = "You are a MySQL expert. Given an input question, first create a syntactically correct MySQL query to run, then look at the results of the query and return the answer to the input question.Given an input question, create a syntactically correct SQLite query to run. Unless otherwise specificed, do not return more than {top_k} rows.\n\nHere is the relevant table info: {table_info}\n\nBelow are a number of examples of questions and their corresponding SQL queries. Our Database contains 4 tables, tables are connected by LINE_KEY and YEAR you can join the tables in your query based on this information. Wrap each column name in backticks (`) to denote them as delimited identifiers.",
    suffix = "User input: {input}\n SQL Query: ",
    input_variables=["input", "top_k", "table_info"],
)

chain = create_sql_query_chain(llm, db, prompt)

query = chain.invoke({'question': "List the client names, asset categories, and associated gross weights per carton for all fulfilled orders in 2024."})

output = db.run(query)

def question_invoke(input_text):
    chain = create_sql_query_chain(llm, db, prompt)

    query = chain.invoke({'question': input_text})
    
    return query

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/', methods=['GET', 'POST'])
def msg():
    new_query = request.form['new_query']
    invoke = question_invoke(new_query)
    db = SQLDatabase.from_uri(mysql_uri)
    output_list = ast.literal_eval(db.run(invoke))
    
    return render_template("index.html", output_list=output_list)

if __name__ == "__main__":
    app.run()