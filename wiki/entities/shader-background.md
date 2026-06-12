---
tags: [component, webgl, shaders, ui]
category: entity
---

# ShaderBackground

A React component that renders an animated WebGL background on the HomePage using fragment shaders. Supports 8 visually distinct variants selectable at runtime via a dropdown.

## Architecture

The component uses a full-screen `<canvas>` element with a WebGL context. A vertex shader maps a full-viewport quad to normalized device coordinates, and fragment shaders compute per-pixel color based on time, resolution, and configurable base/accent colors.

### Shader Variants

| Variant | Style | Key Features |
|---------|-------|--------------|
| `css` | Original CSS dot grid | Not rendered via WebGL; uses `radial-gradient` CSS background with ambient glow orbs. Selected by default. |
| `css_emerald` | CSS-like dot grid with emerald shimmer | Pixel-ratio-aware grid matching the CSS 24px spacing, emerald green dots on dark background, individual dot shimmer |
| `pointillism` | High-density pointillist dots | 150×150 logical grid, soft-edged circles, individual dot glow animation |
| `waves` | Horizontal wave lines | Multiple sine-wave layers with varying frequency and speed, three horizontal line bands |
| `nexus` | Animated grid with intersection highlights | 8×8 grid with moving intersection points that pulse and glow |
| `cosmic` | Starfield with nebula | 120×120 grid of stars (97% sparse) with brightness oscillation, slow nebula overlay |
| `emerald_tide` | Wavy emerald dots | 55×55 dot grid with horizontal wave distortion, forest/patina color palette |
| `royal_bronze` | Woven bronze shimmer | 120×120 staggered grid with burnished bronze dots and slow shimmer on midnight background |

### Safety & Performance

- **Context loss handling**: Listens for `webglcontextlost` and `webglcontextrestored` events; pauses rendering on loss and reinitializes on restore
- **Visibility-aware**: Pauses the animation loop when the tab is hidden via `visibilitychange` event
- **Pixel ratio clamping**: Caps `devicePixelRatio` at 1.5 to reduce GPU load on high-DPI displays
- **Logical pixel mapping**: Injects `u_pixelRatio` into shaders to guarantee physical-to-logical CSS pixel mapping (preventing grids from bunching together on retina displays)
- **Proper cleanup**: Cancels animation frame, removes event listeners, and deletes WebGL resources on unmount

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `ShaderVariant` | `'pointillism'` | Which shader variant to render |
| `baseColor` | `[number, number, number]` | `[0.02, 0.05, 0.04]` | Base RGB color (0.0–1.0) |
| `accentColor` | `[number, number, number]` | `[0.85, 0.75, 0.45]` | Accent RGB color (0.0–1.0) |

## HomePage Integration

The HomePage uses `useState` to track the selected variant and renders either the original CSS background or the WebGL `ShaderBackground` component. A `<select>` dropdown in the header allows users to switch variants at runtime.

## Testing

`ShaderBackground.test.tsx` verifies:
- Canvas renders with correct Tailwind positioning classes (`fixed inset-0 -z-10 pointer-events-none w-screen h-screen`)
- `getContext('webgl')` is called on the canvas element
- Mocked `requestAnimationFrame` and `cancelAnimationFrame` prevent actual rendering loops

## Related

- [[entities/web-app]] — TanStack Start dashboard
- [[entities/design-system]] — Shared UI component library
