"""Synthetic external Gmail adapter for an isolated REAL Celery queue test.

Never imported by the production application/worker entrypoint.
"""

import os

from apps.api import tasks


class SyntheticGmail:
    def __init__(self, *args):
        pass

    def messages(self, since, known_ids=None):
        for identifier, snippet, timestamp in [
            ("synthetic-queue-interview", "Interview scheduled with the team", "1791288000000"),
            ("synthetic-queue-old", "We are not moving forward", "1791115200000"),
            ("synthetic-queue-interview", "Interview scheduled with the team", "1791288000000"),
        ]:
            yield {
                "id": identifier,
                "threadId": "synthetic-queue-thread",
                "snippet": snippet,
                "internalDate": timestamp,
                "payload": {
                    "headers": [
                        {
                            "name": "Subject",
                            "value": "Application for Engineer at Synthetic Queue Labs",
                        },
                        {"name": "From", "value": "recruiter@example.test"},
                    ]
                },
            }

    def close(self):
        pass


if __name__ == "__main__":
    assert os.getenv("FLOWSTATE_VALIDATION") == "1"
    assert os.getenv("SESSION_SECRET") == "synthetic-container-validation-secret-only"
    tasks.GmailClient = SyntheticGmail
    tasks.celery.worker_main(
        [
            "worker",
            "--loglevel=WARNING",
            "--concurrency=1",
            "--queues=synthetic-validation",
            "--hostname=synthetic-validation@isolated",
        ]
    )
