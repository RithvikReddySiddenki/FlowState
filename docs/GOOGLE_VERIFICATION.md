# Google verification and privacy preparation

Draft operational material, not a published policy or evidence of Google approval.
The owner must supply a verified domain, operator identity, support/privacy
contact, actual retention periods and incident process before publication.

## Scope justification

openid, email and profile establish the signed-in identity. The separately
consented gmail.readonly scope supports searching recruiting messages and reading
their identifiers, subject, sender, timestamp and bounded snippet. Gmail metadata
scope does not support the search query required by polling. The app does not
send, modify, trash or label email, retrieve attachments or request full bodies.
Optional watch/history uses the same read-only permission. No additional write
scope is requested for push.

## Privacy policy draft content

FlowState uses Google account identity for authentication and recruiting metadata
to organize the user's application records. Tokens are encrypted with a separately
configured key. Access is restricted to the signed-in owner. Message metadata is
processed by deterministic classification rules; no model provider receives it.
It is not used for advertising, sold, or used to train generalized AI models.
The operator must review these statements against its actual deployment and any
future services before adopting this policy.

Users can correct applications, disconnect Gmail and delete their account in
Settings. Disconnect revokes access and deletes Gmail metadata and sync runs,
while retaining application records. Account deletion removes local account data.
Users can also revoke access in Google Account settings. Operational backups
require a stated encrypted-storage, retention and deletion schedule; local deletion
does not instantly erase retained backups. The operator must choose and publish
that schedule, contact details and applicable user-rights handling.

Infrastructure providers may process stored application/metadata under the
operator's contracts. Identify actual hosting providers, deployment regions,
access controls, retention and transfer arrangements before public release.
Never publish example claims about certifications or approvals as facts.

## Submission checklist

Verify the production domain and OAuth redirect; publish owner-reviewed privacy
and terms URLs; match consent-screen branding/support; describe least-privilege
scope use and deletion; prepare a demonstration with synthetic messages showing
separate Gmail consent, sync, correction, disconnect and deletion; submit through
Google's current verification process and complete any required restricted-scope
assessment. Testing-mode success is not production OAuth verification.

Reference: [Google user-data policy](https://developers.google.com/terms/api-services-user-data-policy)
and [OAuth verification guidance](https://support.google.com/cloud/answer/9110914).
