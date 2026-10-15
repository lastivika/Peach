# Submission Checklist

- [x] Push the lab code and submission package to `main`.
- [ ] Submit the repository: https://github.com/lastivika/Peach
- [x] Final commit: https://github.com/lastivika/Peach/commit/151026eb2e29b441d48de88580cf4ebb7496b390
- [ ] Include `STEP7_ANSWERS.md`, `TEST_EVIDENCE.md`, `FINAL_REPORT.md`, `SCREENSHOTS_GUIDE.md`, and `ARCHITECTURE.md` from this folder.
- [ ] Capture the genuine AWS Console screenshots listed in `SCREENSHOTS_GUIDE.md` after reconnecting AWS and cleaning up temporary resources.
- [ ] Do not claim inbox receipt; SES aggregate statistics show attempts, not inbox delivery.
- [ ] Complete the remaining items in `STEP7_ANSWERS.md`: post-redrive log verification and cleanup, image build/deploy with the local trigger markers, and production duplicate-week verification.
- [ ] Preserve `frontend/.prettierignore`; it is an unrelated local change.

**Manual action currently required:** Reconnect the AWS MCP session (or clean up the isolated test resources listed in `FINAL_REPORT.md` from the AWS Console). A credential-safe ECR Docker login route is also needed before the new image can be published.
