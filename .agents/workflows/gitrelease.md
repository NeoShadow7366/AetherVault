---
description: Prompts the user for a semantic version, creates a Git tag, and pushes it to trigger the automated CI/CD release pipeline.
---
# Trigger the GitHub Actions CI/CD Pipeline

When the user runs `/gitrelease`, you MUST execute the following step-by-step workflow:

1. Stop and ask the user for the release context by prompting:
   "What version number would you like to stamp this release with? (e.g., v1.0.0)"
   Ensure you politely remind them that all current changes should be committed and pushed before cutting the tag, otherwise the release build will fall behind their local progress.

2. Wait for the user to provide the version string. Ensure the version string strictly starts with a `v` (like `v1.2.0`) as required by the `.github/workflows/release.yml` listener you created. If they forget the `v`, prepend it for them.

3. Once the user provides the specific version, immediately execute the following commands using the terminal auto-run `turbo` directives to stamp the repository and trigger the cloud builder:

// turbo
4. Run: `git tag [USER_VERSION_STRING]`

// turbo
5. Run: `git push origin [USER_VERSION_STRING]`

6. Confirm to the user that the tag was successfully pushed, and explain that the remote GitHub Actions runner is now automatically compiling `Local AI Tool.exe`, bundling `AIManager_Release.zip`, and staging it on the Releases page!
