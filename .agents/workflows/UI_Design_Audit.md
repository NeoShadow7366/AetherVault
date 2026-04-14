---
name: UI Design Audit
description: Invokes the Frontend Experience Guardian to perform a deep DOM, CSS, and aesthetic inspection of the frontend monolith.
---

# 🎨 UI Design Audit Workflow (`/UI_Design_Audit`)

## Goal
To evaluate `static/index.html` and associated CSS/JS against the strict "Premium Design" guidelines, DOM integrity rules (unique IDs), and Accessibility (A11y) constraints maintained by the **Frontend Experience Guardian**.

## Triggered By
- User manually types `/UI_Design_Audit`.
- Often run post-feature-complete in a frontend sprint to ensure UI polish.

---

## 📋 Execution Steps

### Step 1: Initialize Frontend Experience Guardian
1. Load the instructions from `.agents/skills/frontend_experience_guardian/SKILL.md`.
2. Locate the primary frontend monolith (typically `.backend/static/index.html`).

### Step 2: DOM & ID Integrity Check
1. Read the `index.html` content.
2. Scan for missing `id` attributes on interactive elements (buttons, inputs, selects). The QA Guardian relies on these for E2E tests.
3. Validate Semantic HTML (ensure there is only one logical `<h1>`, use of `<section>`/`<nav>`, etc.).

### Step 3: Aesthetic & Polish Review
1. Look for inline styles (`style="..."`) that should be formal CSS utility classes.
2. Check for missing interactive states (lack of hover/focus pseudo-classes or transitions).
3. Validate against premium design traits (e.g., verifying that "flat" unstyled generic elements aren't accidentally bypassing the dynamic themes/glassmorphism classes).

### Step 4: Accessibility Check
1. Ensure all icon-only buttons (`<i>`, SVG elements) have appropriate `aria-labels` or title attributes.
2. Confirm contrast ratios and form-label associations.

### Step 5: Generate Report
1. Create (or update) a `UI_Audit_Report.md` artifact detailing:
   - **Critical Violations:** Missing IDs, broken semantics.
   - **A11y Warnings:** Missing aria-labels.
   - **Aesthetic Recommendations:** Opportunities for micro-animations, glassmorphism, or modern typography adoption.

> **Note to Agent:** Do NOT automatically alter the HTML/CSS code unless explicitly requested by the user after the report is generated, as visual context is required for final styling decisions.
