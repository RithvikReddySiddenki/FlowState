# Optional Gmail push and history

Disabled by default. Polling remains the standard local workflow. Implementation
uses authenticated Pub/Sub notifications to enqueue existing durable sync runs,
Gmail messageAdded history pages, metadata-only retrieval and existing classifier,
ownership/deduplication/manual-correction rules. Only completed ingestion advances
the cursor. Initial backfill failure cannot commit a cursor that skips that backfill.
Expired history (404) falls back to the bounded polling window. Watches renew
daily; a 15-minute maintenance tick also queues catch-up work for missed pushes.
One active run per account coalesces duplicate notifications. Recovery/backoff
uses the existing worker machinery. Unknown/disconnected accounts acknowledge
without creating data. No Google notification body is logged.

Preparation requires a reviewed public HTTPS endpoint and separate authorization
for cloud resources/publication. This session did not create a Pub/Sub topic or
subscription, enable push for the real account, or verify live push delivery.

After approval, follow Google's [Gmail push guide](https://developers.google.com/workspace/gmail/api/guides/push)
and [authenticated push configuration](https://docs.cloud.google.com/pubsub/docs/authenticate-push-subscriptions):

1. Create a topic in the OAuth client's project. Grant only the Gmail publisher
   identity gmail-api-push@system.gserviceaccount.com publisher on that topic.
2. Create a dedicated push service account and authenticated subscription. Set
   its endpoint to https://YOUR_DOMAIN/api/gmail/push and an exact audience of
   the same URL. Grant the Pub/Sub service agent the required token-creation
   role for this identity; do not grant application-wide administration.
3. Set ENABLE_GMAIL_PUSH=true, GMAIL_PUSH_TOPIC=projects/PROJECT/topics/TOPIC,
   GMAIL_PUSH_SUBSCRIPTION=projects/PROJECT/subscriptions/SUBSCRIPTION,
   GMAIL_PUSH_AUDIENCE and GMAIL_PUSH_SERVICE_ACCOUNT in the secure runtime
   environment of API, worker and scheduler. Apply migration 0005 first.
4. Start one Beat scheduler and workers, run an initial sync, verify watch expiry
   and completed cursor locally without publishing account information. Deliver
   a synthetic recruiting message, observe the run and persisted classification,
   then exercise duplicate notifications, missed delivery and renewal.
5. Review subscription retry/dead-letter policy, quotas and costs. Monitor failed
   syncs and watch expiry. Keep manual Sync / retry Gmail available.

The endpoint exempts only this exact POST path from browser Origin checks;
it separately requires an RS256 Google signature, issuer, expiry, issued-at,
exact audience, verified service-account email and matching subscription.
Body size is bounded. Signing keys are fetched only from Google's fixed HTTPS
JWKS endpoint and cached for one hour. A newly rotated key can require the next
cache refresh; Pub/Sub retries and periodic catch-up cover that delay.

Disabling the flag returns 404 for new pushes and resumes ordinary polling;
also stop the watch/delete the subscription in the approved Google project to
stop provider traffic. Disconnect revokes the credential and deletes its cursor.
The bounded polling fallback does not promise recovery of arbitrarily old mail
outside its documented window. Metadata from unrelated history additions is
discarded by the classifier and is not stored as recruiting activity.
