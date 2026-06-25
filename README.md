🚀 AutoDQ Analytics

An Intelligent Analytics Workflow Framework for Python

AutoDQ Analytics is an open-source Python framework that helps analysts, researchers, students, and organizations move from raw datasets to explainable insights.

Unlike traditional data cleaning libraries, AutoDQ is designed as an end-to-end analytics workflow framework. It profiles datasets, understands column semantics, diagnoses data quality issues, recommends statistically justified actions, previews proposed changes, and is being extended to automate the complete analytics lifecycle.

⸻

Vision

AutoDQ aims to become an intelligent analytics operating system for tabular data.

Instead of asking:

“How do I clean this dataset?”

AutoDQ answers:

* What is this dataset?
* What do these columns represent?
* What problems exist?
* Why are they problems?
* What is the best action?
* What will happen if I apply that action?
* How will it affect data quality?
* What analyses should I perform next?
* How can I communicate my findings?

⸻

Current Features

Data Loading

* CSV dataset loading
* Project-based workflow

Dataset Profiling

* Dataset summary
* Column data types
* Missing value statistics
* Duplicate detection
* Automatic grouping of numeric, categorical and datetime columns

Semantic Understanding

* Automatic semantic detection
* Extensible semantic detector architecture
* Plugin-ready design

Knowledge Engine

Domain-aware rules for common business columns including:

* Age
* Revenue
* Profit
* Unit Price
* Discount
* Quantity
* Date
* Region
* Product
* Gender

The Knowledge Engine provides preferred strategies, expected ranges and domain-specific recommendations.

Diagnosis Engine

Automatically detects:

* Missing values
* Duplicate rows
* Outliers
* Dataset quality score
* Confidence scores

Recommendation Engine

Knowledge-aware recommendations including:

* Column-specific imputation
* Duplicate removal
* Outlier handling
* Risk assessment
* Recommendation confidence

Decision Engine

Transforms recommendations into an executable cleaning plan.

Preview Engine

Safely previews proposed cleaning actions before modifying the dataset.

Session Tracking

Tracks every workflow step including:

* Dataset loading
* Profiling
* Diagnosis
* Recommendations
* Decisions
* Preview generation

⸻

Architecture

Dataset
    │
    ▼
Knowledge Engine
    │
    ▼
Profile Engine
    │
    ▼
Semantic Engine
    │
    ▼
Diagnosis Engine
    │
    ▼
Recommendation Engine
    │
    ▼
Decision Engine
    │
    ▼
Preview Engine
    │
    ▼
Cleaning Engine (Planned)
    │
    ▼
Analytics Planner (Planned)
    │
    ▼
Visualization Engine (Planned)
    │
    ▼
Modeling Engine (Planned)
    │
    ▼
BLUE Engine (Planned)
    │
    ▼
Explanation Engine (Planned)
    │
    ▼
Report Engine (Planned)

⸻

Installation

git clone https://github.com/josephubani/autodq-analytics.git
cd autodq-analytics
python -m venv .venv
source .venv/bin/activate
pip install -e .

⸻

Quick Start

from autodq import AutoDQ
project = AutoDQ("datasets/sample/sales.csv")
project.set_type("Date", "datetime")
project.profile()
project.diagnose()
project.recommend()
project.preview()
project.show_session()

⸻

Design Principles

AutoDQ follows several architectural principles.

* Every engine answers one question.
* Business logic is separated from rendering.
* Every engine returns structured objects.
* Plugins extend functionality instead of modifying the core.
* Recommendations are evidence-based.
* Sessions capture the complete workflow history.
* Every component is interface-independent, allowing future support for Python, ADQL, desktop applications, VS Code, and web interfaces.

⸻

Roadmap

Phase 1 — Foundation ✅

* Dataset Loader
* Profiling Engine
* Semantic Detection
* Diagnosis Engine
* Knowledge Engine
* Recommendation Engine
* Decision Engine
* Preview Engine
* Session Tracking

Phase 2 — Intelligence Layer 🚧

* Statistics Engine
* Decision Intelligence Engine
* Quality Score Simulator

Phase 3 — Cleaning Layer

* Cleaning Engine
* Undo Engine
* Dataset Versioning

Phase 4 — Analytics Layer

* Analytics Planner
* Visualization Engine
* Dashboard Generation

Phase 5 — Machine Learning

* BLUE Assumption Engine
* Regression
* Classification
* AutoML

Phase 6 — ADQL

* Analytics Domain Query Language
* Query Parser
* Query Executor

Phase 7 — Interfaces

* Streamlit Application
* Desktop Application
* VS Code Extension
* SaaS Platform

⸻

Documentation

Project documentation is available in the docs/ directory.

* Architecture
* Roadmap
* Plugin Guide
* ADQL Specification
* Research Notes
* Decision Log

⸻

Contributing

Contributions are welcome.

The project is currently under active development and follows a modular architecture designed to encourage community contributions.

⸻

License

MIT License

⸻

Author

Joseph Ubani

Master of Data Analytics

University of Niagara Falls Canada

Open-source developer building intelligent analytics software.