# Week 3: CSS Styling & Design Patterns
## Complete Course Content with Code Examples and Exercises

**Duration**: 40 hours | **Focus**: Master spacing systems, visual hierarchy, and responsive design patterns

---

## Module 3.1: Design Tokens & CSS Variables
### Duration: 8 hours | Level: Beginner

---

## Lesson 3.1.1: What Are Design Tokens?

Design tokens are reusable values that define your design system. Instead of hardcoding colors and spacing, you use variables.

### Benefits of Design Tokens

```
❌ Without tokens:
.button { background: #0077cc; padding: 10px 20px; }
.card { background: #ffffff; padding: 20px; }
.header { background: #0077cc; color: #ffffff; }

Problems:
- If you need to change primary color, update 10 places
- No consistency across components
- Hard to maintain

✅ With tokens:
:root {
    --color-primary: #0077cc;
    --color-white: #ffffff;
    --spacing-md: 10px;
    --spacing-lg: 20px;
}

.button { background: var(--color-primary); padding: var(--spacing-md) var(--spacing-lg); }
.card { background: var(--color-white); padding: var(--spacing-lg); }
.header { background: var(--color-primary); color: var(--color-white); }

Benefits:
- Change color in one place
- Consistency guaranteed
- Easy to maintain
- Can switch themes (dark mode)
```

---

## Lesson 3.1.2: CSS Custom Properties (CSS Variables)

CSS variables allow you to store and reuse values.

### Syntax

```css
/* Define variables */
:root {
    --primary-color: #0077cc;
    --spacing: 8px;
}

/* Use variables */
.button {
    background: var(--primary-color);
    padding: var(--spacing);
}

/* Fallback if variable doesn't exist */
.text {
    color: var(--text-color, #333333);  /* Falls back to #333333 */
}
```

### Scope of Variables

Variables are inherited like regular CSS properties.

```css
/* Global scope */
:root {
    --global-color: blue;
}

/* Local scope */
.container {
    --container-color: red;
}

.container p {
    color: var(--container-color);  /* Uses --container-color */
    background: var(--global-color);  /* Uses global */
}

.sidebar p {
    color: var(--container-color);  /* Doesn't exist here, error */
    background: var(--global-color);  /* Works, global */
}
```

### Responsive Variables

Change variables at different breakpoints:

```css
:root {
    --font-size-h1: 32px;
    --font-size-body: 14px;
}

@media (min-width: 768px) {
    :root {
        --font-size-h1: 48px;
        --font-size-body: 16px;
    }
}

@media (min-width: 1024px) {
    :root {
        --font-size-h1: 64px;
        --font-size-body: 18px;
    }
}

/* Usage stays the same */
h1 { font-size: var(--font-size-h1); }
p { font-size: var(--font-size-body); }
```

### JavaScript Integration

You can change variables from JavaScript:

```javascript
/* Get variable value */
const primaryColor = getComputedStyle(document.documentElement)
    .getPropertyValue('--primary-color');

/* Set variable value */
document.documentElement.style.setProperty('--primary-color', '#FF6B35');

/* Toggle dark mode */
function toggleDarkMode() {
    const isDark = document.body.classList.toggle('dark');
    
    if (isDark) {
        document.documentElement.style.setProperty('--text-color', '#FFFFFF');
        document.documentElement.style.setProperty('--bg-color', '#1A1A1A');
    } else {
        document.documentElement.style.setProperty('--text-color', '#000000');
        document.documentElement.style.setProperty('--bg-color', '#FFFFFF');
    }
}
```

---

## Lesson 3.1.3: Creating a Complete Token System

Let's build a professional design token system.

### Step 1: Color Tokens

```css
:root {
    /* Primary Brand Colors */
    --primary: #0077cc;
    --primary-dark: #0055a4;
    --primary-light: #3399ee;
    
    /* Secondary Colors */
    --secondary: #FF6B35;
    --secondary-dark: #cc5629;
    --secondary-light: #ff8856;
    
    /* Semantic Colors */
    --success: #06A77D;
    --success-light: #d4edd3;
    
    --warning: #F4A261;
    --warning-light: #fde8d4;
    
    --danger: #E63946;
    --danger-light: #f5d5d9;
    
    --info: #0077cc;
    --info-light: #e3f2fd;
    
    /* Neutral Colors */
    --text-primary: #1A1A1A;
    --text-secondary: #555555;
    --text-tertiary: #999999;
    --text-disabled: #CCCCCC;
    
    --bg-primary: #FFFFFF;
    --bg-secondary: #F5F5F5;
    --bg-tertiary: #EEEEEE;
    
    --border-color: #DDDDDD;
    --border-color-light: #F0F0F0;
}
```

