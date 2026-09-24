# AI-assisted evidence reporting

The reporting form now has four steps: Upload Evidence, Describe Observation, Select River Location, and Review & Submit. Photos upload immediately in Step 1 and are retained between steps; submission reuses their stored URLs. Citizens can always change the category. Reports remain UNVERIFIED until authority review.

## Enable Gemini

Set these backend variables in `.env` locally or in the Vercel project's environment, then restart the backend or redeploy:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your-private-key
AI_MODEL=gemini-3.8-flash
AI_CONFIDENCE_THRESHOLD=0.75
AI_TIMEOUT_SECONDS=20
```

Choose a vision-capable model available to your Gemini account. The model identifier is configurable. Never put the provider key in a VITE_* variable. Without a key, with `AI_PROVIDER=disabled`, or when Gemini fails, the form explains that automatic analysis is unavailable and accepts manual selection. AI failure never prevents a report. Photos still need working local/Blob evidence storage.

The adapter uses Gemini's REST generateContent endpoint and JSON response schema, without installing a model or a large SDK. Resized, EXIF-stripped JPEG copies are sent to Gemini when enabled. Report originals use the existing evidence-upload path. No photos or keys are written to inference logs.

References: [Gemini image inputs](https://ai.google.dev/gemini-api/docs/image-understanding), [generateContent API](https://ai.google.dev/api/generate-content).

## API and aggregation

`POST /api/ai/classify-contamination` accepts multipart `images[]`, up to the configured image count. The batch payload is limited to 4 MiB on Vercel (20 MiB locally); the UI sends images individually to stay within Vercel request limits, with at most two analysis requests in flight. Individual uploads retain the existing size/type/pixel-count checks.

The provider returns one validated category/confidence per image. All images participate in majority voting. Confidence is the average for the winning category; tied votes produce Other / Unclear at zero confidence. Results below the configurable threshold do not auto-select a specific category. A partial inference failure uses manual selection for the whole set, rather than silently ignoring an image. Removing an image recomputes the suggestion. A late response cannot overwrite a citizen's manual choice.

The abstract `ImageClassifier.classify(images)` interface and factory in `backend/app/image_classifier.py` isolate providers from the route and UI. Add a new adapter there to support another cloud or local model.

## Persistence and interpretation

The additive `report_classifications` table stores original AI category/confidence, final citizen category, source (AI_CONFIRMED, USER_CORRECTED, MANUAL), and per-image results. No existing tables are dropped or altered. Legacy reports display manual classification; their existing categories remain valid. Case review shows both suggestion and citizen choice.

Submitted classification metadata is citizen-provided, schema-validated context; it is not a signed model attestation. The backend recomputes the aggregate and source from the per-image results and final category. Confidence is a model estimate, not a calibrated pollution probability. Neither confidence nor AI_CONFIRMED verifies pollution or changes authority status/impact calculations.

## Validation scope

Automated tests use controlled provider responses for fish, plastic, foam, oil-like surfaces, discoloration, blurry/unrelated images, ties, low confidence, provider failure, multiple images, corrections, and stored evidence. Browser tests exercise the complete report and admin flow. These are integration/contract checks, not a real-world model accuracy evaluation.

A live Gemini key has not yet been configured for this implementation. Before relying on suggestions, test representative real photos with the configured model, including unrelated and blurry photos. Record false positives and tune the threshold. No live accuracy claim is made by the automated tests.

## Inference reliability update

Gemini requests now allow up to 20 seconds per attempt and retry once for timeouts, network failures, HTTP 429, and temporary server errors. Authentication/model errors are not automatically retried. The browser allows 50 seconds for each analysis request. Failed images have a Retry analysis button that reuses their selected files and does not upload evidence again.

Local Gemini credentials have since been configured privately. A live generated-image check through port 5175 succeeded. Real-photo accuracy remains unverified; automatic approval review blocked sending an existing potentially sensitive evidence photo without specific authorization. Nineteen classifier tests and five browser checks passed for this reliability change.
