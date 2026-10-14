ClauseLens property-purchase and mobile-language fixes

What changed

Added property_purchase as a supported document family in configs/scope.yaml and configs/taxonomy.yaml.

Improved document-type detection so a home purchase agreement is not treated as a rental agreement solely because it mentions a flat, buyer or seller.

Added six property-specific clause types: property specifications, title/encumbrances, possession/handover, booking/payment, cancellation/refund, and registration charges.

Added high-precision property clause overrides so an explicit “Property Specifications” clause cannot remain labelled as “Guests & subletting” just because the old model was confident.

Added property-specific risk rules and grounded, template-based explanations. For these new labels, the old rental/employment risk model is deliberately not used until property-specific labelled data is available.

Added contextual extraction roles for purchase consideration, booking amount and registration charges.

Added a property-purchase demo sample to the API and the React sample selector.

Fixed mobile CSS so the EN/HI interface switch remains visible at widths up to 760px. At very narrow widths the search control is hidden to make room for the language switch.

Added Hindi UI strings for the new labels.

Added a dependency-free near-duplicate fallback for minimal test environments without datasketch.

Fixed the Docker build command: this repository snapshot does not include frontend/package-lock.json, so npm ci would fail at the COPY step. The Docker build now installs from package.json using npm install.

Local tests run

Command:

PYTHONPATH=src python -m pytest -q -ra
python -m compileall -q src tests

Result: 140 passed, 3 skipped, 0 failed (143 tests collected). The skipped tests require optional dependencies not installed in this environment: transformers, datasets, and langgraph.

The test suite includes property-purchase detection, property-clause override, contextual amount extraction, property sample API, risk flagging for unilateral property-specification changes, mobile language-switch CSS checks, and Dockerfile checks.

Frontend build status

npm run build was attempted in frontend/, but could not run in this environment because node_modules/Vite are not installed and package-registry network access is unavailable (vite: not found). The JSX/CSS changes were checked with static regression tests, but a production browser build has not been verified locally. The Render Docker build installs dependencies during image build.

Redeploy checklist

Copy the changed files into the repository while preserving their paths.

Commit and push to the branch Render deploys from.

In Render, confirm the Docker build reaches npm install and npm run build without errors.

After deployment, open /api/health and confirm it returns status: ok.

In ClauseLens, select Home purchase agreement from the sample selector and run analysis.

Confirm the sample clause about changes to property specifications is labelled Property specifications and changes, not Guests & subletting, and that the “without prior written consent” wording triggers a rule-based red flag.

Open the same site on a phone. Confirm EN/HI remains visible in the top bar and both buttons switch interface language.

Important limitations

Property rules are an initial deterministic screening layer, not a substitute for advocate review.

The existing risk model is not used for the new property-specific categories until a reviewed property-purchase dataset is available.

Local production frontend build and live Render deployment were not executable/verified from this environment. Do not describe this build as deployed until Render confirms it.