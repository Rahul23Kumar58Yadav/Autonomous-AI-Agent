

import json
import requests

BASE_URL = "http://127.0.0.1:8000"

STANDARD_REQUEST = {
    "request": (
        "Create a project plan for launching a new mobile banking app "
        "feature that allows users to split bills with friends. The project "
        "has a 3-month timeline and involves engineering, design, and QA teams."
    ),
    "session_id": "demo-standard",
}

COMPLEX_REQUEST = {
    "request": (
        "We need something for the client meeting next week about the "
        "payment gateway migration. Leadership wants it to sound confident "
        "but engineering isn't fully sure the new vendor will meet the "
        "compliance deadline. Also finance keeps changing the budget number. "
        "Just put together whatever makes sense."
    ),
    "session_id": "demo-complex",
}


def call_agent(label: str, payload: dict):
    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)
    print(f"Request: {payload['request']}\n")

    resp = requests.post(f"{BASE_URL}/agent", json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()

    print(f"Document type : {data['document_type']}")
    print(f"Title         : {data['title']}")
    print(f"Document path : {data['document_path']}")

    if data["assumptions"]:
        print("\nAssumptions made by agent:")
        for a in data["assumptions"]:
            print(f"  - {a}")

    print(f"\nAgent-generated task list ({len(data['task_list'])} steps):")
    for step in data["task_list"]:
        print(f"  [{step['id']}] {step['action']:<20} -> {step['output_key']}")

    print(f"\nAgent summary: {data['message']}")
    return data


def main():
    standard_result = call_agent("TEST 1: STANDARD BUSINESS REQUEST", STANDARD_REQUEST)
    complex_result = call_agent("TEST 2: COMPLEX / AMBIGUOUS REQUEST", COMPLEX_REQUEST)

    print("\n" + "=" * 70)
    print("DEMO COMPLETE — both documents generated in outputs/")
    print("=" * 70)
    print(f"1. {standard_result['document_path']}")
    print(f"2. {complex_result['document_path']}")


if __name__ == "__main__":
    main()