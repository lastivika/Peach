# Firebase Hosting and Cognito approval review — 2026-11-14

## Firebase enabled; Cognito and publication awaiting approval

Firebase was enabled under the user's explicit authorization on the existing
project peach-lab9-2026, project number 541424029379. Firebase state is ACTIVE;
its DEFAULT_SITE is peach-lab9-2026, and the Hosting API confirms default URL
https://peach-lab9-2026.web.app. The standard companion domain is
https://peach-lab9-2026.firebaseapp.com. Neither contains a published release:
Hosting release count is zero.

The billing link and billingEnabled flag are identical before/after. No billing
API mutation, upgrade request or paid-account activation was performed. Firebase
uses the existing billing relationship (Blaze classification); no current trial
balance/expiry was re-read in this operation. The previously verified trial
status is not being represented as a new dashboard check.

Observed new APIs:
- fcm.googleapis.com
- firebaseinstallations.googleapis.com
- firebaseremoteconfig.googleapis.com
- firebaseremoteconfigrealtime.googleapis.com
- firebaserules.googleapis.com
- identitytoolkit.googleapis.com
- runtimeconfig.googleapis.com
- securetoken.googleapis.com
- testing.googleapis.com

No new service accounts appeared in the before/after inventory. The standard
Firebase-created browser API key was not retrieved or exposed. Existing SQL
instance and Run service inventories are unchanged. Storage bucket count is zero;
App Engine application is absent (404); Firestore API remains disabled, so no
Firestore inventory assertion is made beyond that observed disabled state.
No unexpected paid compute/database resources were observed. No traffic has been
published; real usage charges are not instant and no live charge total is claimed.
Terraform state was not modified. Firebase registration/default site is managed
outside the existing Terraform root in this step.

### Live Cognito inspection completed

AWS login renewal succeeded. Live client has no client secret, code grant,
openid/email/profile scopes, COGNITO/Google identity providers, SRP auth,
revocation enabled, refresh rotation enabled with 10-second grace, one-hour
ID/access tokens and one-day refresh tokens. All settings remain unchanged.

Current callbacks:
- http://localhost:3000/auth/callback/
- http://localhost:3000/callback
- https://d216r9i3ne7uiu.cloudfront.net/auth/callback/
- https://d216r9i3ne7uiu.cloudfront.net/callback

Current logout URLs:
- http://localhost:3000/
- https://d216r9i3ne7uiu.cloudfront.net/

Exact additions proposed (no removals):

Callbacks:
- https://peach-lab9-2026.web.app/auth/callback/
- https://peach-lab9-2026.firebaseapp.com/auth/callback/

Logout:
- https://peach-lab9-2026.web.app/
- https://peach-lab9-2026.firebaseapp.com/

A complete proposed update payload is saved locally in ignored
submission/lab9/cognito-update-proposed.json. It preserves every returned
update-compatible field and modifies only CallbackURLs and LogoutURLs. Only
CreationDate/LastModifiedDate (output-only fields) were excluded. This payload
was NOT submitted. Re-read live configuration before an approved update and stop
on any intervening changes; verify unchanged non-URL fields afterward. Repository
infra/auth.tf remains untouched; the corresponding additive patch is review-only.

Separate approvals still required:
1. Apply precisely these four URL additions to Cognito, retaining all existing
   URLs and authentication settings.
2. Publish only the reviewed frontend/out static build to this Hosting site using
   firebase deploy --only hosting --project peach-lab9-2026 --config firebase.json.

After those approvals, test private-browser sign-in/logout and a real authenticated
API/database read; keep token validation and owner checks intact. Live API CORS
already allows both domains, so no API change is required.

Earlier preparation and blocked-status notes below are historical and superseded
by this enablement and live-inspection record.


## Prepared build

Next.js static export completed against the real API:
https://peach-api-u2sij2lmoa-uc.a.run.app.
Existing public Cognito region/pool/client/domain values were mapped from local
configuration to NEXT_PUBLIC variables; no credentials were injected. The optional
AWS parser URL is explicitly empty pending separate parser CORS approval. Manual
agenda functionality remains available. No application mocks were introduced.

Results: lint passed, TypeScript noEmit passed, 24 tests passed (including auth
session/redirect-state tests), static export passed. Export has 96 files totaling
2,162,992 bytes. Known sensitive values from local env files and private-key,
AWS-access-key and database-URL patterns were not found; no env files/source maps
were included. This bounded scan is not an absolute proof against every possible
secret. The build manifest and hashes are in ignored
submission/lab9/frontend-build-review.json.

