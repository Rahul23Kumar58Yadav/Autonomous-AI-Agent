import json
import logging
from fastapi.testclient import TestClient
from main import app

logging.basicConfig(level=logging.INFO)
client = TestClient(app)

STANDARD_REQUEST = {
    "request": (
        "Create a project plan for launching a new mobile banking app "
        "feature that allows users to split bills with friends. The project "
        "has a 3-month timeline and involves engineering, design, and QA teams."
    ),
    "session_id": "test-standard-001",
}


def run():
    print("=" * 70)
    print("TEST 1: STANDARD BUSINESS REQUEST")
    print("=" * 70)
    print(f"Request: {STANDARD_REQUEST['request']}\n")

    response = client.post("/agent", json=STANDARD_REQUEST)

    assert response.status_code == 200, f"Unexpected status: {response.status_code} — {response.text}"

    data = response.json()

    print(f"Document type : {data['document_type']}")
    print(f"Title         : {data['title']}")
    print(f"Document path : {data['document_path']}")
    print(f"\nAssumptions made by agent:")
    for a in data["assumptions"]:
        print(f"  - {a}")

    print(f"\nAgent-generated task list ({len(data['task_list'])} steps):")
    for step in data["task_list"]:
        print(f"  [{step['id']}] {step['action']} -> {step['output_key']}")
        print(f"       {step['description']}")

    print(f"\nAgent message:\n{data['message']}")

    # Basic sanity assertions for automated verification
    assert data["document_path"].endswith(".docx")
    assert len(data["task_list"]) >= 2
    assert data["document_type"]

    print("\n✅ Standard request test passed.")
    return data


if __name__ == "__main__":
    result = run()
    print("\nFull response JSON:")
    print(json.dumps(result, indent=2))