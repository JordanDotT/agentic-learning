import re

# --- Mock tools ---
def search(query: str):
    database = {
        "population of canada": "39 million",
        "population of germany": "83 million",
    }
    return database.get(query.lower(), "Not found")

def calculator(expression: str):
    try:
        return str(eval(expression))
    except:
        return "Error"

# --- ReAct agent loop ---
def react_agent(question: str):
    print(f"Question: {question}\n")

    reasoning = "I need to find the population of Canada and Germany, then add them."
    print("Reasoning:", reasoning)

    # Step 1: Action - search for Canada
    action = "search('population of Canada')"
    print("Action:", action)
    obs1 = search("population of Canada")
    print("Observation:", obs1)

    # Step 2: Action - search for Germany
    action = "search('population of Germany')"
    print("Action:", action)
    obs2 = search("population of Germany")
    print("Observation:", obs2)

    # Step 3: Reason about results
    reasoning = f"Canada = {obs1}, Germany = {obs2}. Convert to numbers and add."
    print("Reasoning:", reasoning)

    # Extract numbers
    can = int(re.search(r'\d+', obs1).group())
    ger = int(re.search(r'\d+', obs2).group())

    # Step 4: Action - calculator
    action = f"calculator('{can} + {ger}')"
    print("Action:", action)
    obs3 = calculator(f"{can} + {ger}")
    print("Observation:", obs3)

    # Step 5: Final Answer
    answer = f"The combined population is about {obs3} million."
    print("\nFinal Answer:", answer)


# --- Run demo ---
react_agent("What is the population of Canada plus Germany?")
