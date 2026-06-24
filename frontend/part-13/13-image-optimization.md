# Part 13.3: Image Optimization

## What You'll Learn

- Modern image formats (WebP, AVIF)
- Responsive images with srcset
- Lazy loading strategies
- Image CDNs and optimization services
- Placeholder techniques (blur, LQIP)
- Vite image optimization plugins

---

## Table of Contents

1. [Image Format Guide](#image-format-guide)
2. [Responsive Images](#responsive-images)
3. [Lazy Loading](#lazy-loading)
4. [Placeholder Strategies](#placeholder-strategies)
5. [Image CDNs](#image-cdns)
6. [Vite Image Optimization](#vite-image-optimization)
7. [React Image Component](#react-image-component)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Resources](#resources)

---

## Image Format Guide

```
Format      │ Quality │ Size    │ Browser Support │ Best For
────────────┼─────────┼─────────┼─────────────────┼──────────
JPEG        │ Good    │ Medium  │ Universal       │ Photos
PNG         │ Perfect │ Large   │ Universal       │ Transparency, icons
WebP        │ Great   │ Small   │ 97%+            │ General (preferred)
AVIF        │ Best    │ Smallest│ 92%+            │ Photos (best compression)
SVG         │ Perfect │ Tiny    │ Universal       │ Icons, logos, illustrations

Recommendation:
1. Icons/logos → SVG
2. Photos → AVIF with WebP fallback
3. Screenshots → WebP
4. Tiny images → Inline SVG or base64
```

---

## Responsive Images

### srcset and sizes

```html
<!-- Different sizes for different screens -->
<img
  src="/images/hero-800.webp"
  srcset="
    /images/hero-400.webp 400w,
    /images/hero-800.webp 800w,
    /images/hero-1200.webp 1200w,
    /images/hero-1600.webp 1600w
  "
  sizes="(max-width: 640px) 100vw, (max-width: 1024px) 80vw, 1200px"
  alt="Hero image"
  width="1200"
  height="600"
/>

<!-- Picture element for format fallback -->
<picture>
  <source srcset="/hero.avif" type="image/avif" />
  <source srcset="/hero.webp" type="image/webp" />
  <img src="/hero.jpg" alt="Hero" width="1200" height="600" />
</picture>
```

---

## Lazy Loading

```typescript
// Native lazy loading (recommended)
<img src="/photo.webp" loading="lazy" alt="Photo" width={400} height={300} />

// Exceptions: DON'T lazy load above-the-fold images
<img src="/hero.webp" loading="eager" fetchPriority="high" alt="Hero" />

// Intersection Observer for more control
function LazyImage({ src, alt, ...props }) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setIsVisible(true); observer.disconnect(); } },
      { rootMargin: '200px' }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className="relative overflow-hidden bg-gray-100" style={{ aspectRatio: props.width / props.height }}>
      {isVisible && (
        <img
          src={src}
          alt={alt}
          onLoad={() => setIsLoaded(true)}
          className={cn('w-full h-full object-cover transition-opacity duration-300', isLoaded ? 'opacity-100' : 'opacity-0')}
          {...props}
        />
      )}
    </div>
  );
}
```

---

## Placeholder Strategies

### Blur Hash Placeholder

```typescript
// Using blurhash for beautiful placeholders
import { Blurhash } from 'react-blurhash';

function OptimizedImage({ src, hash, alt, width, height }) {
  const [isLoaded, setIsLoaded] = useState(false);

  return (
    <div className="relative overflow-hidden" style={{ aspectRatio: width / height }}>
      {/* Blur placeholder */}
      {!isLoaded && (
        <Blurhash hash={hash} width="100%" height="100%" className="absolute inset-0" />
      )}

      {/* Actual image */}
      <img
        src={src}
        alt={alt}
        loading="lazy"
        onLoad={() => setIsLoaded(true)}
        className={cn('w-full h-full object-cover transition-opacity duration-500', isLoaded ? 'opacity-100' : 'opacity-0')}
      />
    </div>
  );
}
```

### CSS Shimmer Placeholder

```typescript
function ImageWithShimmer({ src, alt, className }) {
  const [loaded, setLoaded] = useState(false);

  return (
    <div className={cn('relative overflow-hidden bg-gray-200', className)}>
      {!loaded && (
        <div className="absolute inset-0 animate-shimmer bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 bg-[length:200%_100%]" />
      )}
      <img src={src} alt={alt} loading="lazy" onLoad={() => setLoaded(true)}
        className={cn('w-full h-full object-cover', loaded ? 'opacity-100' : 'opacity-0')} />
    </div>
  );
}
```

---

## Image CDNs

```
Popular image CDN services:
1. Cloudinary  - Transform, optimize, deliver
2. imgix       - Real-time image processing
3. Cloudflare  - Images (built into Cloudflare)
4. Vercel      - next/image optimization
5. Bunny.net   - CDN with image optimization

Benefits:
- Automatic format conversion (WebP/AVIF)
- On-the-fly resizing
- Global CDN delivery
- Quality optimization
- Responsive image generation
```

```typescript
// Cloudinary URL-based transformation
function cloudinaryUrl(publicId: string, width: number, quality = 'auto') {
  return `https://res.cloudinary.com/yourcloud/image/upload/w_${width},q_${quality},f_auto/${publicId}`;
}

// Usage
<img
  src={cloudinaryUrl('hero', 1200)}
  srcSet={`
    ${cloudinaryUrl('hero', 400)} 400w,
    ${cloudinaryUrl('hero', 800)} 800w,
    ${cloudinaryUrl('hero', 1200)} 1200w
  `}
  sizes="(max-width: 640px) 100vw, 1200px"
  alt="Hero"
/>
```

---

## Vite Image Optimization

```bash
pnpm add -D vite-plugin-image-optimizer
```

```typescript
// vite.config.ts
import { imageOptimizer } from 'vite-plugin-image-optimizer';

export default defineConfig({
  plugins: [
    react(),
    imageOptimizer({
      png: { quality: 80 },
      jpeg: { quality: 80 },
      webp: { quality: 80 },
      avif: { quality: 65 },
    }),
  ],
});
```

---

## React Image Component

```typescript
// Reusable optimized image component
interface OptimizedImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string;
  alt: string;
  priority?: boolean;
  placeholder?: 'blur' | 'shimmer' | 'none';
  aspectRatio?: number;
}

function OptimizedImage({
  src, alt, priority = false, placeholder = 'shimmer',
  aspectRatio, className, ...props
}: OptimizedImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);

  return (
    <div className={cn('relative overflow-hidden', className)}
      style={aspectRatio ? { aspectRatio } : undefined}>
      {/* Placeholder */}
      {!isLoaded && placeholder === 'shimmer' && (
        <div className="absolute inset-0 bg-gray-200 animate-pulse" />
      )}

      <img
        src={src}
        alt={alt}
        loading={priority ? 'eager' : 'lazy'}
        fetchPriority={priority ? 'high' : undefined}
        decoding="async"
        onLoad={() => setIsLoaded(true)}
        className={cn('w-full h-full object-cover transition-opacity duration-300',
          isLoaded ? 'opacity-100' : 'opacity-0')}
        {...props}
      />
    </div>
  );
}
```

---

## Common Patterns & Best Practices

- Use WebP/AVIF with JPEG fallback for photos
- Always specify width/height to prevent CLS
- Lazy load everything below the fold
- Use `fetchPriority="high"` for LCP images
- Serve responsive sizes via srcset
- Consider an image CDN for dynamic optimization
- Compress images at build time with Vite plugins

---

## Resources

- **web.dev Image Optimization:** https://web.dev/fast/#optimize-your-images
- **Squoosh (Image Compression):** https://squoosh.app/
- **BlurHash:** https://blurha.sh/
- **Cloudinary:** https://cloudinary.com/

---

**Next:** [Part 13.4: Build & Bundle Size Optimization](./13-build-size-optimization.md)
