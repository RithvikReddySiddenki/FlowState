# Gmail integration and privacy

Normal sign-in requests only openid/email/profile. The authenticated Connect
Gmail action requests gmail.readonly plus offline consent. The callback requires
the same Google account, verified email and a refresh token with the granted
scope. A separate Fernet TOKEN_ENCRYPTION_KEY encrypts refresh tokens at rest;
the signed HttpOnly browser cookie holds an opaque revocable session ID only.
Keep encryption and signing keys outside source control; losing the encryption
key requires reconnecting Gmail. Google access tokens exist only in worker memory.

The worker uses [Google's message listing API](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list),
follows page tokens, then requests metadata for each message. Read-only scope
supports search; the narrower metadata scope does not support the q parameter.
Only identifiers, sender, subject, bounded snippet, timestamp and classification
are stored. Full bodies/attachments are not requested or persisted.

Initial sync scans recruiting search results from the past year. Incremental
polling overlaps the previous successful scan by one day. A per-user unique
message identifier prevents duplicate ingestion. Thread context and exact
company/role matches scope association; ambiguous matches remain reviewable.
Generic ATS addresses are never assumed to name the employer. Rules accept
explicit company/role phrases and supported status signals, but many real-world
templates will require review. This is a conservative rules engine, not universal
email understanding. Deadline detection currently supports explicit ISO dates.

Status history references the source message. Older events cannot roll back
newer stages. Manual changes lock the stage against automatic changes; there
is currently no UI to release that lock. Review decisions can explicitly attach
a message and apply its detected stage as a manual correction. Action reminders
do not replace recruiting stage.

Disconnect revokes the refresh token and deletes stored email metadata and sync
runs while retaining applications. Account deletion revokes access and removes
all local account data. If Google revocation is unavailable, retry; deletion is
not falsely reported successful. Alternatively revoke in Google Account >
Security > Third-party apps and retry. Backups follow their separate retention
policy and require operational deletion management.

Production use of Gmail restricted scopes may require Google verification and
a security assessment. Neither verification nor approval is claimed. Before
public release, publish an accurate privacy policy and scope justification,
document retention/contact/support, and complete Google's applicable process.
Optional authenticated Pub/Sub, watch/history, renewal and polling recovery are
implemented but disabled and tested with synthetic fixtures only. See
[push setup](GMAIL_PUSH.md) and [verification preparation](GOOGLE_VERIFICATION.md).
Real local login, consent, refresh and polling sync have passed; public push
delivery and production restricted-scope verification remain pending.
