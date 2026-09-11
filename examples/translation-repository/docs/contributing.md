# Contributing Translations

You can translate in Localize/Weblate or propose a GitHub pull request using
only your browser. You do not need to install the tooling or edit code.

## Edit on GitHub

1. Open [the question outline](../tree/outline.md) and find the text to change.
2. Open its `translation.md` file. For a repeated string, follow the shared
   block link and edit that group's `context.md` instead.
3. Use GitHub's pencil button. Change only the text inside the
   `Translation ({{TARGET_LANGUAGE}})` fenced block. Keep its fences, English
   source, UUIDs, links, and Markdown formatting intact.
4. Propose the change on a new branch and open a pull request. Explain the
   wording briefly; do not edit generated PO files or run build commands.
5. Wait for **Validate Translation Config**. Its `github-translation-report`
   artifact identifies formatting errors or conflicting Weblate edits.

CI expands canonical shared translations in its temporary checkout. If you
edited a repeated string's individual field to a different value, restore that
field and keep the edit in the canonical shared block.

## Review the PO

Open the pull request's Actions run and download `native-locale-<head SHA>`
from **Artifacts**. It contains `final_translated.po` and a review diff, retained
for 14 days. Import the PO into the matching KM version in a test DSW instance
to review a questionnaire. This artifact is not a hosted DSW preview.

CI validates the PO and its source references locally; it does not upload the
locale to DSW. Fork and same-repository pull requests both run without secrets
or branch write access.

After merge, automation checks Weblate again, imports safe edits, and refreshes
the generated files. A conflicting edit needs maintainer review; automation
does not choose which translation wins.

For approved, long-term downloads, use this repository's **Releases → Latest**.
