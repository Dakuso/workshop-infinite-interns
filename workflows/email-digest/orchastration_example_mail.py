#!/usr/bin/env python
# coding: utf-8

# --- 1. Setup ---
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()  # Load API key etc.

# Logging
logging.basicConfig(
    filename="llm_trace.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

# --- 2. LLM Setup ---
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-3-5-sonnet-latest",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)

# --- 3. Pydantic Schema ---
from pydantic import BaseModel, Field
from typing import Annotated, List
import operator

class Task(BaseModel):
    name: str = Field(description="This is the name of the task or subtask we are about to solve")
    description: str = Field(description="Description of the task or subtasks activities.")

class Tasks(BaseModel):
    sections: List[Task] = Field(description="An exhaustive list of tasks to be performed.")

planner = llm.with_structured_output(Tasks)

class Classification(BaseModel):
    decision: str = Field(description="True for mails that concern me and require action on my part, False otherwise.")

spam_bot = llm.with_structured_output(Classification)

# --- 4. Graph State ---
from typing_extensions import TypedDict

class State(TypedDict):
    topic: str
    decision: str
    tasks: list[Task]
    completed_sections: Annotated[list, operator.add]
    final_report: str

class WorkerState(TypedDict):
    task: Task
    completed_sections: Annotated[list, operator.add]

# --- 5. Nodes ---
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send

def spam_protection(state: State):
    email_body = state['topic']
    spam_decision = spam_bot.invoke([
        SystemMessage(content="Decide whether the provided email is classified as Spam or not"),
        HumanMessage(content=f"Here is the Mail in question: {state['topic']}"),
    ])
    logging.info("Spam decision: %s", spam_decision.decision)
    print('############################', spam_decision)
    if spam_decision.decision in ('False', 'false'):
        return {'decision': spam_decision.decision, 'final_report': 'This email was classified as spam.'}
    else:
        return {'decision': spam_decision.decision}

def orchestrator(state: State):
    report_sections = planner.invoke([
        SystemMessage(content="Generate a plan for the report."),
        HumanMessage(content=f"Here is the report topic: {state['topic']}"),
    ])
    logging.info("Planning report: %s", report_sections.sections)
    return {"tasks": report_sections.sections}

def llm_call(state: WorkerState):
    section = llm.invoke([
        SystemMessage(content="Write a report section."),
        HumanMessage(
            content=f"Task name: {state['task'].name}\nDescription: {state['task'].description}"
        ),
    ])
    return {"completed_sections": [section.content]}

def synthesizer(state: State):
    sections = state["tasks"]
    completed_sections = state["completed_sections"]

    # Build Table of Contents
    toc_lines = ["## Table of Contents\n"]
    for i, section in enumerate(sections):
        anchor = section.name.lower().replace(" ", "-")
        toc_lines.append(f"- [{section.name}](#{anchor})")

    toc = "\n".join(toc_lines)

    # Build full report body with anchors
    report_lines = []
    for section, content in zip(sections, completed_sections):
        anchor = section.name.lower().replace(" ", "-")
        report_lines.append(f"## {section.name}\n\n{content.strip()}\n")

    report_body = "\n\n---\n\n".join(report_lines)

    # Combine everything
    full_report = f"# Report on {state['topic']}\n\n{toc}\n\n---\n\n{report_body}"

    return {"final_report": full_report}

def synthesizerv2(state: State):
    print('Hello World')
    return

def assign_workers(state: State):
    print('#########################', state)
    return [Send("llm_call", {"task": s}) for s in state["tasks"]]

def spam_router(state: State):
    if state['decision'] in ('False', 'True', 'false', 'true'):
        return state['decision']
    else:
        raise ValueError("Invalid decision value")

# --- 6. Build Graph ---
from langgraph.graph import StateGraph, START, END

builder = StateGraph(State)
builder.add_node("spam_protection", spam_protection)
builder.add_node("orchestrator", orchestrator)
builder.add_node("llm_call", llm_call)
builder.add_node("synthesizer", synthesizer)

# builder.add_edge(START, "orchestrator")
builder.add_edge(START, "spam_protection")
builder.add_conditional_edges(
    "spam_protection",
    spam_router,
    {
        'True': 'orchestrator',
        'False': END,
        'true': 'orchestrator',
        'false': END,
    }
)
builder.add_conditional_edges("orchestrator", assign_workers, ["llm_call"])
builder.add_edge("llm_call", "synthesizer")
builder.add_edge("synthesizer", END)

workflow = builder.compile()

# --- 6.5 visualize graph

# from PIL import Image

# # Generate and save PNG
# img = workflow.get_graph().draw_mermaid_png()
# with open("workflow.png", "wb") as f:
#     f.write(img)

# # Open the image (platform-dependent)
# Image.open("workflow.png").show()


# --- 7. Run and Save Output ---
topic = """Reminder to Think Before You Click!
Dear Client,

Our clients have seen a recent wave of “phishing” attempts in which scammers are impersonating Interactive Brokers. They send requests for urgent updates of client information (often tax or other key information) and include login links pointing to websites that appear legitimate but are actually fake websites.

If you click those links, you may inadvertently give bad actors access to your account.

The scammers continue to change their methods—sometimes sending texts, sometimes emails—but you can protect yourself by following a few simple rules:

    Check the domain name in your browser to see whether it is the official website of Interactive Brokers; if not, it is likely fake.
    When in doubt, directly access your account from the log in button on the Interactive Brokers website.


Interactive Brokers
Interactive Brokers (U.K.) Limited, FCA 208159. Unsubscribe

Message Reference Number: 5-17535689319040473-745673, Sent Date: 2025.07.26 18:28:54 -0400
MRN:GE3TKMZVGY4DSMZRHEYDIMBUG4ZXY3DFN5XC42DJNZSGK4TMNFXGOQDIN52G2YLJNQXGIZL4GV6DCNZVGM2TMOBZGMYTSMBUGA2DOMZNG42DKNRXGM%3D%3D%3D%3D%3D%3D:"""


topic = """
Hi Léon,

I hope you're doing well.

Could you please review the current version of the Security Dashboard and update it with the latest vulnerability data from the past two weeks? It would also be great if you could cross-check the EDR alerts to ensure they're accurately reflected in the risk scoring model.

Ideally, we’d like to have this ready by Friday afternoon so we can include it in the monthly reporting cycle. Let me know if anything is unclear or if you need access to any additional data sources.

Thanks in advance!

Best,
"""
    
state = workflow.invoke({"topic": topic})

# Save as Markdown
output_dir = Path("workflows/email-digest/report_output")
output_dir.mkdir(exist_ok=True)
output_file = output_dir / (topic.replace('\n', ' ').replace(' ', '_')[:30] + '.md')
with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"# Recovery Report\n\n## Topic: {topic}\n\n")
    f.write(state["final_report"])

print(f"Report saved to: {output_file.resolve()}")