### Step 2: Spacing Tokens (8px Grid)

```css
:root {
    /* Spacing Scale (8px base unit) */
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
    --space-2xl: 48px;
    --space-3xl: 64px;
    
    /* Specific use cases */
    --space-gutter: 16px;  /* Padding inside containers */
    --space-gap: 16px;     /* Gap between flex/grid items */
}

/* Usage */
.container {
    padding: var(--space-lg);  /* 24px padding */
    margin-bottom: var(--space-xl);  /* 32px margin */
}

.flex-container {
    display: flex;
    gap: var(--space-md);  /* 16px gap */
}
```

### Step 3: Typography Tokens

```css
:root {
    /* Font Families */
    --font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-heading: 'Playfair Display', serif;
    --font-mono: 'Courier New', monospace;
    
    /* Font Sizes */
    --font-size-xs: 12px;
    --font-size-sm: 14px;
    --font-size-base: 16px;
    --font-size-lg: 18px;
    --font-size-xl: 24px;
    --font-size-2xl: 32px;
    --font-size-3xl: 48px;
    
    /* Font Weights */
    --font-weight-normal: 400;
    --font-weight-medium: 500;
    --font-weight-semibold: 600;
    --font-weight-bold: 700;
    
    /* Line Heights */
    --line-height-tight: 1.2;
    --line-height-normal: 1.5;
    --line-height-relaxed: 1.8;
}
```

### Step 4: Shadow Tokens

```css
:root {
    /* Shadows */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
    --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.15);
    --shadow-2xl: 0 25px 50px rgba(0, 0, 0, 0.25);
    
    /* Shadows for elevation */
    --elevation-1: var(--shadow-sm);
    --elevation-2: var(--shadow-md);
    --elevation-3: var(--shadow-lg);
    --elevation-4: var(--shadow-xl);
}

/* Usage */
.card {
    box-shadow: var(--shadow-lg);
}

.card:hover {
    box-shadow: var(--shadow-xl);
}
```

### Step 5: Border & Radius Tokens

```css
:root {
    /* Border Radius */
    --radius-none: 0;
    --radius-sm: 2px;
    --radius-md: 4px;
    --radius-lg: 8px;
    --radius-xl: 12px;
    --radius-2xl: 16px;
    --radius-full: 9999px;  /* For pill-shaped elements */
    
    /* Border Width */
    --border-width-thin: 1px;
    --border-width-medium: 2px;
    --border-width-thick: 3px;
}

/* Usage */
.button {
    border-radius: var(--radius-md);  /* 4px */
}

.pill-button {
    border-radius: var(--radius-full);  /* Circular */
}

.card {
    border-radius: var(--radius-lg);  /* 8px */
}
```

### Complete Token System Example

```css
/* === COLORS === */
:root {
    /* Brand */
    --primary: #0077cc;
    --primary-dark: #0055a4;
    --primary-light: #3399ee;
    --secondary: #FF6B35;
    
    /* Semantic */
    --success: #06A77D;
    --success-light: #d4edd3;
    --warning: #F4A261;
    --warning-light: #fde8d4;
    --danger: #E63946;
    --danger-light: #f5d5d9;
    
    /* Neutral */
    --text-primary: #1A1A1A;
    --text-secondary: #555555;
    --bg-primary: #FFFFFF;
    --bg-secondary: #F5F5F5;
    --border-color: #DDDDDD;
}

/* === SPACING === */
:root {
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
}

/* === TYPOGRAPHY === */
:root {
    --font-primary: 'Inter', sans-serif;
    --font-heading: 'Playfair Display', serif;
    
    --font-size-sm: 14px;
    --font-size-base: 16px;
    --font-size-lg: 18px;
    --font-size-xl: 24px;
    --font-size-2xl: 32px;
    
    --font-weight-normal: 400;
    --font-weight-bold: 700;
    
    --line-height-tight: 1.2;
    --line-height-normal: 1.5;
}

/* === SHADOWS === */
:root {
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
}

/* === BORDER & RADIUS === */
:root {
    --radius-md: 4px;
    --radius-lg: 8px;
    --radius-full: 9999px;
}
```

