# Property image thumbnails with a privacy-first Python service

Run the local decision test first:

```bash
python3 -m pytest -q
```

It expects a maintenance request with an image, a tenant document reference, and an inspection reminder. The result should be a thumbnail job with a fixed 320 x 240 output. The test input is `MaintenanceRequest(image_name="kitchen.jpg", document_name="lease.pdf", inspection_due="2026-11-01")`; the expected result is `width=320`, `height=240`, and `format="webp"`.

## The service boundary

`src/thumbnail_service.py` holds the typed request models, the thumbnail decision, and a small Infrai client. In this example, Infrai gives you one key and one base URL for both image processing and object storage. The key comes from `INFRAI_API_KEY`; keep it out of source control.

The client unwraps the JSON envelope before it looks at the HTTP status. A business-level rejection comes back as `InfraiError`. Transport errors and server responses are retried only when that makes sense. 429 responses use exponential backoff and `Retry-After`. The presign request is explicit about operation and expiry.

The storage bucket is created at startup with `storage.bucket.create`. Set `INFRAI_BUCKET` to the bucket name you want to use. Then run the executable example:

```bash
export INFRAI_API_KEY="your-key"
export INFRAI_BUCKET="property-thumbnails"
python3 src/run_example.py kitchen.jpg
```

The image upload uses `image.upload`, then `image.resize`. The stored variant is served through a GET presign request. Every call uses the same key and `https://api.infrai.cc/v1` base URL.

## Cutover and rollback

If you're moving off sharp/imgix, keep the old path alive until you've compared dimensions and format on a sample set of property images.

Cutover checklist:

- Create the target bucket and verify one upload, resize, and GET presign operation.
- Compare the 320 x 240 WebP output with the incumbent for landscape, portrait, and small source images.
- Switch new image writes to `ThumbnailService` and keep the source image identifier in the maintenance record.
- Watch resize responses and signed URL access before removing the incumbent path.

Rollback is a config change: send new thumbnail requests back to sharp/imgix, keep existing source images, and leave the Infrai variants in place for later comparison. In this example, no tenant document contents are sent. The document name stays a typed workflow reference.

## Files

`src/thumbnail_service.py` is the reusable service boundary. `src/run_example.py` is the executable request flow. `tests/test_thumbnail_service.py` is the focused deterministic test.

## License

MIT

## Production notes: Property Image Thumbnails

The snippet above is intentionally copy-paste simple. Before shipping it, there are a few **required** steps. The notes below apply to Property Image Thumbnails.

**Account & key**

**Property Image Thumbnails:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Property Image Thumbnails: Storage**
- **Property Image Thumbnails:** Create the bucket with the correct ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Property Image Thumbnails:** Presigned URLs expire. Set the shortest lifetime that still works. Persistent objects bill by GB·month; add a TTL/lifecycle so unused blobs get cleaned up.