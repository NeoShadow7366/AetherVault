---
description: How to implement a new feature from planning through verification using the agents.md framework
---

# New Feature Implementation Workflow

Follow this workflow when implementing any new feature for the Generative AI Manager.

## Prerequisites

1. Read `agents.md` fully — understand all three layers
2. Check `.agents/skills/` — is there an existing skill for your feature area?
3. Read any relevant SKILL.md files before writing code

## Step 1: Research & Understand

- [ ] Read the existing implementation files related to your feature
- [ ] Identify which backend modules and API endpoints are affected
- [ ] Check if the feature touches the database schema (metadata_db.py)
- [ ] Identify cross-platform concerns (Windows vs UNIX branching)

## Step 2: Plan the Change

Write out in natural language:
- **What** exactly will change (files, functions, endpoints)
- **Why** this approach (trade-offs considered)
- **Where** the change fits in the existing architecture

## Step 3: Red-Team Review

Before writing any code, answer these questions:

- [ ] Does this change respect the Non-Negotiable Requirements? (agents.md Layer 1)
- [ ] Could this change corrupt `metadata.sqlite`?
- [ ] Does this change work on Windows AND UNIX?
- [ ] Does this change leak file handles or subprocess PIDs?
- [ ] Is there a race condition with background scanners?
- [ ] Could this change delete user data without consent?

## Step 4: Implement

// turbo-all

1. **Backend first**: Modify `.backend/` Python files
2. **Database schema**: If adding columns, use `ALTER TABLE` with `try/except` for backward compatibility
3. **API endpoints**: Add to `do_GET()` or `do_POST()` in `server.py` 
4. **Frontend**: Update `index.html` — use template literals for dynamic HTML

### Code Standards Reminder
- Type hints on all public functions
- Docstrings on classes and non-trivial functions
- `logging.info/error` over `print()`
- Parameterized SQL queries only
- List-form `subprocess.run([...])` — never `shell=True` with user input

## Step 5: Verify

1. **Start the server**: Run `python .backend/server.py`
2. **Test the endpoint**: Use browser or curl to hit the new/modified API
3. **Cross-platform check**: Verify any OS-specific branching works
4. **Data safety check**: Confirm no user data is affected
5. **Build test**: Run `python build.py` to ensure the feature doesn't break packaging

## Step 6: Document

- [ ] Update the relevant SKILL.md if behavior changed
- [ ] Update `agents.md` if new patterns were introduced
- [ ] Add comments to non-obvious code
- [ ] Update README.md if user-facing behavior changed
