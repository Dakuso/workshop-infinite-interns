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

class Section(BaseModel):
    name: str = Field(description="Name for this section of the report.")
    description: str = Field(description="Overview of the topics covered.")

class Sections(BaseModel):
    sections: List[Section] = Field(description="Sections of the report.")

planner = llm.with_structured_output(Sections)

# --- 4. Graph State ---
from typing_extensions import TypedDict

class State(TypedDict):
    topic: str
    sections: list[Section]
    completed_sections: Annotated[list, operator.add]
    final_report: str

class WorkerState(TypedDict):
    section: Section
    completed_sections: Annotated[list, operator.add]

# --- 5. Nodes ---
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send

def orchestrator(state: State):
    report_sections = planner.invoke([
        SystemMessage(content="Generate a plan for the report."),
        HumanMessage(content=f"Here is the report topic: {state['topic']}"),
    ])
    logging.info("Planning report: %s", report_sections.sections)
    return {"sections": report_sections.sections}

def llm_call(state: WorkerState):
    section = llm.invoke([
        SystemMessage(content="Write a report section."),
        HumanMessage(
            content=f"Section name: {state['section'].name}\nDescription: {state['section'].description}"
        ),
    ])
    return {"completed_sections": [section.content]}

def synthesizer(state: State):
    sections = state["sections"]
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

def assign_workers(state: State):
    return [Send("llm_call", {"section": s}) for s in state["sections"]]

# --- 6. Build Graph ---
from langgraph.graph import StateGraph, START, END

builder = StateGraph(State)
builder.add_node("orchestrator", orchestrator)
builder.add_node("llm_call", llm_call)
builder.add_node("synthesizer", synthesizer)

builder.add_edge(START, "orchestrator")
builder.add_conditional_edges("orchestrator", assign_workers, ["llm_call"])
builder.add_edge("llm_call", "synthesizer")
builder.add_edge("synthesizer", END)

workflow = builder.compile()

# --- 7. Run and Save Output ---
topic = "if all humans jump at the exact same time, what happens?"
state = workflow.invoke({"topic": topic})

# Save as Markdown
output_dir = Path("workflows/email-digest/report_output")
output_dir.mkdir(exist_ok=True)
output_file = output_dir / (topic.replace(' ', '_') + '.md')

with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"# Recovery Report\n\n## Topic: {topic}\n\n")
    f.write(state["final_report"])

print(f"Report saved to: {output_file.resolve()}")