---

## Lesson 3.1.4: Dark Mode with Tokens

Implementing dark mode becomes trivial with tokens:

```css
/* Light Mode (default) */
:root {
    --text-primary: #1A1A1A;
    --text-secondary: #555555;
    --bg-primary: #FFFFFF;
    --bg-secondary: #F5F5F5;
    --border-color: #DDDDDD;
}

/* Dark Mode */
@media (prefers-color-scheme: dark) {
    :root {
        --text-primary: #FFFFFF;
        --text-secondary: #CCCCCC;
        --bg-primary: #1A1A1A;
        --bg-secondary: #2D2D2D;
        --border-color: #404040;
    }
}

/* Or with class-based toggle */
body.dark-mode {
    --text-primary: #FFFFFF;
    --text-secondary: #CCCCCC;
    --bg-primary: #1A1A1A;
    --bg-secondary: #2D2D2D;
    --border-color: #404040;
}

/* Usage stays the same everywhere */
body {
    color: var(--text-primary);
    background: var(--bg-primary);
}

p {
    color: var(--text-secondary);
}
```

### JavaScript for Dark Mode Toggle

```javascript
// Toggle dark mode
function toggleDarkMode() {
    const body = document.body;
    const isDark = body.classList.toggle('dark-mode');
    
    // Save preference
    localStorage.setItem('darkMode', isDark);
}

// Load saved preference
function loadDarkMode() {
    const isDark = localStorage.getItem('darkMode') === 'true';
    if (isDark) {
        document.body.classList.add('dark-mode');
    }
}

// Run on page load
loadDarkMode();

// Toggle on button click
document.getElementById('dark-mode-toggle').addEventListener('click', toggleDarkMode);
```

---

## Summary: Module 3.1

You've learned:
- ✅ What design tokens are
- ✅ CSS custom properties syntax
- ✅ Creating complete token systems
- ✅ Scope and inheritance
- ✅ Responsive tokens
- ✅ Dark mode implementation
- ✅ JavaScript integration

**Key Takeaway**: Design tokens create consistency and make maintenance trivial. Always use them in professional projects.

---

## Module 3.2: Spacing & Visual Hierarchy
### Duration: 8 hours | Level: Beginner

---

## Lesson 3.2.1: The 8px Grid System

Professional design uses consistent spacing based on a base unit (usually 8px).

### Why 8px?

```
- Divisible by 2, 4, 6, 8 (many options)
- Creates rhythm and harmony
- Standard in most design systems (Google Material, iOS, etc.)
- Easy to scale (8, 16, 24, 32, 48, 64...)
```

### Building Your Spacing Scale

```css
/* Base unit: 8px */
:root {
    --space-1: 8px;      /* 1x */
    --space-2: 16px;     /* 2x */
    --space-3: 24px;     /* 3x */
    --space-4: 32px;     /* 4x */
    --space-5: 40px;     /* 5x */
    --space-6: 48px;     /* 6x */
    --space-8: 64px;     /* 8x */
}

/* Alternative naming */
:root {
    --space-xs: 8px;
    --space-sm: 16px;
    --space-md: 24px;
    --space-lg: 32px;
    --space-xl: 48px;
    --space-2xl: 64px;
}
```

### Applying Spacing

```css
/* Padding inside containers */
.container {
    padding: var(--space-3);  /* 24px all sides */
}

/* Margins between elements */
.section {
    margin-bottom: var(--space-4);  /* 32px space below */
}

/* Gap in flexbox/grid */
.grid {
    display: grid;
    gap: var(--space-2);  /* 16px between items */
}

/* Button padding */
.button {
    padding: var(--space-1) var(--space-2);  /* 8px 16px (top/bottom left/right) */
}
```

---

## Lesson 3.2.2: Vertical Rhythm

Vertical rhythm creates harmony in typography.

### Line Height and Spacing

```css
/* Base font size: 16px */
html {
    font-size: 16px;
}

/* Line height: 1.5 = 24px */
body {
    font-size: 16px;
    line-height: 1.5;
    /* Line height = 16 * 1.5 = 24px */
}

/* All margins/padding should be multiples of 24px */
h1 {
    font-size: 32px;
    line-height: 1.2;
    margin-top: 24px;  /* 1 line */
    margin-bottom: 24px;  /* 1 line */
}

p {
    font-size: 16px;
    line-height: 1.5;
    margin-bottom: 24px;  /* 1 line */
}

/* 24px is our vertical rhythm unit */
```

