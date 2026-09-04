# Gama Mail Transport

This first-party plugin configures WordPress' bundled PHPMailer only when
`WP_ENVIRONMENT_TYPE=production`. Credentials are read at runtime from
`GAMA_SMTP_HOST`, `GAMA_SMTP_PORT`, `GAMA_SMTP_USERNAME`,
`GAMA_SMTP_PASSWORD` and `GAMA_SMTP_ENCRYPTION` (`tls` or `ssl`). They must be
provided by the protected production environment and host `.env`; they are not
stored in WordPress or built into an image.

Non-production delivery remains owned by `gama-local-mailpit`, so test messages
cannot escape the isolated sink. Production deployment validation rejects local
and Mailpit hosts before starting the release.

The plugin is first-party, GPL-2.0-or-later, has no additional dependency and
does not persist data. Its separate Jira subtask must be linked to GSWEB-8 when
Jira access is available.
