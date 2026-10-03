This is an example to copy from. Do not leave it in the `MANAGER.md` the agent loads.

Fictivia is a fictional company. Copy the values you want into your own **Your context** block, then delete this file from the folder the agent reads.

- Role and scope: Director of Engineering at Fictivia. Three engineers, no other managers. Owns delivery for this team.
- Timezone (the zone reports should use): America/Toronto
- Reports (name, role, team, timezone, 1:1 language):
  - Sam, Senior, Platform, America/Toronto, English
  - Priya, Senior, Clinical, Europe/Lisbon, English
  - Lior, Mid, Mobile, America/Los_Angeles, Spanish
- Team membership and the minimum staffing that counts as covered: Sam, Priya, and Lior count toward coverage. Minimum staffing is 2.
- Your manager, and what they care about: The CTO. Wants early warning on people risk, a headline before the detail, and no surprise in a skip-level.
- Key stakeholders: Product (one PM per pod), Support, and the clinical lead.
- Escalation contact when harm is accruing: the CTO, then the on-call director.
- Frameworks in use (OKRs, DORA metrics, ...): OKRs at company and pod level. DORA metrics for delivery.
- Sources the agent can read (code host, calendar, chat, docs, observability): GitHub, the team calendar, the team chat, the engineering docs.
- Where saved artifacts go: notes/briefs/
- Review states that count as a verdict on your code host: APPROVED, CHANGES_REQUESTED. These are this host's names for approve and request-changes, which R-12 uses when the field is blank.
- Topics that stay verbal (see G-2): health, family, legal, immigration.
- Output preferences (length, language, link format): decision-first summary, then a short narrative. Links include the repository and number.
- Rule overrides if any (by ID): R-12: stalled after three days, not five