### Vertical Rhythm Formula

```
Vertical Rhythm Unit = Font Size × Line Height

Example:
- Base font: 16px
- Line height: 1.5
- Rhythm unit: 16 × 1.5 = 24px

All margins/padding should be:
- 24px (1x)
- 48px (2x)
- 72px (3x)
```

### Practical Example

```css
/* Define vertical rhythm */
:root {
    --vr-unit: 24px;  /* 16px × 1.5 */
}

body {
    font-size: 16px;
    line-height: 1.5;
}

h1 {
    margin-bottom: var(--vr-unit);  /* 24px */
}

h2 {
    margin-top: calc(var(--vr-unit) * 2);  /* 48px */
    margin-bottom: var(--vr-unit);  /* 24px */
}

p {
    margin-bottom: var(--vr-unit);  /* 24px */
}

/* Visual result: elements feel connected and rhythmic */
```

---

## Lesson 3.2.3: White Space as Design

White space (negative space) is crucial for good design.

### Benefits of White Space

```
✅ Improves readability
✅ Creates focus
✅ Reduces cognitive load
✅ Makes premium/luxury feel
✅ Improves visual hierarchy
```

### White Space Types

**Macro White Space**: Large gaps between major sections
```css
.section {
    margin-bottom: 64px;  /* Large gap between sections */
}
```

**Micro White Space**: Small gaps within components
```css
.button {
    padding: 8px 16px;  /* Small internal spacing */
}
```

**Passive White Space**: Empty areas that don't have content
```css
.card {
    padding: 24px;  /* Passive white space around content */
}
```

### Example: Landing Page Spacing

```css
/* Macro spacing between sections */
.hero {
    padding: 64px 0;  /* Large top/bottom padding */
    margin-bottom: 64px;  /* Large gap to next section */
}

.features {
    padding: 64px 0;
    margin-bottom: 64px;
}

/* Micro spacing within section */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 32px;  /* Gap between cards */
}

.feature-card {
    padding: 24px;  /* Padding inside card */
}

/* Typography spacing */
h2 {
    margin-bottom: 24px;  /* Space below heading */
}

p {
    margin-bottom: 16px;  /* Space between paragraphs */
}
```

---

## Lesson 3.2.4: Visual Hierarchy

Make important content stand out using spacing, size, and color.

### Hierarchy Through Size

```css
/* Larger = more important */
h1 {
    font-size: 48px;  /* Largest, most important */
}

h2 {
    font-size: 32px;
}

body {
    font-size: 16px;
}

.caption {
    font-size: 12px;  /* Smallest, least important */
}
```

### Hierarchy Through Color

```css
:root {
    --primary: #0077cc;  /* Most important */
    --secondary: #555555;  /* Less important */
    --tertiary: #999999;  /* Even less important */
}

.headline {
    color: var(--primary);  /* Draw attention */
}

.body {
    color: var(--secondary);  /* Normal reading */
}

.caption {
    color: var(--tertiary);  /* Least important */
}
```

### Hierarchy Through Spacing

```css
/* More space = more important */
.important-section {
    margin-bottom: 64px;  /* Lots of space after */
}

.less-important {
    margin-bottom: 24px;  /* Less space */
}
```

### Hierarchy Through Weight

```css
h1 {
    font-weight: 700;  /* Bold = important */
    font-size: 48px;
    margin-bottom: 24px;
    color: var(--primary);
}

p {
    font-weight: 400;  /* Normal = less important */
    font-size: 16px;
    color: var(--secondary);
}

.label {
    font-weight: 500;  /* Semi-bold = moderate importance */
    font-size: 14px;
    color: var(--tertiary);
}
```

---

## Summary: Module 3.2

You've learned:
- ✅ 8px grid system
- ✅ Vertical rhythm
- ✅ White space as design element
- ✅ Visual hierarchy through size, color, spacing, weight

**Key Takeaway**: Consistent spacing and hierarchy create beautiful, professional designs.

---

## Module 3.3: Shadows, Borders & Depth
### Duration: 8 hours | Level: Intermediate

---

## Lesson 3.3.1: Shadow Systems

Shadows create depth and elevation in flat design.

### Shadow Anatomy

