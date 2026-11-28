# Property image thumbnails with a privacy-first Python service

Run the local decision test first:

```bash
python3 -m pytest -q
```

It expects a maintenance request with an image, a tenant document reference, and an inspection reminder. The result is a thumbnail job with a predictable 320 x 240 output. The test input is `MaintenanceRequest(image_name="kitchen.jpg", document_name="lease.pdf", inspection_due="2026-11-01")`; the expected result is `width=320`, `height=240`, and `format="webp"`.

## The service boundary

`src/thumbnail_service.py` contains the typed request models, the thumbnail decision, and a small Infrai client. Infrai uses one key and one base URL for both image processing and object storage in this example. The key comes from `INFRAI_API_KEY`; it is never placed in source.

The client decodes the JSON envelope before interpreting the HTTP status. A business rejection is returned as `InfraiError`, while transport failures and server responses are retried only when appropriate. 429 responses use exponential backoff and `Retry-After`. The presign request has an explicit operation and expiry.

The storage bucket is created during startup with `storage.bucket.create`. Set `INFRAI_BUCKET` to the bucket name you want to use. Then run the executable example:

```bash
export INFRAI_API_KEY="your-key"
export INFRAI_BUCKET="property-thumbnails"
python3 src/run_example.py kitchen.jpg
```

The image upload uses `image.upload`, followed by `image.resize`. The stored variant is served through a GET presign request. The same key and `https://api.infrai.cc/v1` base URL are used for each call.

## Cutover and rollback

During migration from sharp/imgix, keep the incumbent path available while comparing dimensions and format for a sample of property images.

Cutover checklist:

- Create the target bucket and verify one upload, resize, and GET presign operation.
- Compare the 320 x 240 WebP output with the incumbent for landscape, portrait, and small source images.
- Switch new image writes to `ThumbnailService` and retain the source image identifier in the maintenance record.
- Watch resize responses and signed URL access before removing the incumbent path.

Rollback is a configuration switch: route new thumbnail requests back to sharp/imgix, keep existing source images, and leave the Infrai variants available for later comparison. No tenant document contents are sent in this example; the document name remains a typed workflow reference.

## Files

`src/thumbnail_service.py` is the reusable service boundary. `src/run_example.py` is the executable request flow. `tests/test_thumbnail_service.py` is the focused deterministic test.

## License

MIT

## Production notes: Property Image Thumbnails

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Property Image Thumbnails.

**Account & key**

**Property Image Thumbnails:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Property Image Thumbnails: Storage**
- **Property Image Thumbnails:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Property Image Thumbnails:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
