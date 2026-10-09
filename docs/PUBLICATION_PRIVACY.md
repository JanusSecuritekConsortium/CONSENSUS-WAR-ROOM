# Public-source privacy

Publish implementation code and synthetic examples only. Keep personal names,
addresses, affiliations, account and channel identifiers, mailbox endpoints,
calendar-sharing URLs, credentials, recordings and source contents in private
local configuration or the local vault.

Examples must use reserved domains such as `example.invalid`. Imported workflows
must not contain real account addresses or saved credential references. Newsletter
settings use the private account store or `AURELIUS_NEWS_IMAP_HOST` and
`AURELIUS_NEWS_USERNAME`; no real mailbox should be a source-code default.

Before publishing, review the staged diff, generated files, commit metadata and
new binary files. A current-tree scan is not a guarantee that history is clean.
Removing a value in a normal commit leaves previous versions accessible. Historical
removal requires a separately validated history rewrite and may require cleanup of
pull-request references, caches, forks or downloaded copies. Repository ownership
also remains public on the hosting service.