```css
/* box-shadow: horizontal vertical blur spread color opacity */
box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
```

Where:
- `0` = no horizontal offset
- `4px` = 4px vertical offset (down)
- `6px` = 6px blur radius (softness)
- `rgba(0, 0, 0, 0.1)` = black, 10% opacity

### Building a Shadow System

```css
:root {
    /* Subtle shadows */
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    
    /* Small shadows */
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    
    /* Medium shadows */
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    
    /* Large shadows */
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    
    /* Extra large shadows */
    --shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

/* Usage */
.card {
    box-shadow: var(--shadow-md);  /* Default state */
}

.card:hover {
    box-shadow: var(--shadow-lg);  /* Hover elevation */
}

.modal {
    box-shadow: var(--shadow-2xl);  /* Maximum elevation */
}
```

### Neumorphism Shadows (Soft UI)

Neumorphism uses soft, subtle shadows that blend with background.

```css
/* Neumorphic shadow system */
:root {
    /* Light source from top-left */
    --shadow-neomorphic-inset: inset 2px 2px 5px rgba(255, 255, 255, 0.6),
                                inset -2px -2px 5px rgba(0, 0, 0, 0.2);
    
    --shadow-neomorphic-outset: 2px 2px 5px rgba(0, 0, 0, 0.2),
                                 -2px -2px 5px rgba(255, 255, 255, 0.6);
}

.neumorphic-button {
    background: #e0e5ec;
    box-shadow: var(--shadow-neomorphic-outset);
    border: none;
    border-radius: 8px;
    padding: 16px 32px;
}

.neumorphic-button:active {
    box-shadow: var(--shadow-neomorphic-inset);
}
```

### Layered Shadows (Realistic Depth)

Use multiple shadows for more realistic depth:

```css
/* Build up layers for more realistic shadows */
.elevated-card {
    box-shadow: 
        0 1px 3px rgba(0, 0, 0, 0.12),
        0 1px 2px rgba(0, 0, 0, 0.24);
}

.more-elevated {
    box-shadow: 
        0 3px 6px rgba(0, 0, 0, 0.15),
        0 2px 4px rgba(0, 0, 0, 0.12);
}

.very-elevated {
    box-shadow: 
        0 10px 20px rgba(0, 0, 0, 0.15),
        0 3px 6px rgba(0, 0, 0, 0.10);
}
```

### Drop Shadow on Images

```css
/* Subtle shadow on images */
img {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    border-radius: 4px;
}

/* Larger shadow on featured images */
.featured-image {
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    border-radius: 8px;
}
```

---

## Lesson 3.3.2: Border Styles

Borders define boundaries and add visual interest.

### Border Styles

```css
/* Different border styles */
.solid-border {
    border: 1px solid #ccc;
}

.dashed-border {
    border: 1px dashed #ccc;
}

.dotted-border {
    border: 1px dotted #ccc;
}

.double-border {
    border: 3px double #ccc;
}

.groove-border {
    border: 3px groove #ccc;
}

.ridge-border {
    border: 3px ridge #ccc;
}

.inset-border {
    border: 3px inset #ccc;
}

.outset-border {
    border: 3px outset #ccc;
}
```

### Accent Borders (Semantic)

```css
/* Use colored left border for semantic meaning */
.success {
    border-left: 4px solid var(--success);
    padding-left: 12px;
}

.warning {
    border-left: 4px solid var(--warning);
    padding-left: 12px;
}

.error {
    border-left: 4px solid var(--danger);
    padding-left: 12px;
}

.info {
    border-left: 4px solid var(--info);
    padding-left: 12px;
}
```

### Border Radius for Shapes

```css
/* Rounded corners */
.slightly-rounded {
    border-radius: 2px;
}

.rounded {
    border-radius: 4px;
}

.more-rounded {
    border-radius: 8px;
}

.very-rounded {
    border-radius: 16px;
}

/* Pill shape */
.pill {
    border-radius: 9999px;  /* Very large value = pill shape */
}

/* Circle */
.circle {
    width: 100px;
    height: 100px;
    border-radius: 50%;  /* 50% = perfect circle */
}

/* Individual corners */
.top-left-rounded {
    border-radius: 8px 0 0 0;
}

.bottom-rounded {
    border-radius: 0 0 8px 8px;
}
```

---

## Lesson 3.3.3: Combining Shadows, Borders & Radius

