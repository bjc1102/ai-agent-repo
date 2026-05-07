---
name: Synthetic Intelligence Finance
colors:
  surface: '#0d150e'
  surface-dim: '#0d150e'
  surface-bright: '#323c33'
  surface-container-lowest: '#081009'
  surface-container-low: '#151e16'
  surface-container: '#19221a'
  surface-container-high: '#232c24'
  surface-container-highest: '#2e372e'
  on-surface: '#dbe5d9'
  on-surface-variant: '#bacbb9'
  inverse-surface: '#dbe5d9'
  inverse-on-surface: '#29332a'
  outline: '#859585'
  outline-variant: '#3b4a3d'
  surface-tint: '#00e475'
  primary: '#75ff9e'
  on-primary: '#003918'
  primary-container: '#00e676'
  on-primary-container: '#00612e'
  inverse-primary: '#006d35'
  secondary: '#ffb3ae'
  on-secondary: '#68000c'
  secondary-container: '#a00118'
  on-secondary-container: '#ffa8a3'
  tertiary: '#ffdec4'
  on-tertiary: '#4b2800'
  tertiary-container: '#ffba79'
  on-tertiary-container: '#794810'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#62ff96'
  primary-fixed-dim: '#00e475'
  on-primary-fixed: '#00210b'
  on-primary-fixed-variant: '#005226'
  secondary-fixed: '#ffdad7'
  secondary-fixed-dim: '#ffb3ae'
  on-secondary-fixed: '#410004'
  on-secondary-fixed-variant: '#930015'
  tertiary-fixed: '#ffdcbf'
  tertiary-fixed-dim: '#fdb878'
  on-tertiary-fixed: '#2d1600'
  on-tertiary-fixed-variant: '#6a3c03'
  background: '#0d150e'
  on-background: '#dbe5d9'
  surface-variant: '#2e372e'
typography:
  h1:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  data-lg:
    fontFamily: Roboto Mono
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
    letterSpacing: -0.02em
  data-md:
    fontFamily: Roboto Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: '0'
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  gutter: 20px
  margin: 32px
---

## Brand & Style

This design system is engineered for the high-stakes world of AI-driven finance. The brand personality is **technical, analytical, and authoritative**, aiming to evoke a sense of absolute precision and futuristic reliability. 

The aesthetic blends **Modern Dark Mode** with **Technical Minimalism**. It leverages deep charcoal backgrounds to reduce visual fatigue during long-term data monitoring, while using high-vibrancy accents to highlight critical market movements. The inclusion of subtle neon glows and monospaced data points creates an interface that feels like a sophisticated trading terminal designed for the next generation of synthetic intelligence.

## Colors

The color palette is optimized for high-contrast legibility in dark environments. 

- **Base:** The background uses a deep `#121212` to provide a true dark-mode experience, with elevated surfaces utilizing `#1E1E1E`.
- **Accents:** The system employs a binary logic for financial indicators. **Mint (#00E676)** signifies growth, success, and positive synthetic signals. **Coral Red (#FF5252)** is reserved for decline, risk, and negative data points.
- **Borders:** A consistent, low-opacity stroke `rgba(255, 255, 255, 0.08)` is used to define boundaries without adding visual noise.
- **Glows:** Active states and CTA buttons utilize a 15-25% opacity glow based on the primary Mint accent to simulate a technical, illuminated hardware aesthetic.

## Typography

The typography strategy prioritizes functional distinction between narrative content and quantitative data.

- **Inter:** Used for all interface labels, headlines, and body copy. Its neutral, geometric clarity provides a professional and systematic tone.
- **Roboto Mono:** Exclusively used for numbers, price tickers, timestamps, and code-based signals. The fixed-width nature ensures that fluctuating data points do not cause horizontal layout shifts, maintaining visual stability during high-volatility events.

## Layout & Spacing

This design system utilizes a **8px grid system** to ensure mathematical consistency across all components. 

The layout philosophy follows a **Fluid Grid** model with a 12-column structure for desktop views. Large margins (32px) and generous gutters (20px) are used to prevent the dense financial information from feeling cluttered. Data-heavy dashboards should prioritize vertical rhythm using the `md` (16px) and `lg` (24px) spacing units to group related information blocks logically.

## Elevation & Depth

Depth is conveyed through **Tonal Layering** and **Subtle Outlines** rather than heavy shadows.

- **Level 0:** Background `#121212`.
- **Level 1:** Cards and Containers `#1E1E1E` with a 1px stroke of `rgba(255, 255, 255, 0.08)`.
- **Level 2:** Modals and Pop-overs `#252525` with a slightly more pronounced stroke and a very soft 24px blur black shadow to separate from the background.
- **Interactive Depth:** Buttons and active elements do not "lift" physically but "activate" through color transitions and a 12px outer glow (`drop-shadow`) using the Mint accent color at 30% opacity.

## Shapes

The shape language is defined by a consistent **12px border radius (rounded-lg)**. 

This specific radius strikes a balance between the clinical sharpness of a 0px radius and the overly consumer-friendly look of fully rounded pills. It suggests a "modern-industrial" feel. All containers, input fields, and buttons must adhere to this 12px standard to maintain a cohesive structural identity. Small components like tags or checkboxes may use a reduced 4px radius for internal visual harmony.

## Components

### Buttons & CTAs
- **Primary CTA:** Solid Mint (`#00E676`) background with black text. Apply a `0px 0px 15px rgba(0, 230, 118, 0.4)` neon glow. 12px radius.
- **Secondary:** Outline style with 1px stroke. No glow until hovered.

### Form Inputs
- Background: `#1E1E1E`.
- Border: 1px `rgba(255, 255, 255, 0.1)`.
- Focus state: Border changes to Mint with a subtle inner glow.

### Cards & Modules
- Use the 12px radius and the 1px subtle stroke. Header areas within cards should be separated by a thin horizontal line of the same stroke color.

### Data Visualizations
- Charts should use Mint for "up" candles/lines and Coral Red for "down" candles/lines. 
- Grid lines in charts should use `rgba(255, 255, 255, 0.05)` to remain unobtrusive.

### Status Indicators
- Small circular dots for "System Online" or "Live Feed" should utilize the neon glow effect to indicate active processing.