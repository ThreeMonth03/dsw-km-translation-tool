# Contributing Translations

You can translate in Localize/Weblate or propose a GitHub pull request using
only your browser. You do not need to install the tooling or edit code.

## Blank-only contributions

Fill only translation fields that were empty in the pull request's base.
Reviewers may revise those new translations within the same PR. Leave existing
nonempty translations unchanged, including fuzzy entries; do not clear review
flags. Report a suspected problem in an existing translation separately for a
maintainer's decision. Do not rewrite surrounding text while filling a gap.

CI checks this rule before merge and again before uploading to Weblate. Official
Weblate synchronization remains authoritative and is not subject to this
contributor restriction.

## Edit on GitHub

1. Open [the question outline](../tree/outline.md) and find an empty translation field.
2. Open its `translation.md` file. For a repeated string, follow the shared
   block link and edit that group's `context.md` instead.
3. Use GitHub's pencil button. Change only the text inside the
   empty `Translation ({{TARGET_LANGUAGE}})` fenced block. Keep its fences, English
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

1. Open the desired Knowledge Model version under **Knowledge Models**.
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
Source sync pauses while merged edits await Weblate import, so a failed import
does not cause your translation to be overwritten by the next scheduled run.

After successful sync and validation, changed usable translations are published
automatically. No manual tag is required. For approved, long-term downloads,
use this repository's **Releases → Latest**.