Let's build professional components with all three:

```css
/* Professional Card Component */
.card {
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    box-shadow: var(--shadow-md);
    padding: 24px;
    
    transition: all 200ms ease-out;
}

.card:hover {
    border-color: var(--primary);
    box-shadow: var(--shadow-lg);
    transform: translateY(-4px);  /* Lift on hover */
}

/* Alert Component with Left Accent */
.alert {
    border-left: 4px solid var(--info);
    border-radius: 4px;
    background: var(--info-light);
    padding: 16px;
    margin-bottom: 16px;
}

.alert.success {
    border-left-color: var(--success);
    background: var(--success-light);
}

.alert.warning {
    border-left-color: var(--warning);
    background: var(--warning-light);
}

.alert.error {
    border-left-color: var(--danger);
    background: var(--danger-light);
}

/* Button with Subtle Shadow */
.button {
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    
    cursor: pointer;
    transition: all 200ms ease-out;
}

.button:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
}

.button:active {
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    transform: translateY(0);
}
```

---

## Summary: Module 3.3

You've learned:
- ✅ Shadow systems and elevation
- ✅ Neumorphism shadows
- ✅ Border styles and semantic meaning
- ✅ Border radius for shapes
- ✅ Combining for professional components

**Key Takeaway**: Shadows create depth, borders define boundaries, radius softens edges.

---

## Module 3.4: Responsive Design Mastery
### Duration: 16 hours | Level: Intermediate

---

## Lesson 3.4.1: Mobile-First Approach

Always design and code for mobile first, then enhance for larger screens.

### Why Mobile-First?

```
✅ Mobile is default (easiest)
✅ Forces focus on essentials
✅ Progressive enhancement (add features, not remove)
✅ Better performance
✅ Easier CSS (simpler rules, fewer overrides)
```

### Mobile-First Example

```css
/* MOBILE FIRST - Start here */
body {
    font-size: 14px;
    margin: 0;
}

.container {
    width: 100%;  /* Full width */
    padding: 16px;
}

.grid {
    display: grid;
    grid-template-columns: 1fr;  /* Single column */
    gap: 16px;
}

/* ENHANCE FOR TABLET */
@media (min-width: 768px) {
    body {
        font-size: 16px;
    }
    
    .grid {
        grid-template-columns: repeat(2, 1fr);  /* 2 columns */
    }
}

/* ENHANCE FOR DESKTOP */
@media (min-width: 1024px) {
    body {
        font-size: 18px;
    }
    
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 32px;
    }
    
    .grid {
        grid-template-columns: repeat(3, 1fr);  /* 3 columns */
    }
}
```

### Common Breakpoints

```css
/* Mobile-first breakpoints */
/* Mobile: 0px - 479px (no media query needed) */

/* Tablet: 480px - 767px */
@media (min-width: 480px) { }

/* Small Tablet: 768px - 1023px */
@media (min-width: 768px) { }

/* Desktop: 1024px - 1439px */
@media (min-width: 1024px) { }

/* Large Desktop: 1440px+ */
@media (min-width: 1440px) { }

/* Extra Large: 1920px+ */
@media (min-width: 1920px) { }
```

---

## Lesson 3.4.2: Responsive Typography

Text should scale smoothly across devices.

### Fixed Breakpoint Approach

```css
/* Mobile */
h1 {
    font-size: 24px;
}

body {
    font-size: 14px;
}

/* Tablet */
@media (min-width: 768px) {
    h1 {
        font-size: 32px;
    }
    
    body {
        font-size: 16px;
    }
}

/* Desktop */
@media (min-width: 1024px) {
    h1 {
        font-size: 48px;
    }
    
    body {
        font-size: 18px;
    }
}
```

### Fluid Typography with clamp()

Modern and better approach using `clamp()`:

```css
/* clamp(min, preferred, max) */

/* Scale h1 from 24px (mobile) to 48px (desktop) */
h1 {
    font-size: clamp(24px, 6vw, 48px);
    /* Minimum 24px
       Preferred: 6% of viewport width
       Maximum 48px */
}

/* Scale body from 14px to 18px */
body {
    font-size: clamp(14px, 2vw, 18px);
}

/* Scale padding from 16px to 48px */
.container {
    padding: clamp(16px, 8vw, 48px);
}

/* All scale smoothly without media queries */
```