Hosting emulator verified seven real routes, callback query preservation and
unknown-route 404. The emulator was stopped afterward. Real API CORS preflight
passed for both proposed Firebase origins; no API/CORS change is required.

## Firebase registration gate

Fresh Firebase Management API lookup returned 404: Firebase is not yet registered.
Proposed default site ID: peach-lab9-2026. Expected URLs (not deployed or allocated
as verified Hosting sites yet):

- https://peach-lab9-2026.web.app
- https://peach-lab9-2026.firebaseapp.com

Confirm the actual site ID/default URLs after approved enablement. No second GCP
project, App Hosting server, Firebase database, Firebase Authentication or SQL
Connect instance is needed for this static Hosting deployment.

Adding Firebase enables additional APIs, adds a project label, creates a
Firebase-restricted browser API key and Firebase service accounts, including the
Firebase service agent and Admin SDK account. It cannot be fully undone. Because
this GCP project already has billing enabled, Firebase uses the Blaze pricing
classification. This is distinct from intentionally upgrading the underlying
Cloud Billing Free Trial account to Paid. Do not perform any such upgrade or
change the billing link. Stop on an upgrade/payment requirement. Firebase supports
Google Cloud trial credits, but eligibility and remaining credit must remain
verified before publishing. User approval is required for enablement's resource
changes, and publication requires separate approval.

Sources:
- https://firebase.google.com/docs/projects/use-firebase-with-existing-cloud-project
- https://firebase.google.com/support/faq/

## Minimum Cognito additions

The actual SPA redirect is origin + /auth/callback/ and logout is origin + /.
For both default Hosting domains, add only:

Callback URLs:
- https://peach-lab9-2026.web.app/auth/callback/
- https://peach-lab9-2026.firebaseapp.com/auth/callback/

Logout URLs:
- https://peach-lab9-2026.web.app/
- https://peach-lab9-2026.firebaseapp.com/

The legacy /callback redirect page does not require an additional Cognito callback
registration for this flow. The review-only docs/lab9/cognito-firebase.patch was
reduced accordingly and passes git apply --check; infra/auth.tf itself was not
changed. It preserves all URLs currently declared in repository configuration.

Live Cognito inspection is BLOCKED by expired AWS authentication. AWS CLI 2.37.7
supports aws login; confirmation to run that command was requested. Until live
inspection succeeds, preservation of every live URL/setting cannot be certified.
Do not apply the patch or send a partial update-user-pool-client request. After
login, read the client, compare Terraform/live settings, union the additions with
all existing live URLs and preserve scopes, flows, providers, token lifetimes,
revocation, rotation, branding and all other settings. If drift exists, prepare
an updated exact change for approval. Cognito requires separate explicit approval.

The frontend uses oidc-client-ts authorization code flow, its default PKCE,
sessionStorage for redirect state/user session, and Cognito ID tokens for API
requests. Authentication and backend owner checks remain unchanged. Private-
browser login, authenticated data reads and cross-user isolation are pending.

## Deployment sequence after approvals

1. Renew AWS login and finish the live Cognito review. Obtain separate approval
   for the exact additive Cognito change before any write.
2. After explicit enablement approval, run:
   firebase projects:addfirebase peach-lab9-2026
   Stop on terms or billing prompts requiring user action. Do not enable Analytics,
   extra databases or unrelated Firebase products. Verify project/site metadata
   with firebase hosting:sites:list --project peach-lab9-2026.
3. Verify trial/billing linkage remains unchanged and actual Hosting URLs match
   the approved callbacks. Review newly created service identities/API enablement.
4. After separate publication approval, confirm export manifest and public config,
   then run:
   firebase deploy --only hosting --project peach-lab9-2026 --config firebase.json
5. Verify HTTPS routes/404/callback routing, sign in in a private window, and read
   actual items/meetings from Cloud SQL through the Cloud Run API. Use legitimate
   user sessions; never paste tokens into chat or remove auth checks. Verify logout
   and two-user isolation. Any missing Cognito approval remains a login blocker.

## Costs

Current export is about 2.16 MB, well below Hosting's 10 GB storage allowance.
Hosting includes 360 MB/day data transfer; above allowances, storage is
$0.026/GB-month and data transfer $0.15/GB. Retained releases share storage quota.
Small demo usage may incur no incremental Hosting charges, but traffic and other
project usage determine this. Cloud Run/SQL/Cognito and optional integrations keep
their existing pricing; free trial credit is temporary, not a permanent discount.
Source: https://firebase.google.com/pricing (Hosting, not App Hosting).

No Firebase enablement/publication, Cognito modification, billing change, unrelated
AWS change, commit, push or destroy was performed in this preparation.
