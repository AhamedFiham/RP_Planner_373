# DiabeticCARE frontend

## Run

From `frontend`:

```sh
npm install
npm run dev
```

Open http://127.0.0.1:3000, sign in, and choose **Diet Planner → Open Food
Detector** (or open `/diet`). Start the existing FastAPI backend on port 8000
using its backend README. `NEXT_PUBLIC_API_URL` matches the existing login
configuration; to override it, copy `.env.example` to `.env.local`, edit the URL,
and restart/rebuild Next.js. Backend CORS must allow the frontend origin.

## Food detector

1. Choose or drop one JPG/JPEG, PNG or WebP meal image (up to 10 MiB and 20 million pixels).
2. Review the local preview and click **Analyze Meal**. Selecting a file never starts inference.
3. Review the actual backend detections and confidence percentages. Boxes scale as percentages of the backend image dimensions.
4. Use **Change Image**, **Analyze Another Meal**, or **Reset** to clear prior results.

The request is multipart `POST /api/diet/detect-food` with field `image`.
The browser supplies the Content-Type boundary. The interface handles successful
empty results, invalid images, server errors, unavailable backend and timeouts.
Changing/removing an image aborts the active request and ignores stale responses.
Blob preview URLs are released on change and unmount. The original file is sent
without resizing; no image is saved by this interface. The preview uses native
image orientation (`image-orientation: none`) to match the backend's decoded
pixel coordinates. Bounding boxes and the list use actual API results only.

Confidence labels are UI descriptions: High >=75%, Medium >=50%, Low <50%.
They do not filter or modify predictions. Low-confidence predictions should be
reviewed. This interface does not estimate portions, nutrition, GI/GL or provide
diet recommendations. Existing downstream diet components are preserved.

## Checks

```sh
npm run test:diet
npm run build
```

No lint command is configured. Unit checks cover file validation, response
validation, relative box coordinates, multipart field names, safe errors and
cancellation. Browser checks also covered real JPG and PNG requests, multiple
real detections, desktop/mobile overlay alignment, no-detection and service-error
states, and change/reset actions. Empty/error responses were intercepted only
inside the browser test; no placeholder detections are included in production UI.
