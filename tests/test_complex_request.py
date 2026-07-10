

import json
import logging
from fastapi.testclient import TestClient
from main import app

logging.basicConfig(level=logging.INFO)
client = TestClient(app)

COMPLEX_REQUEST = {
    "request": (
        "We need something for the client meeting next week about the "
        "payment gateway migration. Leadership wants it to sound confident "
        "but engineering isn't fully sure the new vendor will meet the "
        "compliance deadline. Also finance keeps changing the budget number. "
        "Just put together whatever makes sense."
    ),
    "session_id": "test-complex-001",
}


def run():
    print("=" * 70)
    print("TEST 2: COMPLEX / AMBIGUOUS REQUEST")
    print("=" * 70)
    print(f"Request: {COMPLEX_REQUEST['request']}\n")

    response = client.post("/agent", json=COMPLEX_REQUEST)

    assert response.status_code == 200, f"Unexpected status: {response.status_code} — {response.text}"

    data = response.json()

    print(f"Document type (agent-inferred) : {data['document_type']}")
    print(f"Title                          : {data['title']}")
    print(f"Document path                  : {data['document_path']}")

    print(f"\nAssumptions the agent had to make (this is the key part):")
    for a in data["assumptions"]:
        print(f"  - {a}")

    print(f"\nAgent-generated task list ({len(data['task_list'])} steps):")
    for step in data["task_list"]:
        print(f"  [{step['id']}] {step['action']} -> {step['output_key']}")
        print(f"       {step['description']}")

    print(f"\nAgent message:\n{data['message']}")

    # For an ambiguous request, we specifically expect the agent to have
    # recorded at least one assumption — if it didn't, that's a planning gap.
    assert len(data["assumptions"]) >= 1, "Expected agent to surface assumptions for ambiguous input."
    assert data["document_path"].endswith(".docx")

    print("\n✅ Complex request test passed — assumptions were surfaced as expected.")
    return data


if __name__ == "__main__":
    result = run()
    print("\nFull response JSON:")
    print(json.dumps(result, indent=2))