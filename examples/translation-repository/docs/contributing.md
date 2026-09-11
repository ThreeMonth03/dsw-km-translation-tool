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
5. Wait for **KM Translation Operations**. Its `github-translation-report`
   artifact identifies formatting errors or conflicting Weblate edits.

CI expands canonical shared translations in its temporary checkout. If you
edited a repeated string's individual field to a different value, restore that
field and keep the edit in the canonical shared block.

## Review the PO

Open the pull request's Actions run and download `native-locale-<head SHA>`
from **Artifacts**. It contains `final_translated.po` and a review diff, retained
for 14 days. This artifact is not a hosted DSW preview.

Download `native-dsw-review` from the same run for actual DSW screenshots and
`coverage.md`. CI imports the PO in a temporary official DSW instance and checks
source/translated language switching. The screenshots cover a translated
chapter title, not every changed question. Review other changes interactively
using the steps below.

The coverage report compares the PO with a freshly exported official POT.
Missing, empty, fuzzy and extra entries are listed separately. An **incomplete**
warning does not block an importable partial locale; a green workflow does not
mean every official string has been translated.

If a missing string is also listed in `source-catalog/source-catalog.md`, it is
absent from Weblate's shared source POT. Ask a maintainer to follow the
[shared source update process](sync-policy.md#shared-source-catalog); do not add
ad hoc PO entries or create new translation folders for it.

To review the translation in a test DSW instance running DSW 4.33 or newer:

1. Open the matching source Knowledge Model version under **Knowledge Models**.
2. Open **Locales → Import**, enter a display name, and upload the PO.
3. Create or open a test project that uses that Knowledge Model version.
4. In the project's **Settings**, select `{{TARGET_LANGUAGE}}` under **Language**
   and save. Importing a locale does not switch existing projects to it.
5. Open **Questionnaire** and review the changed questions. Switch **Language**
   back to the source language to compare the original text.

CI uses disposable test data and removes its DSW containers after the check.
It does not access production DSW or publish a live website. Fork and
same-repository pull requests both run without secrets or branch write access.

After merge, automation checks Weblate again, imports safe edits, and refreshes
the generated files. A conflicting edit needs maintainer review; automation
does not choose which translation wins.

For approved, long-term downloads, use this repository's **Releases → Latest**.
