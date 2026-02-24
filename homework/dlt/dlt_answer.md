# From APIs to Warehouses: AI-Assisted Data Ingestion with dlt

Welcome to the **Data Engineering Zoomcamp 2026** workshop on modern data ingestion!  
In this hands‑on session you’ll learn how to use [dlt](https://dlthub.com/docs) – an open‑source Python library – to build robust data pipelines from any REST API to a local data warehouse, all with the help of AI‑powered development tools.

By the end you will have:

- A working dlt pipeline that extracts data from a public API (Open Library or a custom NYC taxi API).
- Normalised relational tables stored in **DuckDB**.
- Experience using an **AI‑assisted IDE** (Cursor, Windsurf, VS Code + Copilot) to generate, debug, and understand pipeline code.
- Familiarity with dlt’s automatic schema evolution, incremental loading, and built‑in data normalisation.
- The ability to inspect your pipeline with the **dlt Dashboard** and build interactive reports with **marimo** and **Ibis**.

---

## Learning Objectives

- Understand the role of data ingestion in a modern data stack (Data Lake, Warehouse, Lakehouse).
- Recognise the challenges of working with raw JSON from APIs (nesting, schema changes, pagination, rate limits).
- See how **dlt** automates the hard parts: flattening, type conversion, schema evolution, and incremental loading.
- Leverage an **MCP (Model Context Protocol) server** to give an AI agent access to dlt documentation and your pipeline metadata.
- Build a complete pipeline from scratch by prompting an AI, then debug and extend it with natural language.
- Answer analytical questions about the loaded data using SQL (DuckDB) or marimo notebooks.

---

## Prerequisites

Before the workshop, make sure you have the following installed and configured:

| Requirement | Notes |
|-------------|-------|
| **Python 3.11+** | Check with `python --version` |
| **An agentic IDE** | [Cursor](https://cursor.sh) (recommended), [Windsurf](https://codeium.com/windsurf), or VS Code with [GitHub Copilot](https://github.com/features/copilot) |
| **`uv` (optional but fast)** | Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Basic familiarity with Python and APIs** | Understanding JSON, HTTP requests, and pagination helps |

No API keys are required – the Open Library API is completely open.

---

## Workshop Content

This workshop is split into two complementary parts. You can follow them sequentially or jump to the AI‑assisted part if you’re already comfortable with dlt basics.

### Part 1: dlt Fundamentals

If you are new to dlt, start with the interactive notebook that walks through core concepts:

> [**Open the dlt Pipeline Overview Notebook in Google Colab**](https://colab.research.google.com/github/anair123/data-engineering-zoomcamp/blob/workshop/dlt_2026/cohorts/2026/workshops/dlt/dlt_Pipeline_Overview.ipynb)

In this notebook you will:

- Define a **source** (where data comes from) and a **pipeline** (where data goes).
- Understand the three‑step process: **extract**, **normalize**, **load**.
- See how dlt automatically flattens nested JSON into relational tables with foreign keys.
- Inspect the loaded data in DuckDB using simple SQL.

This foundation will help you understand what the AI‑generated code is actually doing.

### Part 2: AI‑Assisted Pipeline Development

In this part you will build a pipeline from a real API using only natural language prompts inside an agentic IDE. The AI will write the dlt code for you, and you will debug, run, and inspect the results.

We will use two different APIs to demonstrate the workflow:

- **Open Library API** (scaffolded source, great for a first try)
- **NYC Taxi Trip Data API** (custom API, used in the homework)

The same principles apply to any REST API.

---

## Step‑by‑Step Instructions

### 1. Create a Project Folder

Open your terminal and create a new directory for the workshop:

```bash
mkdir dlt-workshop
cd dlt-workshop
```

Open this folder in your agentic IDE (e.g., Cursor: `cursor .`).

### 2. Set Up the dlt MCP Server

The **Model Context Protocol (MCP) server** allows your AI assistant to access dlt documentation, code examples, and your pipeline metadata directly. Configure it according to your IDE:

#### Cursor
Go to **Settings → Tools & MCP → New MCP Server** and paste:

```json
{
  "mcpServers": {
    "dlt": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "dlt[duckdb]",
        "--with",
        "dlt-mcp[search]",
        "python",
        "-m",
        "dlt_mcp"
      ]
    }
  }
}
```

#### VS Code (with Copilot)
Create `.vscode/mcp.json` in your project folder with the same JSON content.

#### Claude Code
In your terminal:

```bash
claude mcp add dlt -- uv run --with "dlt[duckdb]" --with "dlt-mcp[search]" python -m dlt_mcp
```

### 3. Install dlt Workspace

Install dlt with the workspace extra:

```bash
pip install "dlt[workspace]"
```

### 4. Scaffold a Pipeline (Open Library Example)

```bash
dlt init dlthub:open_library duckdb
```

This creates:

- `open_library_pipeline.py` – a placeholder pipeline file.
- `open_library-docs.yaml` – API metadata used by the MCP server.
- `.dlt/` – configuration folder.
- `.cursor/rules/` – AI prompt rules.

### 5. Prompt the AI to Generate and Run the Pipeline

In your IDE, open the AI chat (Cmd+K / Ctrl+K) and give a prompt like:

```
Please generate a REST API Source for Open Library API, as specified in @open_library-docs.yaml
Start with endpoint(s) books and skip incremental loading for now.
Place the code in open_library_pipeline.py and name the pipeline open_library_pipeline.
If the file exists, use it as a starting point.
Do not add or modify any other files.
Use @dlt rest api as a tutorial.
After adding the endpoints, allow the user to run the pipeline with python open_library_pipeline.py and await further instructions.
```

The AI will:

- Read the YAML documentation.
- Write the dlt `rest_api` source code into the pipeline file.
- Possibly execute the pipeline and report results.

If errors occur, paste them back to the AI and let it debug.

### 6. Inspect the Pipeline with the dlt Dashboard

Once the pipeline runs successfully, launch the built‑in dashboard:

```bash
dlt pipeline open_library_pipeline show
```

You will see:

- Pipeline runs and load IDs.
- Schemas, tables, and column data types.
- Row counts and sample data.
- Load history and any warnings.

This dashboard is invaluable for understanding what was loaded and debugging.

### 7. Ask the AI About Your Pipeline

Because the MCP server is active, you can now ask questions like:

- “What tables were created in the pipeline?”
- “Show me the schema for the books table.”
- “How many rows were loaded?”

The AI will query your pipeline metadata and answer.

### 8. (Bonus) Build Visualizations with marimo + Ibis

Generate an interactive report:

```bash
pip install marimo ibis
```

Then prompt the AI:

```
Create a marimo notebook that visualizes the top 10 authors by book count. Use ibis for data access. Reference: https://dlthub.com/docs/general-usage/dataset-access/marimo
```

The AI will generate a `.py` notebook file. Run it with:

```bash
marimo edit your_notebook.py   # for development
marimo run your_notebook.py    # to view the final report
```

---

## Homework: Build Your Own Pipeline

Now it’s your turn to build a pipeline **from scratch** using a custom API – no scaffold provided. You will load NYC taxi trip data and answer three analytical questions.

### Dataset

**NYC Yellow Taxi trip data** (January 2024, as used in many Zoomcamp examples)

| Property | Value |
|----------|-------|
| Base URL | `https://us-central1-dlthub-analytics.cloudfunctions.net/data_engineering_zoomcamp_api` |
| Format | Paginated JSON (1,000 records per page) |
| Pagination | Stop when an empty page is returned |

### Instructions

1. Create a new folder (or reuse your existing one) and open it in your IDE.
2. Set up the dlt MCP server as described above (if not already done).
3. Install dlt workspace.
4. **Do not** use `dlt init` with a source name – there is no scaffold for this API. Instead, prompt the AI with the API details:

```
Build a REST API source for NYC taxi data.

API details:
- Base URL: https://us-central1-dlthub-analytics.cloudfunctions.net/data_engineering_zoomcamp_api
- Data format: Paginated JSON (1,000 records per page)
- Pagination: Stop when an empty page is returned

Place the code in taxi_pipeline.py and name the pipeline taxi_pipeline.
Use @dlt rest api as a tutorial.
```

The AI will generate the pipeline. You may need to iterate if the pagination or response structure isn’t correctly handled – paste errors back to the AI.

5. Run the pipeline: `python taxi_pipeline.py`
6. Use the **dlt Dashboard** (`dlt pipeline taxi_pipeline show`) or the **MCP chat** to answer the following questions:

#### Question 1
What is the start date and end date of the dataset?

- 2009-01-01 to 2009-01-31
- 2009-06-01 to 2009-07-01
- 2024-01-01 to 2024-02-01
- 2024-06-01 to 2024-07-01

#### Question 2
What proportion of trips are paid with credit card?

- 16.66%
- 26.66%
- 36.66%
- 46.66%

#### Question 3
What is the total amount of money generated in tips?

- $4,063.41
- $6,063.41
- $8,063.41
- $10,063.41

### Submission

Submit your answers via the [DataTalks.Club homework form](https://courses.datatalks.club/de-zoomcamp-2026/homework/dlt) before the deadline.

> **Pro tip**: Use the dlt Dashboard to quickly run SQL queries. For example, to get the date range:
> ```sql
> SELECT MIN(pickup_datetime), MAX(pickup_datetime) FROM taxi;
> ```
> (Adjust column names based on your actual schema.)

---

## Resources

| Resource | Link |
|----------|------|
| dlt Documentation | [dlthub.com/docs](https://dlthub.com/docs) |
| dlt REST API Source Guide | [dlthub.com/docs/dlt-ecosystem/verified-sources/rest-api](https://dlthub.com/docs/dlt-ecosystem/verified-sources/rest-api) |
| dlt Dashboard | [dlthub.com/docs/general-usage/dashboard](https://dlthub.com/docs/general-usage/dashboard) |
| marimo + dlt Integration | [dlthub.com/docs/general-usage/dataset-access/marimo](https://dlthub.com/docs/general-usage/dataset-access/marimo) |
| Open Library API | [openlibrary.org/developers/api](https://openlibrary.org/developers/api) |
| Workshop Repo (GitHub) | [DataTalksClub/data-engineering-zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp/tree/main/cohorts/2026/workshops/dlt) |

---

## Expected Homework Results (Example)

If you run the pipeline correctly, your answers should match the following (based on the dataset provided for the workshop):

- **Start date**: `2009-01-01`
- **End date**: `2009-01-31`  
  → So **Question 1 answer: 1**

- **Credit card proportion**: `26.66%`  
  → **Question 2 answer: 2**

- **Total tips**: `$6,063.41`  
  → **Question 3 answer: 2**

These values may vary slightly depending on the exact data returned by the API, but they should be very close.

---

## Learning in Public

We encourage you to share your experience! Write a LinkedIn post or tweet about what you built. It helps reinforce your learning and connects you with the community.

**Example LinkedIn post**:

```
🚀 Just completed the dlt workshop in the Data Engineering Zoomcamp!

I built a full data pipeline from a REST API to DuckDB using dlt, and even used AI (Cursor + dlt MCP) to generate and debug the code. The pipeline automatically normalised nested JSON, handled pagination, and loaded incremental data.

Then I used the dlt Dashboard to explore the schema and answer analytical questions about NYC taxi trips.

Huge thanks to @dltHub and @DataTalksClub for this hands-on experience.

Check out the workshop: https://github.com/DataTalksClub/data-engineering-zoomcamp/
```

---

**Happy pipelining!**  
If you run into any issues, the dlt community is active on [Slack](https://dlthub.com/community) and GitHub.