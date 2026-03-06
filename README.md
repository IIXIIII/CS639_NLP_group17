# LLM Agents in Operating System Environments

Course project on evaluating **LLM-based agents** using the **AgentBench Operating System (OS) domain**.  
Our goal is to study how LLM agents perform in **interactive command-line tasks** and analyze common **failure modes in long-horizon tasks**.

---

## Team Members and Responsibilities

| Member | Responsibility |
|---|---|
| Jingyu Huang | Method implementation: OS evaluation pipeline, prompt engineering, and model inference |
| Wanyi Chen | Literature review on LLM agents and long-horizon reasoning |
| Leyan Chen | Dataset analysis: exploratory analysis of OS tasks, task complexity, and horizon length |
| Yanting Guo | Experiment design and failure taxonomy |
| Guangwen Xiong | Project coordination, timeline planning, and report integration |
| Hunter Zhang | Slides for proposal and final presentation |

---

## Project Overview

This project investigates the generalization ability of **LLM-based agents** in interactive environments.

We use the **Operating System (OS) domain of AgentBench**, where an agent must translate natural language instructions into executable **bash commands** and interact with the system environment.

Tasks involve:

- Retrieving information from the system (**QA tasks**)
- Modifying system state using shell commands (**operation tasks**)

The OS benchmark contains **144 test tasks** with an average of **~8 interaction rounds per task**.

---

## Repository Structure  
data/ OS dataset and metadata  
experiments/ scripts for running agent evaluations  
analysis/ dataset analysis and failure analysis  
results/ experiment outputs  
report/ project report  


---

## Project Goals

1. Run baseline evaluations of LLM agents on OS tasks  
2. Perform exploratory **dataset analysis**  
3. Analyze common **failure modes** in multi-step tasks  
4. Explore potential improvements for agent performance
