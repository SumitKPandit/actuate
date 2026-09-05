def ask_mobility_agent(question):
    """
    Convert a natural-language mobility question into SQL with Qwen3-4B,
    execute the SQL against DuckDB, and return the analytical result.
    """

    start = time.time()

    schema = """
TABLE trips
Purpose: One row per mobility trip.

Columns:
- business_unit VARCHAR
- office VARCHAR
- product_type VARCHAR
- trip_date DATE
- shift_type VARCHAR
- trip_id BIGINT
- trip_direction VARCHAR
- actual_escort BOOLEAN
- vendor_id VARCHAR
- actual_cab_capacity INTEGER
- planned_km DOUBLE
- traveled_km DOUBLE
- delay_reason VARCHAR
- delay_minutes DOUBLE
- actual_cab_fuel_type VARCHAR
- is_driver_nc BOOLEAN
- is_cab_nc BOOLEAN
- trip_nodal VARCHAR
- plannedemployee_cnt INTEGER
- actualemployee_cnt INTEGER
- noshow_cnt INTEGER

Rules:
- Use trips.vendor_id for vendors.
- Use trips.delay_minutes for delay.
- Use COUNT(*) for trip volume.
- Filter trips.trip_date for date ranges.
- Use AVG(trips.delay_minutes) for average delay.
"""

    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_mobility_data",
                "description": "Execute a read-only SQL query against the mobility DuckDB database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "A SELECT or WITH SQL query using only the provided schema."
                        }
                    },
                    "required": ["sql"]
                }
            }
        }
    ]

    messages = [
        {
            "role": "system",
            "content": f"""You are an enterprise mobility analytics agent.

Use ONLY the provided schema.
Never invent tables or columns.

{schema}

Generate a tool call to query_mobility_data.
Do not answer the user's question directly."""
        },
        {
            "role": "user",
            "content": question
        }
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        tools=tools,
        enable_thinking=False
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=256,
        do_sample=False
    )

    model_output = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=False
    )

    match = re.search(
        r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
        model_output,
        re.DOTALL
    )

    if not match:
        raise RuntimeError(f"No tool call generated:\n{model_output}")

    tool_call = json.loads(match.group(1))
    sql = tool_call["arguments"]["sql"]

    # Basic read-only protection.
    normalized = sql.strip().rstrip(";")
    if not (
        normalized.upper().startswith("SELECT")
        or normalized.upper().startswith("WITH")
    ):
        raise ValueError("Only SELECT/WITH queries are allowed.")

    forbidden = [
        "INSERT ", "UPDATE ", "DELETE ", "DROP ",
        "ALTER ", "CREATE ", "TRUNCATE ",
        "ATTACH ", "DETACH ", "COPY "
    ]

    upper_sql = normalized.upper()

    if any(word in upper_sql for word in forbidden):
        raise ValueError("Potentially unsafe SQL generated.")

    query_start = time.time()

    con = duckdb.connect(DB_PATH, read_only=True)

    try:
        result = con.execute(normalized).fetchdf()
    finally:
        con.close()

    query_time = time.time() - query_start
    total_time = time.time() - start

    return {
        "question": question,
        "sql": normalized,
        "result": result,
        "llm_time": total_time - query_time,
        "query_time": query_time,
        "total_time": total_time,
    }
#####################################################################################


def format_agent_response(response):
    """
    Convert DuckDB results into concise natural-language output.
    Supports vendor rankings with or without trip volume.
    """

    df = response["result"]

    if df.empty:
        return (
            "I couldn't find any matching mobility data for that request. "
            "The available trip data covers May through July 2026."
        )

    question = response["question"]
    lines = [
        f'Based on the mobility data, here are the results for: "{question}"',
        ""
    ]

    if "vendor_id" in df.columns and "average_delay" in df.columns:

        for i, row in df.iterrows():
            line = f"{i + 1}. {row['vendor_id']}: "

            if "trip_volume" in df.columns:
                line += f"{int(row['trip_volume']):,} trips, "

            line += f"{row['average_delay']:.2f} min average delay."
            lines.append(line)

        top = df.iloc[0]

        direction = (
            "lowest"
            if "lowest" in question.lower()
            or "least" in question.lower()
            else "highest"
        )

        summary = (
            f"Key finding: {top['vendor_id']} has the {direction} "
            f"average delay at {top['average_delay']:.2f} minutes"
        )

        if "trip_volume" in df.columns:
            summary += f" across {int(top['trip_volume']):,} trips"

        lines.extend(["", summary + "."])

    else:
        lines.append(df.to_string(index=False))

    return "\n".join(lines)


response = ask_mobility_agent(
    "Which vendor had the lowest average delay in July 2026?"
)

print("===== AGENT RESPONSE =====")
print(format_agent_response(response))