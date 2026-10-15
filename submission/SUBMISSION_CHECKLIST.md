# Submission Checklist

- [x] Push the lab code and submission package to `main`.
- [ ] Submit the repository: https://github.com/lastivika/Peach
- [x] Latest prior commit: https://github.com/lastivika/Peach/commit/11be2093da7f461ed2072b3d7e4be4f13011efe4
- [ ] Include `STEP7_ANSWERS.md`, `TEST_EVIDENCE.md`, `FINAL_REPORT.md`, `SCREENSHOTS_GUIDE.md`, and `ARCHITECTURE.md` from this folder.
- [ ] Capture the genuine AWS Console screenshots listed in `SCREENSHOTS_GUIDE.md` after reconnecting AWS and cleaning up temporary resources.
- [ ] Do not claim inbox receipt; SES aggregate statistics show attempts, not inbox delivery.
- [ ] Complete the remaining items in `STEP7_ANSWERS.md`: post-redrive log verification and cleanup, image build/deploy with the local trigger markers, and production duplicate-week verification.
- [ ] Preserve `frontend/.prettierignore`; it is an unrelated local change.

**Manual action currently required:** Complete AWS sign-in for profile `peach-lab` (the CLI token endpoint was unreachable and the browser sign-in page did not finish loading), then verify and clean up the isolated test resources listed in `FINAL_REPORT.md`. After access is restored, verify post-redrive logs, build/publish/deploy the tested ARM64 images, capture the three trigger markers, and run the missing duplicate-week check. No AWS mutation or cleanup was performed during the latest continuation.
