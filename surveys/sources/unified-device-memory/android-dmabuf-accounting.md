> Local Markdown copy fetched on 2026-06-22 via Claude Code's WebFetch tool (the host sandbox blocked direct `curl`). Content is the WebFetch model's extracted-Markdown rendering of the source page — not raw HTML. For canonical text, see the original URL.
>
> Source URL: https://source.android.com/docs/core/graphics/implement-dma-buf-gpu-mem
> Fetched: 2026-06-22

---

# FETCH FAILED — content not captured

The target page is "Implement DMABUF and GPU memory accounting in Android 12"
on source.android.com.

Multiple WebFetch attempts (with and without `.html`, with `?hl=en`,
plain URL, etc.) all returned the **Graphics overview** parent page
(`https://source.android.com/docs/core/graphics`) instead of the
DMA-BUF/GPU memory accounting article — even though a Google search
confirms the article exists at the requested URL.

This is most likely an SPA-hydration / pre-render mismatch between the
AOSP docs site and the WebFetch fetcher (the fetcher gets the shell page
without the per-article content rendered).

A separate WebFetch attempt against `https://web.archive.org/...` was
blocked by Claude Code policy.

## Known related page that WAS successfully fetched

For the broader ION → DMA-BUF heaps story (Android 12, GKI 2.0), the
adjacent doc is captured locally at:

  `surveys/sources/unified-device-memory/android-dmabuf-heaps.md`
  (source: https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps)

That page covers the kernel-side ION→DMA-BUF heaps transition but is
NOT a substitute for the GPU memory accounting page (which discusses
the GPU memory tracepoint / eBPF solution, `Debug` class APIs for
DMA-BUF heap pool sizes, and Lost RAM accounting in Android 12).

## Recommended next step

Either:
- retry with a different fetcher (curl with proxy, or a headless browser),
- or pull the page text from Android Code Search / git mirror of the
  AOSP docs repo, since the live docs site keeps returning the wrong body.