**Why clamp() is better**:
- Smooth scaling (no jump at breakpoints)
- Fewer media queries needed
- Fewer code lines
- Responsive without breakpoints

---

## Lesson 3.4.3: Responsive Layouts

Different layouts for different screen sizes.

### Flex Direction Changes

```css
/* Mobile: Stack vertically */
.flex-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

/* Desktop: Horizontal layout */
@media (min-width: 1024px) {
    .flex-container {
        flex-direction: row;
        gap: 32px;
    }
}
```

### Grid Column Changes

```css
/* Mobile: 1 column */
.grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
}

/* Tablet: 2 columns */
@media (min-width: 768px) {
    .grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Desktop: 3 columns */
@media (min-width: 1024px) {
    .grid {
        grid-template-columns: repeat(3, 1fr);
        gap: 32px;
    }
}
```

### Container Query Approach (Modern)

Container queries size components based on their container, not viewport:

```css
/* Container is the parent */
.container {
    container-type: inline-size;
    container-name: card-container;
}

/* Adapt based on container size */
@container (min-width: 300px) {
    .card {
        display: flex;
        flex-direction: column;
    }
}

@container (min-width: 500px) {
    .card {
        display: flex;
        flex-direction: row;
    }
    
    .card-image {
        width: 200px;
    }
}
```

---

## Lesson 3.4.4: Responsive Images

Images should scale appropriately.

### Max-Width Images

```css
/* Images never bigger than container */
img {
    max-width: 100%;
    height: auto;  /* Maintain aspect ratio */
    display: block;  /* Avoid inline spacing */
}
```

### Responsive Picture Element

```html
<!-- Serve different images for different screen sizes -->
<picture>
    <!-- Mobile: smaller image -->
    <source media="(max-width: 480px)" srcset="image-mobile.jpg">
    
    <!-- Tablet: medium image -->
    <source media="(max-width: 1024px)" srcset="image-tablet.jpg">
    
    <!-- Desktop: full-size image -->
    <img src="image-desktop.jpg" alt="...">
</picture>
```

### Aspect Ratio Preservation

```css
/* Modern: aspect-ratio property */
.image-container {
    aspect-ratio: 16 / 9;  /* 16:9 ratio */
    overflow: hidden;
}

.image-container img {
    width: 100%;
    height: 100%;
    object-fit: cover;  /* Cover without stretching */
}

/* Older browsers: padding-bottom trick */
.image-container-legacy {
    position: relative;
    width: 100%;
    padding-bottom: 56.25%;  /* 9/16 = 0.5625 = 56.25% */
    overflow: hidden;
}

.image-container-legacy img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
}
```

---

## Lesson 3.4.5: Touch-Friendly Design

Optimize for touch on mobile devices.

### Touch Target Sizes

```css
/* Minimum 44×44 pixels for touch targets */
.button {
    min-width: 44px;
    min-height: 44px;
    padding: 12px 16px;  /* At least 44px tall */
}

.link {
    padding: 12px 8px;  /* Make clickable area larger */
    min-height: 44px;
    display: inline-block;
}

/* Enough spacing between touch targets */
.button + .button {
    margin-left: 16px;  /* At least 16px gap */
}
```

### Tap-Friendly Spacing

```css
/* More spacing on mobile for touch */
.mobile-menu a {
    display: block;
    padding: 16px;  /* Large touch area */
}

/* Smaller spacing on desktop */
@media (min-width: 1024px) {
    .desktop-menu a {
        padding: 8px 12px;  /* Smaller for mouse */
    }
}
```

### Hover vs Touch

```css
/* Hover effects only work with mouse, not touch */
.card {
    transition: all 200ms ease-out;
}

/* Works on both hover and touch */
.card:hover,
.card:focus-within {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}

/* Mobile-friendly: use focus instead of hover alone */
.button {
    padding: 12px 24px;
}

.button:focus {
    outline: 2px solid var(--primary);
    outline-offset: 2px;
}
```

---

## Lesson 3.4.6: Responsive Navigation

Navigation changes significantly between mobile and desktop.

### Hamburger Menu Example

```html
<nav class="navbar">
    <div class="navbar-container">
        <a href="/" class="navbar-logo">Logo</a>
        
        <!-- Hamburger button (mobile only) -->
        <button class="hamburger" id="hamburger-btn">
            <span></span>
            <span></span>
            <span></span>
        </button>
        
        <!-- Navigation menu -->
        <ul class="nav-menu" id="nav-menu">
            <li><a href="/">Home</a></li>
            <li><a href="/about">About</a></li>
            <li><a href="/services">Services</a></li>
            <li><a href="/contact">Contact</a></li>
        </ul>
    </div>
</nav>
```

