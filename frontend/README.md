# DiabeticCARE frontend

## Run

From `frontend`:

```sh
npm install
npm run dev
```

Start the existing FastAPI backend on port 8000 using its README. Open
http://127.0.0.1:3000 and sign in. `NEXT_PUBLIC_API_URL` uses the existing login
configuration; override it in `.env.local` and restart Next.js when needed.
Backend CORS must allow the frontend origin.

## Patient Diet pages

`/dashboard/diet` provides Nutrition & Diet, an Analyze My Meal link, and honest
empty states for Latest Meal Assessment, Nutrition Summary and Meal History.
`/diet` preserves the application shell, sidebar and navy/green design system.

1. Choose or drop a JPG/JPEG, PNG or WebP meal photo (up to 10 MiB and 20 million pixels).
2. Review the preview and click **Analyze Meal**. Choosing a file sends no request.
3. Review the Meal Summary, food-name overlays and one card per grouped food.
4. Use **Choose Another Image**, **Analyze Another Meal**, or **Reset** to clear results.

Cards display Small/Medium/Large/Unknown portions, Reference Nutrition, and
Estimated Intake. Nutrition details expand into Macronutrients, Vitamins and
Minerals, with the source at the bottom. Null values are omitted; numeric zero
is retained. Reference values keep their supplied per-100-g or per-serving basis,
including the original serving quantity when available. Missing references show
**Nutrition Information / Not available yet**.

Current serving-weight evidence is unavailable for all 46 foods, so intake shows
**Serving-based nutrition is not available yet.** Future sourced estimates can
show mass and available nutrients. Visual portion categories are not converted
to grams by the frontend. No meal totals, GI/GL or recommendations are calculated.

Model names, confidence, method names, mapping statuses, completeness metadata,
internal notes and research badges are hidden from the patient UI. Raw API data
and calculations are preserved. One nutrition reference disclaimer appears at
the bottom of the page.

## API and image behavior

The page uses `useDietConsumedNutrition` and one multipart
`POST /api/diet/estimate-consumed-nutrition` request with field `image`.
The browser supplies the Content-Type boundary. The response contains grouped
`foods`, `portion_summary` and raw `detections`; the adapter attaches grouped
values while preserving individual detections and box coordinates. Image overlays
use the original image dimensions and food names only.

Changing/removing an image aborts the active request and ignores stale responses.
Preview URLs are released on change and unmount. Images are sent without resizing
and are not saved by this interface. Native image orientation matches the backend
coordinate system. Empty results, invalid uploads, network errors and timeouts
have patient-facing messages.

Standalone detection, portion and nutrition helpers/hooks remain available for
existing consumers. Backend model, nutrition lookup and portion calculations are
unchanged by the presentation redesign.

## Checks

```sh
npm run test:diet
npm run build
```

No lint command is configured. Unit checks cover validation, response adapters,
coordinates, safe errors, cancellation, nutrient grouping and zero/null handling.
Browser checks cover the dashboard link, a real combined analysis request,
grouped food cards, nutrient expansion, missing nutrition, one footer note,
reset, desktop/tablet/mobile overflow and unchanged overlay alignment.

## Glycemic Index

Meal results may show a patient-facing Glycemic Index card with a reference GI
value and Low, Medium or High explanation. Unavailable values show “Not available
yet”. Mapping statuses and source identifiers stay out of the patient UI. GI is
food/preparation specific and does not represent total meal impact; no meal GI or
Glycemic Load is calculated in this stage.
