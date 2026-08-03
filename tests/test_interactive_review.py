import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from autodq import ADQLFileRunner, AutoDQ
from autodq.cli import (
    _execute_review_interaction,
    _notebook_payload,
    _review_interactive_data,
)


REVIEW_MIME = "application/vnd.autodq.review+json"


class InteractiveReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        data = pd.DataFrame(
            {
                "Age": [25, 30, -5, 40, 200, 35, 28, 31, 29, 32, 33, 34],
                "Revenue": [
                    100.0,
                    110.0,
                    120.0,
                    130.0,
                    10000.0,
                    140.0,
                    150.0,
                    160.0,
                    170.0,
                    180.0,
                    190.0,
                    200.0,
                ],
                "Quantity": [1.0, 2.0, 3.0, np.nan, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0],
                "Region": ["North", "South", "Unknown", None, "West", "North", "South", "West", "North", "South", "West", "North"],
            }
        )
        self.dataset = self.root / "review.csv"
        data.to_csv(self.dataset, index=False)
        self.script = self.root / "review.adql"
        self.script.write_text(
            """#!/usr/bin/env autodq
# %% [Dataset]
DATASET "review.csv" TARGET Revenue;
# %% [Review]
REVIEW;
""",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_interactive_payload_is_opt_in_and_static_output_remains(self):
        result = ADQLFileRunner().run(
            self.script,
            through_cell=2,
            auto_display=False,
        )

        static = _notebook_payload(result)
        interactive = _notebook_payload(result, interactive_review=True)

        self.assertIn("text/html", [item["mime"] for item in static["outputs"]])
        self.assertNotIn(REVIEW_MIME, [item["mime"] for item in static["outputs"]])
        custom = next(
            item for item in interactive["outputs"] if item["mime"] == REVIEW_MIME
        )
        data = json.loads(custom["data"])
        self.assertEqual(data["protocol"], "autodq-review-v1")
        self.assertEqual(data["cell"]["number"], 2)
        self.assertGreater(data["summary"]["action_count"], 0)
        self.assertTrue(data["actions"])

    def test_review_actions_use_project_api_and_preserve_audit(self):
        project = AutoDQ(str(self.dataset), target="Revenue")
        review = project.review_cleaning(auto_display=False)
        first = review.actions[0].action_id

        approved = _execute_review_interaction(
            project,
            {"type": "approve", "action_ids": [first]},
        )
        self.assertTrue(approved["interaction"]["success"])
        self.assertEqual(review.actions[0].status, "approved")

        previewed = _execute_review_interaction(
            project,
            {"type": "preview", "action_ids": [first], "max_rows": 2},
        )
        self.assertIsNotNone(previewed["interaction"]["result"])

        edited = _execute_review_interaction(
            project,
            {
                "type": "edit",
                "row_index": 2,
                "changes": {"Age": 5},
                "reason": "Confirmed in source system.",
            },
        )
        self.assertEqual(review.working_data.loc[2, "Age"], 5)
        self.assertIn("row 2", edited["interaction"]["message"])

        applied = _execute_review_interaction(project, {"type": "apply"})
        self.assertEqual(applied["interaction"]["result"]["stage"], "CLEANED")
        self.assertEqual(project.state.cleaned_data.loc[2, "Age"], 5)
        event_types = [entry.event_type for entry in review.audit_trail]
        self.assertIn("action_approved", event_types)
        self.assertIn("manual_cell_edit", event_types)

    def test_review_action_validation_rejects_unsafe_or_empty_requests(self):
        project = AutoDQ(str(self.dataset), target="Revenue")
        project.review_cleaning(auto_display=False)

        with self.assertRaisesRegex(ValueError, "Unsupported"):
            _execute_review_interaction(project, {"type": "python"})
        with self.assertRaisesRegex(ValueError, "Select at least one"):
            _execute_review_interaction(
                project,
                {"type": "approve", "action_ids": []},
            )
        with self.assertRaisesRegex(ValueError, "non-empty object"):
            _execute_review_interaction(
                project,
                {"type": "edit", "row_index": 0, "changes": []},
            )

    def test_interactive_data_is_bounded_to_recent_audit_entries(self):
        project = AutoDQ(str(self.dataset), target="Revenue")
        review = project.review_cleaning(auto_display=False)
        for index in range(30):
            project.edit_row(
                0,
                {"Age": 25 + index},
                reason=f"Edit {index}",
            )

        data = _review_interactive_data(review, cell_number=2)

        self.assertEqual(len(data["audit_trail"]), 25)
        self.assertEqual(data["summary"]["audit_count"], review.audit_count)

    def test_kernel_executes_interactive_review_action_in_same_session(self):
        process = subprocess.Popen(
            [sys.executable, "-m", "autodq", "kernel", str(self.script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            process.stdin.write(
                json.dumps(
                    {
                        "id": 1,
                        "action": "execute",
                        "cell": 2,
                        "interactive_review": True,
                    }
                )
                + "\n"
            )
            process.stdin.flush()
            initial = json.loads(process.stdout.readline())
            review_output = next(
                item for item in initial["outputs"] if item["mime"] == REVIEW_MIME
            )
            review_data = json.loads(review_output["data"])
            action_id = review_data["actions"][0]["action_id"]

            process.stdin.write(
                json.dumps(
                    {
                        "id": 2,
                        "action": "review",
                        "cell": 2,
                        "interaction": {
                            "type": "approve",
                            "action_ids": [action_id],
                        },
                    }
                )
                + "\n"
            )
            process.stdin.flush()
            updated = json.loads(process.stdout.readline())
        finally:
            if process.stdin:
                process.stdin.write(json.dumps({"action": "shutdown"}) + "\n")
                process.stdin.flush()
            process.wait(timeout=15)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream:
                    stream.close()

        self.assertTrue(initial["success"])
        self.assertTrue(updated["success"])
        output = next(item for item in updated["outputs"] if item["mime"] == REVIEW_MIME)
        data = json.loads(output["data"])
        approved = next(item for item in data["actions"] if item["action_id"] == action_id)
        self.assertEqual(approved["status"], "approved")
        self.assertGreater(data["summary"]["audit_count"], review_data["summary"]["audit_count"])


if __name__ == "__main__":
    unittest.main()
