# Tasks tracking - Invoice Extractor

## Epic: Documentation Overhaul (v2.1.0)

Goal: Ensure all documentation is accurate, consistent, and reflects the latest features.

---

Name: Update README.md
Status: [x]
Goal: Update the main documentation to version 2.1.0 and include new features.
Details:

- Update version number
- Add supplier/client correction logic details
- Synchronize default models with deploy script
Testing: Manual review of the README rendering.

---

Name: Update CONFIGURATION.md
Status: [x]
Goal: Synchronize configuration guide with `src_propre/config.py`.
Details:

- Update env vars table
- List all supported Bedrock models
- Document supplier correction lists
Testing: Manual verification against source code.

---

Name: Update DEPLOY.md
Status: [x]
Goal: Ensure deployment instructions are accurate.
Details:

- Focus on `deploy.py` as the recommended method
- Verify CLI parameter examples
Testing: Manual review of commands.

---

Name: Update CHANGELOG.md
Status: [x]
Goal: Document changes in version 2.1.0.
Details:

- Add entry for 2.1.0
- List simplified PDF extraction and supplier fix
Testing: Manual review.

---

Name: Update CONTRIBUTING.md
Status: [x]
Goal: Keep repository structure map up to date.
Details:

- Update file/directory descriptions
Testing: Manual review.

---

Name: Project Cleanup & Text Refining
Status: [x]
Goal: Reorganize the repository and improve text consistency.
Details:

- Prefix unused files with `not_used_`
- Reverted `cleanup.py` to active status (still in use)
- Remove references to missing scripts
- Synchronize `.env` and `env.example`
- Refine code comments in French
Testing: Verify file names and documentation accuracy.

---