```css
/* Mobile First */
.navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    background: white;
    border-bottom: 1px solid var(--border-color);
}

.navbar-logo {
    font-size: 24px;
    font-weight: bold;
    color: var(--primary);
    text-decoration: none;
}

/* Hamburger button visible on mobile */
.hamburger {
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: none;
    border: none;
    cursor: pointer;
}

.hamburger span {
    display: block;
    width: 25px;
    height: 3px;
    background: var(--text-primary);
    border-radius: 2px;
    transition: all 200ms ease-out;
}

/* Navigation menu hidden on mobile */
.nav-menu {
    display: none;
    position: absolute;
    top: 60px;
    left: 0;
    width: 100%;
    background: white;
    flex-direction: column;
    list-style: none;
    padding: 16px;
    border-bottom: 1px solid var(--border-color);
}

/* Show menu when active */
.nav-menu.active {
    display: flex;
}

.nav-menu a {
    padding: 12px;
    color: var(--text-primary);
    text-decoration: none;
    transition: color 200ms;
}

.nav-menu a:hover {
    color: var(--primary);
}

/* Desktop */
@media (min-width: 1024px) {
    .navbar {
        justify-content: space-between;
        gap: 48px;
    }
    
    /* Hide hamburger on desktop */
    .hamburger {
        display: none;
    }
    
    /* Show menu on desktop */
    .nav-menu {
        display: flex !important;
        position: static;
        flex-direction: row;
        width: auto;
        background: none;
        border: none;
        padding: 0;
        gap: 32px;
    }
    
    .nav-menu a {
        padding: 0;
    }
}
```

```javascript
// Toggle mobile menu
const hamburgerBtn = document.getElementById('hamburger-btn');
const navMenu = document.getElementById('nav-menu');

hamburgerBtn.addEventListener('click', () => {
    navMenu.classList.toggle('active');
});

// Close menu when link clicked
navMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
        navMenu.classList.remove('active');
    });
});
```

---

## Summary: Module 3.4

You've learned:
- ✅ Mobile-first methodology
- ✅ Media queries and breakpoints
- ✅ Responsive typography with clamp()
- ✅ Responsive layouts (flex, grid)
- ✅ Responsive images
- ✅ Touch-friendly design
- ✅ Responsive navigation patterns

**Key Takeaway**: Start mobile, enhance for larger screens. Use clamp() for smooth scaling.

---

## Summary: Week 3

You've learned:
- ✅ Design tokens and CSS variables
- ✅ Spacing systems (8px grid)
- ✅ Vertical rhythm
- ✅ White space design
- ✅ Visual hierarchy
- ✅ Shadow systems
- ✅ Border and radius
- ✅ Mobile-first responsive design
- ✅ Responsive typography
- ✅ Touch-friendly design

**Key Deliverables**:
1. Complete design token system
2. Responsive component library
3. Landing page with responsive design
4. Dark mode implementation

---

## Week 3 Practical Project: Build a Responsive Component Library

### Project Requirements

Create a responsive component library with:

1. **Buttons** (primary, secondary, sizes, disabled)
2. **Cards** (with images, with content, elevated)
3. **Forms** (inputs, textareas, labels, validation)
4. **Navigation** (responsive navbar with hamburger)
5. **Alerts** (success, warning, error, info)
6. **Badges** (different colors and sizes)

### All with:

- ✅ Design tokens (colors, spacing, typography)
- ✅ Responsive design (mobile-first)
- ✅ Dark mode support
- ✅ Touch-friendly (44px minimum targets)
- ✅ Proper shadows and borders
- ✅ Smooth transitions

### Deliverables

```
week-3-project/
├── index.html (component showcase)
├── styles.css (all components)
├── styles-dark.css (dark mode variables)
├── script.js (interactivity, dark mode toggle)
├── components/
│   ├── buttons.html
│   ├── cards.html
│   ├── forms.html
│   ├── navbar.html
│   └── alerts.html
└── README.md (documentation)
```

---

**End of Week 3 Content**

Next: Week 4 - Tailwind CSS (continuing with detailed content for weeks 4-8...)
