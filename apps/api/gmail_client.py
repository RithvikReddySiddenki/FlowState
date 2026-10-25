"""Gmail's official REST API over bounded HTTP requests (no bodies requested)."""

import time
from datetime import datetime, timezone

import httpx

from apps.api.token_store import decrypt

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
SEARCH = '{"thank you for applying" "your application" "application received" "under review" "coding challenge" assessment HackerRank interview "offer of employment" "not moving forward" "action required" deadline}'


class GmailFailure(Exception):
    def __init__(self, retryable=False):
        self.retryable = retryable
        super().__init__(
            "Gmail temporarily unavailable" if retryable else "Reconnect Gmail to continue"
        )


class GmailClient:
    def __init__(self, refresh_token: str, client_id: str, client_secret: str):
        self.http = httpx.Client(timeout=30)
        self.next_request_at = 0.0
        try:
            response = self.http.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": decrypt(refresh_token),
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            self.check(response)
            self.http.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        except Exception:
            self.http.close()
            raise

    @staticmethod
    def check(response):
        if response.is_error:
            raise GmailFailure(response.status_code in {403, 429, 500, 502, 503, 504})

    def get(self, url, *, params):
        # Pace metadata requests as well as retrying provider-side rate limits.
        # This runs only in background workers, never in an API request.
        delay = self.next_request_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        response = self.http.get(url, params=params)
        self.next_request_at = time.monotonic() + 0.25
        return response

    def messages(self, since: datetime | None, known_ids: set[str] | None = None):
        query = SEARCH
        if since:
            # Overlap covers same-second indexing; stable IDs deduplicate results.
            query += f" after:{int(since.replace(tzinfo=timezone.utc).timestamp()) - 86400}"
        else:
            query += " newer_than:365d"
        page = None
        while True:
            params = {"q": query, "maxResults": 100}
            if page:
                params["pageToken"] = page
            response = self.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages", params=params
            )
            self.check(response)
            data = response.json()
            for message in data.get("messages", []):
                if known_ids and message["id"] in known_ids:
                    continue
                details = self.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message['id']}",
                    params=[
                        ("format", "metadata"),
                        ("metadataHeaders", "Subject"),
                        ("metadataHeaders", "From"),
                    ],
                )
                if details.status_code == 404:
                    continue
                self.check(details)
                yield details.json()
            page = data.get("nextPageToken")
            if not page:
                break

    def close(self):
        self.http.close()

    def watch(self, topic):
        response = self.http.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/watch",
            json={"topicName": topic},
        )
        self.check(response)
        return response.json()

    def history_messages(self, history_id, since, known_ids):
        """Advance only after the caller durably ingests every page.

        An expired cursor (404) falls back to the bounded polling overlap.
        Added messages are fetched as metadata; the classifier rejects unrelated mail.
        """
        page = None
        seen = set(known_ids)
        while True:
            params = {
                "startHistoryId": history_id,
                "historyTypes": "messageAdded",
                "maxResults": 100,
            }
            if page:
                params["pageToken"] = page
            response = self.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/history", params=params
            )
            if response.status_code == 404:
                self.completed_history_id = None
                yield from self.messages(since, known_ids=known_ids)
                return
            self.check(response)
            data = response.json()
            for change in data.get("history", []):
                for added in change.get("messagesAdded", []):
                    identifier = added["message"]["id"]
                    if identifier in seen:
                        continue
                    seen.add(identifier)
                    detail = self.get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{identifier}",
                        params=[
                            ("format", "metadata"),
                            ("metadataHeaders", "Subject"),
                            ("metadataHeaders", "From"),
                        ],
                    )
                    if detail.status_code == 404:
                        continue
                    self.check(detail)
                    yield detail.json()
            page = data.get("nextPageToken")
            if not page:
                self.completed_history_id = data["historyId"]
                return
