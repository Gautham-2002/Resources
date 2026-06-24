# Week 1: Design Fundamentals & Figma Mastery
## Complete Course Content with Code Examples and Exercises

**Duration**: 40 hours | **Focus**: Understanding design thinking, extracting specs from Figma

---

## Module 1.1: Color Theory & Psychology
### Duration: 10 hours | Level: Beginner

---

## Lesson 1.1.1: Understanding Color Fundamentals

### What is Color?

Color is light reflected from objects. In web design, we work with **RGB (Red, Green, Blue)** color model because screens emit light.

### Color Models You Need to Know

#### 1. **RGB (Red, Green, Blue)**
Values from 0-255 for each channel. Pure red = rgb(255, 0, 0)

```css
/* RGB Format */
.element {
    color: rgb(255, 0, 0);           /* Red */
    background: rgb(0, 128, 255);    /* Blue */
    border: 1px solid rgb(100, 100, 100);  /* Gray */
}
```

#### 2. **Hexadecimal (Hex)**
Shorthand for RGB using base-16. #RRGGBB where each pair is 00-FF

```css
/* Hex Format */
.element {
    color: #FF0000;          /* Red (same as rgb(255,0,0)) */
    background: #0080FF;     /* Blue */
    border: 1px solid #646464;  /* Gray */
}

/* Short Hex (when both digits are same) */
.element {
    color: #F00;    /* Red (same as #FF0000) */
    background: #0EF;  /* Cyan (same as #00EEFF) */
}
```

#### 3. **HSL (Hue, Saturation, Lightness)**
More intuitive for humans. Hue (0-360°), Saturation (0-100%), Lightness (0-100%)

```css
/* HSL Format - Best for creating variations */
.element {
    color: hsl(0, 100%, 50%);        /* Red */
    background: hsl(200, 100%, 50%); /* Blue */
    border: 1px solid hsl(0, 0%, 39%);  /* Gray */
}

/* Easy to create lighter/darker versions */
.button {
    background: hsl(200, 80%, 45%);    /* Base blue */
}

.button:hover {
    background: hsl(200, 80%, 35%);    /* 10% darker */
}

.button:active {
    background: hsl(200, 80%, 25%);    /* 20% darker */
}
```

**Why HSL is great for design**:
- Change only the Lightness for dark/light variants
- Change only the Saturation for muted versions
- Hue stays consistent across variations

#### 4. **OKLCH (OKLab Color Space)**
Modern format, better color perception. Better than HSL for matching human vision.

```css
/* OKLCH Format - Most modern and accurate */
.element {
    color: oklch(60% 0.2 30);        /* Hue 30°, 60% lightness, 0.2 chroma */
}

/* Similar to HSL but perceptually more accurate */
.button {
    background: oklch(50% 0.15 250);  /* Blue-ish */
}

.button:hover {
    background: oklch(40% 0.15 250);  /* Darker version */
}
```

### Color Conversion Cheat Sheet

```
Red:
  RGB: rgb(255, 0, 0)
  Hex: #FF0000 or #F00
  HSL: hsl(0, 100%, 50%)

Green:
  RGB: rgb(0, 128, 0)
  Hex: #008000
  HSL: hsl(120, 100%, 25%)

Blue:
  RGB: rgb(0, 0, 255)
  Hex: #0000FF or #00F
  HSL: hsl(240, 100%, 50%)

Gray:
  RGB: rgb(128, 128, 128)
  Hex: #808080
  HSL: hsl(0, 0%, 50%)
```

### Practice Exercise 1.1.1.1

Convert these colors between formats:

1. Red (#FF0000) → HSL
2. hsl(120, 100%, 50%) → Hex
3. rgb(100, 150, 200) → Hex

**Solutions**:
1. hsl(0, 100%, 50%)
2. #00FF00
3. #6496C8

---

## Lesson 1.1.2: The Color Wheel & Harmony

### Understanding the Color Wheel

The color wheel organizes colors in a circle based on their relationships.

```
                  Yellow (60°)
                      |
    Yellow-Green       |       Yellow-Orange
            \          |          /
             \         |         /
    Green -------- Primary Colors -------- Orange
    (120°)  \       (0°,120°,240°)  /       (30°)
             \                     /
              Red-Green    Red-Orange
                  |
                Red (0°)
```

### Color Harmony Schemes

These are proven combinations that look good together:

#### 1. **Complementary Colors** (Opposite on wheel)
Colors 180° apart. High contrast, vibrant.

```css
/* Example: Blue & Orange */
:root {
    --primary: hsl(240, 100%, 50%);      /* Blue */
    --complement: hsl(30, 100%, 50%);    /* Orange */
}

.header {
    background: var(--primary);
}

.accent {
    background: var(--complement);
}
```

**When to use**: Call-to-action buttons, important alerts, emphasis elements

#### 2. **Analogous Colors** (Adjacent on wheel)
Colors 30-60° apart. Harmonious, pleasing to eye.

```css
/* Example: Blue, Blue-Green, Green */
:root {
    --color1: hsl(240, 100%, 50%);       /* Blue */
    --color2: hsl(180, 100%, 50%);       /* Cyan (60° apart) */
    --color3: hsl(120, 100%, 50%);       /* Green (120° apart) */
}

.card-1 { background: var(--color1); }
.card-2 { background: var(--color2); }
.card-3 { background: var(--color3); }
```

**When to use**: Unified designs, nature themes, calm interfaces

#### 3. **Triadic Colors** (120° apart)
Three colors evenly spaced. Balanced, vibrant.

```css
/* Example: Red, Green, Blue (primary colors) */
:root {
    --primary: hsl(0, 100%, 50%);        /* Red (0°) */
    --secondary: hsl(120, 100%, 50%);    /* Green (120°) */
    --tertiary: hsl(240, 100%, 50%);     /* Blue (240°) */
}

.brand-primary { color: var(--primary); }
.brand-secondary { color: var(--secondary); }
.brand-tertiary { color: var(--tertiary); }
```

**When to use**: Playful designs, diverse content, dynamic interfaces

#### 4. **Tetradic (Split-Complementary)** (90° apart)
Four colors in a rectangle. Rich, balanced.

```css
/* Example: Red, Yellow, Green, Blue */
:root {
    --color1: hsl(0, 100%, 50%);         /* Red (0°) */
    --color2: hsl(60, 100%, 50%);        /* Yellow (60°) */
    --color3: hsl(120, 100%, 50%);       /* Green (120°) */
    --color4: hsl(240, 100%, 50%);       /* Blue (240°) */
}
```

**When to use**: Complex dashboards, diverse categories

---

## Lesson 1.1.3: Color Psychology

Colors trigger emotions. Understanding this helps design better UX.

### Color Psychology Reference

| Color | Emotion | Use Case | Example |
|-------|---------|----------|---------|
| **Red** | Urgency, passion, energy | Warnings, sales, CTAs | Error messages, "Buy Now" buttons |
| **Orange** | Optimistic, friendly | Call-to-action, creative | Social sharing buttons |
| **Yellow** | Happiness, caution | Warnings (light yellow) | Important notices, highlights |
| **Green** | Growth, success, calm | Confirmations, go actions | "Approved" badges, success messages |
| **Blue** | Trust, calm, stability | Corporate, tech, finance | Bank websites, productivity tools |
| **Purple** | Creativity, luxury | Premium products, tech | Creative services, premium apps |
| **Pink** | Playfulness, warmth | Beauty, youth | Fashion, lifestyle brands |
| **Black** | Power, sophistication | Premium, drama | High-end brands, dark modes |
| **White** | Clean, simplicity, space | Backgrounds, trust | Minimalist design, SaaS |
| **Gray** | Neutral, balance, sadness | Secondary text, disabled states | Placeholder text, inactive buttons |

### Practical Example: E-commerce Website

```css
:root {
    /* Colors based on psychology */
    
    /* Primary: Blue for trust (financial transactions) */
    --primary: hsl(210, 100%, 50%);
    
    /* Accent: Orange for CTAs (draw attention) */
    --accent: hsl(30, 100%, 50%);
    
    /* Success: Green (humans expect green for success) */
    --success: hsl(120, 100%, 40%);
    
    /* Danger: Red (humans expect red for danger) */
    --danger: hsl(0, 100%, 50%);
    
    /* Warning: Yellow (humans expect yellow for warning) */
    --warning: hsl(45, 100%, 50%);
    
    /* Text: Dark gray for readability */
    --text-primary: hsl(0, 0%, 20%);
    --text-secondary: hsl(0, 0%, 50%);
    
    /* Background: White for cleanliness */
    --bg-primary: hsl(0, 0%, 100%);
    --bg-secondary: hsl(0, 0%, 95%);
}

/* Apply psychology */
.button-primary {
    background: var(--primary);  /* Blue = trust */
    color: white;
}

.button-cta {
    background: var(--accent);   /* Orange = action */
    color: white;
}

.success-message {
    background: var(--success);  /* Green = approved */
    color: white;
}

.error-message {
    background: var(--danger);   /* Red = danger */
    color: white;
}

.warning-message {
    background: var(--warning);  /* Yellow = caution */
    color: var(--text-primary);  /* Dark text for contrast */
}
```

---

## Lesson 1.1.4: The 60-30-10 Rule

**The 60-30-10 rule is a professional design principle** that ensures balanced, pleasing color schemes.

### The Rule

- **60%**: Dominant color (usually neutral or main brand color)
- **30%**: Secondary color (supporting color)
- **10%**: Accent color (highlights, CTAs)

This ratio creates visual harmony without being boring.

### Practical Implementation

```css
:root {
    /* 60% - Dominant (neutral, safe) */
    --dominant: hsl(0, 0%, 95%);         /* Light gray background */
    
    /* 30% - Secondary (supporting) */
    --secondary: hsl(210, 70%, 50%);     /* Blue for content */
    
    /* 10% - Accent (highlights) */
    --accent: hsl(30, 100%, 50%);        /* Orange for CTAs */
}

/* 60% - Dominant Color */
body {
    background: var(--dominant);
    color: hsl(0, 0%, 20%);  /* Dark text on light background */
}

/* 30% - Secondary Color */
.header {
    background: var(--secondary);
    color: white;
}

.section-title {
    color: var(--secondary);
}

/* 10% - Accent Color */
.button-primary {
    background: var(--accent);
    color: white;
}

.link {
    color: var(--accent);
}

.badge {
    background: var(--accent);
    color: white;
}
```

### Visual Example

```
┌─────────────────────────────────────────┐
│ WEBSITE LAYOUT SHOWING 60-30-10 RULE    │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │  HEADER (Secondary - 30%)           │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │                                     │ │
│ │  MAIN CONTENT (Dominant - 60%)      │ │
│ │  Light gray background              │ │
│ │                                     │ │
│ │  Title text in secondary color      │ │
│ │  Paragraph text in dark gray        │ │
│ │                                     │ │
│ │  ┌────────────────────────────────┐ │ │
│ │  │ [CTA Button - Accent - 10%]    │ │ │
│ │  └────────────────────────────────┘ │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## Lesson 1.1.5: Creating a Color Palette

Now let's create a complete, professional color palette from scratch.

### Step 1: Choose Your Dominant Color

This should match your brand or the feeling you want. Usually a neutral.

```css
/* For a tech startup - cool, trustworthy */
:root {
    --dominant: hsl(0, 0%, 97%);  /* Almost white, very clean */
}
```

### Step 2: Choose Your Primary Brand Color (30%)

Complementary or analogous to dominant.

```css
:root {
    --dominant: hsl(0, 0%, 97%);
    
    /* Primary brand - Blue for tech */
    --primary: hsl(210, 80%, 45%);
    
    /* Create variations for hover/active states */
    --primary-dark: hsl(210, 80%, 35%);
    --primary-light: hsl(210, 80%, 55%);
}
```

### Step 3: Choose Your Accent Color (10%)

Complementary to primary.

```css
:root {
    --dominant: hsl(0, 0%, 97%);
    --primary: hsl(210, 80%, 45%);
    --primary-dark: hsl(210, 80%, 35%);
    --primary-light: hsl(210, 80%, 55%);
    
    /* Accent - opposite of blue on color wheel */
    --accent: hsl(30, 90%, 50%);
    --accent-dark: hsl(30, 90%, 40%);
    --accent-light: hsl(30, 90%, 60%);
}
```

### Step 4: Add Semantic Colors

Colors for specific meanings.

```css
:root {
    /* ... previous colors ... */
    
    /* Success - green (humans expect this) */
    --success: hsl(120, 70%, 40%);
    --success-light: hsl(120, 70%, 85%);
    
    /* Warning - yellow/orange */
    --warning: hsl(45, 100%, 50%);
    --warning-light: hsl(45, 100%, 85%);
    
    /* Danger - red */
    --danger: hsl(0, 90%, 50%);
    --danger-light: hsl(0, 90%, 85%);
    
    /* Info - light blue */
    --info: hsl(210, 90%, 50%);
    --info-light: hsl(210, 90%, 85%);
}
```

### Step 5: Add Neutral Colors

For text, backgrounds, borders.

```css
:root {
    /* ... previous colors ... */
    
    /* Neutrals for text and backgrounds */
    --text-primary: hsl(0, 0%, 15%);      /* Very dark gray */
    --text-secondary: hsl(0, 0%, 50%);    /* Medium gray */
    --text-disabled: hsl(0, 0%, 70%);     /* Light gray */
    
    --bg-primary: hsl(0, 0%, 100%);       /* White */
    --bg-secondary: hsl(0, 0%, 95%);      /* Light gray */
    --bg-tertiary: hsl(0, 0%, 90%);       /* Medium light gray */
    
    --border: hsl(0, 0%, 85%);            /* For borders */
}
```

### Complete Color Palette Example

```css
/* Tech Startup Color Palette */
:root {
    /* Dominant (60%) */
    --dominant: hsl(0, 0%, 97%);
    
    /* Primary (30%) - Blue */
    --primary: hsl(210, 80%, 45%);
    --primary-dark: hsl(210, 80%, 35%);
    --primary-light: hsl(210, 80%, 55%);
    
    /* Accent (10%) - Orange */
    --accent: hsl(30, 90%, 50%);
    --accent-dark: hsl(30, 90%, 40%);
    --accent-light: hsl(30, 90%, 60%);
    
    /* Semantic Colors */
    --success: hsl(120, 70%, 40%);
    --success-light: hsl(120, 70%, 85%);
    --warning: hsl(45, 100%, 50%);
    --warning-light: hsl(45, 100%, 85%);
    --danger: hsl(0, 90%, 50%);
    --danger-light: hsl(0, 90%, 85%);
    --info: hsl(210, 90%, 50%);
    --info-light: hsl(210, 90%, 85%);
    
    /* Neutrals */
    --text-primary: hsl(0, 0%, 15%);
    --text-secondary: hsl(0, 0%, 50%);
    --text-disabled: hsl(0, 0%, 70%);
    --bg-primary: hsl(0, 0%, 100%);
    --bg-secondary: hsl(0, 0%, 95%);
    --bg-tertiary: hsl(0, 0%, 90%);
    --border: hsl(0, 0%, 85%);
}

/* Usage Example */
body {
    background: var(--bg-primary);
    color: var(--text-primary);
}

.header {
    background: var(--primary);
    color: white;
}

.button {
    background: var(--primary);
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
}

.button:hover {
    background: var(--primary-dark);
}

.button-secondary {
    background: var(--accent);
}

.button-secondary:hover {
    background: var(--accent-dark);
}

.success-badge {
    background: var(--success-light);
    color: var(--success);
}

.error-message {
    background: var(--danger-light);
    color: var(--danger);
}
```

---

## Lesson 1.1.6: Dark Mode Color Palette

Modern websites need both light and dark modes. Here's how to create them.

### Strategy

For dark mode, flip the lightness values while keeping hue and saturation similar.

```css
/* Light Mode */
@media (prefers-color-scheme: light) {
    :root {
        --dominant: hsl(0, 0%, 97%);
        --primary: hsl(210, 80%, 45%);
        --text-primary: hsl(0, 0%, 15%);
        --bg-primary: hsl(0, 0%, 100%);
        --border: hsl(0, 0%, 85%);
    }
}

/* Dark Mode - Flip lightness */
@media (prefers-color-scheme: dark) {
    :root {
        --dominant: hsl(0, 0%, 15%);      /* Flipped from 97% */
        --primary: hsl(210, 80%, 55%);    /* Flipped from 45% */
        --text-primary: hsl(0, 0%, 95%);  /* Flipped from 15% */
        --bg-primary: hsl(0, 0%, 10%);    /* Flipped from 100% */
        --border: hsl(0, 0%, 25%);        /* Flipped from 85% */
    }
}
```

### Complete Dark Mode Example

```css
:root {
    /* Light Mode (default) */
    --dominant: hsl(0, 0%, 97%);
    --primary: hsl(210, 80%, 45%);
    --primary-dark: hsl(210, 80%, 35%);
    --primary-light: hsl(210, 80%, 55%);
    
    --accent: hsl(30, 90%, 50%);
    --accent-dark: hsl(30, 90%, 40%);
    --accent-light: hsl(30, 90%, 60%);
    
    --success: hsl(120, 70%, 40%);
    --success-light: hsl(120, 70%, 85%);
    
    --text-primary: hsl(0, 0%, 15%);
    --text-secondary: hsl(0, 0%, 50%);
    --bg-primary: hsl(0, 0%, 100%);
    --bg-secondary: hsl(0, 0%, 95%);
    --border: hsl(0, 0%, 85%);
}

/* Dark Mode */
@media (prefers-color-scheme: dark) {
    :root {
        --dominant: hsl(0, 0%, 15%);
        --primary: hsl(210, 80%, 55%);    /* Lighter for dark mode */
        --primary-dark: hsl(210, 80%, 45%);
        --primary-light: hsl(210, 80%, 65%);
        
        --accent: hsl(30, 90%, 60%);      /* Lighter for dark mode */
        --accent-dark: hsl(30, 90%, 50%);
        --accent-light: hsl(30, 90%, 70%);
        
        --success: hsl(120, 70%, 50%);    /* Lighter for dark mode */
        --success-light: hsl(120, 70%, 25%);
        
        --text-primary: hsl(0, 0%, 95%);
        --text-secondary: hsl(0, 0%, 70%);
        --bg-primary: hsl(0, 0%, 10%);
        --bg-secondary: hsl(0, 0%, 20%);
        --border: hsl(0, 0%, 25%);
    }
}

/* Usage stays the same */
body {
    background: var(--bg-primary);
    color: var(--text-primary);
    /* Automatically adapts to light/dark mode */
}
```

---

## Practice Exercise 1.1.6.1

Create a color palette for a **health and wellness app**.

Requirements:
1. Choose 3 main colors (dominant, primary, accent)
2. Create 2 variations for each (light, dark)
3. Add semantic colors (success, warning, danger)
4. Write it as CSS variables
5. Create dark mode versions

**Solution Framework**:

```css
:root {
    /* Health & Wellness - should feel calming, natural, trustworthy */
    
    /* Dominant - soft, calming background */
    --dominant: hsl(180, 30%, 96%);      /* Very light cyan-ish */
    
    /* Primary - green (health, growth) */
    --primary: hsl(140, 70%, 45%);
    --primary-dark: hsl(140, 70%, 35%);
    --primary-light: hsl(140, 70%, 55%);
    
    /* Accent - warm orange (energy, vitality) */
    --accent: hsl(25, 85%, 50%);
    --accent-dark: hsl(25, 85%, 40%);
    --accent-light: hsl(25, 85%, 60%);
    
    /* Semantic */
    --success: hsl(140, 70%, 40%);
    --warning: hsl(45, 100%, 50%);
    --danger: hsl(0, 90%, 50%);
    
    /* Neutrals */
    --text-primary: hsl(0, 0%, 20%);
    --bg-primary: hsl(0, 0%, 100%);
}

@media (prefers-color-scheme: dark) {
    :root {
        --dominant: hsl(180, 30%, 20%);
        --primary: hsl(140, 70%, 55%);
        --accent: hsl(25, 85%, 60%);
        --text-primary: hsl(0, 0%, 95%);
        --bg-primary: hsl(0, 0%, 12%);
    }
}
```

---

## Summary: Module 1.1

You've learned:
- ✅ Color models (RGB, Hex, HSL, OKLCH)
- ✅ Color wheel and harmony rules
- ✅ Color psychology and emotion
- ✅ The 60-30-10 rule for balance
- ✅ Creating professional palettes
- ✅ Dark mode implementation

**Key Takeaway**: Color is psychology. Intentional color choices communicate emotion and guide user behavior.

---

## Module 1.2: Typography Mastery
### Duration: 8 hours | Level: Beginner

---

## Lesson 1.2.1: Typography Fundamentals

### What is Typography?

Typography is the art and technique of arranging text. Good typography:
- Improves readability
- Creates hierarchy
- Guides user attention
- Communicates emotion

### Key Typography Concepts

#### 1. **Font Family**

A font family is a group of related typefaces.

```css
/* Serif Fonts - traditional, formal */
body {
    font-family: Georgia, 'Times New Roman', serif;
}

/* Sans-serif Fonts - modern, clean */
body {
    font-family: Arial, Helvetica, sans-serif;
}

/* Monospace Fonts - code, technical */
code {
    font-family: 'Courier New', monospace;
}

/* Custom Fonts from Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

body {
    font-family: 'Inter', sans-serif;
}
```

#### 2. **Font Size**

Measured in pixels (px), em, rem, or percentage.

```css
/* Pixel sizes (fixed) */
.small { font-size: 12px; }
.normal { font-size: 16px; }
.large { font-size: 20px; }

/* REM (relative to root) - better for scaling */
html { font-size: 16px; }  /* Default */

.small { font-size: 0.75rem; }   /* 12px */
.normal { font-size: 1rem; }     /* 16px */
.large { font-size: 1.25rem; }   /* 20px */

/* EM (relative to parent) - cascades */
.container { font-size: 16px; }
.container .text { font-size: 1em; }      /* 16px */
.container .small { font-size: 0.875em; } /* 14px */
```

#### 3. **Font Weight**

How thick/bold the text is. 100-900 (100 = thin, 900 = black)

```css
/* Named weights */
.light { font-weight: light; }      /* 300 */
.normal { font-weight: normal; }    /* 400 (default) */
.bold { font-weight: bold; }        /* 700 */

/* Numeric weights */
.thin { font-weight: 100; }
.extralight { font-weight: 200; }
.light { font-weight: 300; }
.regular { font-weight: 400; }
.medium { font-weight: 500; }
.semibold { font-weight: 600; }
.bold { font-weight: 700; }
.extrabold { font-weight: 800; }
.black { font-weight: 900; }

/* Best practice: use 400 and 600-700 for most designs */
.text { font-weight: 400; }
.heading { font-weight: 600; }
```

#### 4. **Line Height**

Space between lines of text. Affects readability.

```css
/* Line height as multiplier (recommended) */
body {
    line-height: 1.5;  /* 1.5x the font size */
}

.heading {
    line-height: 1.2;  /* Tighter for headings */
}

.display {
    line-height: 1.1;  /* Very tight for large text */
}

/* Line height as pixels (not recommended, less flexible) */
body {
    line-height: 24px;
}

/* Recommended line-height values */
.body-text { line-height: 1.6; }      /* Extra readable for paragraphs */
.heading { line-height: 1.2; }        /* Tighter for headings */
.display { line-height: 1.1; }        /* Very tight for large text */
```

**Why line-height matters**:
- Too small (< 1.3): Hard to read, eye strain
- Perfect (1.5-1.6): Easy to read
- Too large (> 2): Disjointed, doesn't feel cohesive

#### 5. **Letter Spacing**

Space between individual letters.

```css
/* Default is normal (0) */
.normal { letter-spacing: normal; }

/* Slightly increased - more elegant */
.heading { letter-spacing: 0.05em; }

/* Significantly increased - luxury feel */
.luxury { letter-spacing: 0.15em; }

/* Decreased - compact, technical */
.compact { letter-spacing: -0.02em; }
```

---

## Lesson 1.2.2: Font Pairing

Pairing fonts well is crucial. Bad pairings look amateurish.

### Font Pairing Rules

#### Rule 1: Serif + Sans-Serif
Classic, always works.

```css
/* Serif for headings, sans-serif for body */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400&display=swap');

h1, h2, h3 {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
}

body, p {
    font-family: 'Inter', sans-serif;
    font-weight: 400;
}
```

#### Rule 2: Same Family, Different Weights
Harmony with variation.

```css
/* Same font family, different weights */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

body {
    font-family: 'Poppins', sans-serif;
    font-weight: 400;  /* Regular for body */
}

.heading {
    font-family: 'Poppins', sans-serif;
    font-weight: 700;  /* Bold for headings */
}

.highlight {
    font-family: 'Poppins', sans-serif;
    font-weight: 600;  /* Semi-bold for emphasis */
}
```

#### Rule 3: Contrast in Styles
Different styles for clear distinction.

```css
/* Serif = traditional, Sans-serif = modern */
@import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600&family=Montserrat:wght@400;700&display=swap');

h1 {
    font-family: 'Montserrat', sans-serif;  /* Modern */
    font-weight: 700;
    font-size: 2.5rem;
}

body {
    font-family: 'Lora', serif;             /* Traditional */
    font-weight: 400;
    font-size: 1rem;
    line-height: 1.6;
}
```

### Professional Font Pairings

Here are proven combinations:

```css
/* Modern SaaS (clean, professional) */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

:root {
    --font-primary: 'Inter', sans-serif;
}

/* Luxury (elegant, sophisticated) */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lora:wght@400&display=swap');

:root {
    --font-heading: 'Playfair Display', serif;
    --font-body: 'Lora', serif;
}

/* Tech (bold, geometric) */
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Roboto:wght@400;500&display=swap');

:root {
    --font-heading: 'Space Mono', monospace;
    --font-body: 'Roboto', sans-serif;
}

/* Creative (playful, friendly) */
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&family=Outfit:wght@400;700&display=swap');

:root {
    --font-heading: 'Outfit', sans-serif;
    --font-body: 'Fredoka', sans-serif;
}
```

---

## Lesson 1.2.3: Creating a Typography System

A typography system ensures consistency and hierarchy across your design.

### Step 1: Define Your Base Font Size

Typically 16px for body text (matches browser default).

```css
html {
    font-size: 16px;  /* Base size */
}
```

### Step 2: Create a Font Scale

Use a ratio (like 1.5x or 1.2x) to create harmonious sizes.

```css
/* Using 1.5 ratio (great for clear hierarchy) */
:root {
    /* Base */
    --fs-base: 1rem;        /* 16px */
    
    /* Smaller */
    --fs-xs: 0.67rem;       /* 10.7px - very small text */
    --fs-sm: 0.875rem;      /* 14px - small text */
    
    /* Larger */
    --fs-lg: 1.5rem;        /* 24px */
    --fs-xl: 2.25rem;       /* 36px */
    --fs-2xl: 3.375rem;     /* 54px - large heading */
    --fs-3xl: 5.062rem;     /* 81px - hero heading */
}

/* Usage */
.caption { font-size: var(--fs-xs); }
.body { font-size: var(--fs-base); line-height: 1.6; }
.small { font-size: var(--fs-sm); }
h3 { font-size: var(--fs-lg); }
h2 { font-size: var(--fs-xl); }
h1 { font-size: var(--fs-2xl); }
.hero { font-size: var(--fs-3xl); }
```

### Step 3: Define Font Families

```css
:root {
    /* Fonts */
    --font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-heading: 'Playfair Display', serif;
    --font-mono: 'Courier New', monospace;
}

body {
    font-family: var(--font-primary);
}

h1, h2, h3 {
    font-family: var(--font-heading);
}

code, pre {
    font-family: var(--font-mono);
}
```

### Step 4: Define Font Weights

```css
:root {
    --fw-light: 300;
    --fw-normal: 400;
    --fw-medium: 500;
    --fw-semibold: 600;
    --fw-bold: 700;
}

.text-light { font-weight: var(--fw-light); }
.text-normal { font-weight: var(--fw-normal); }
.text-semibold { font-weight: var(--fw-semibold); }
.text-bold { font-weight: var(--fw-bold); }
```

### Step 5: Define Typography Classes

```css
/* Display - Large, bold, hero text */
.display-large {
    font-family: var(--font-heading);
    font-size: var(--fs-3xl);
    font-weight: var(--fw-bold);
    line-height: 1.1;
    letter-spacing: -0.02em;
}

.display {
    font-family: var(--font-heading);
    font-size: var(--fs-2xl);
    font-weight: var(--fw-bold);
    line-height: 1.2;
}

/* Heading 1 */
h1 {
    font-size: var(--fs-xl);
    font-weight: var(--fw-bold);
    line-height: 1.2;
    margin-bottom: 0.5em;
}

/* Heading 2 */
h2 {
    font-size: var(--fs-lg);
    font-weight: var(--fw-semibold);
    line-height: 1.3;
    margin-bottom: 0.5em;
}

/* Heading 3 */
h3 {
    font-size: var(--fs-base);
    font-weight: var(--fw-semibold);
    line-height: 1.4;
    margin-bottom: 0.5em;
}

/* Body text */
p {
    font-size: var(--fs-base);
    font-weight: var(--fw-normal);
    line-height: 1.6;
    margin-bottom: 1em;
}

/* Small text */
.small {
    font-size: var(--fs-sm);
    font-weight: var(--fw-normal);
    line-height: 1.5;
}

/* Extra small text (captions, labels) */
.caption {
    font-size: var(--fs-xs);
    font-weight: var(--fw-normal);
    line-height: 1.4;
    color: var(--text-secondary);
}
```

### Complete Typography System Example

```css
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600;700&display=swap');

:root {
    /* Font families */
    --font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-heading: 'Playfair Display', serif;
    
    /* Font sizes (1.5 ratio) */
    --fs-xs: 0.67rem;    /* 10.7px */
    --fs-sm: 0.875rem;   /* 14px */
    --fs-base: 1rem;     /* 16px */
    --fs-lg: 1.5rem;     /* 24px */
    --fs-xl: 2.25rem;    /* 36px */
    --fs-2xl: 3.375rem;  /* 54px */
    
    /* Font weights */
    --fw-normal: 400;
    --fw-medium: 500;
    --fw-semibold: 600;
    --fw-bold: 700;
}

/* Base */
body {
    font-family: var(--font-primary);
    font-size: var(--fs-base);
    font-weight: var(--fw-normal);
    line-height: 1.6;
    color: var(--text-primary);
}

/* Headings */
h1 {
    font-family: var(--font-heading);
    font-size: var(--fs-2xl);
    font-weight: var(--fw-bold);
    line-height: 1.1;
}

h2 {
    font-family: var(--font-heading);
    font-size: var(--fs-xl);
    font-weight: var(--fw-bold);
    line-height: 1.2;
}

h3 {
    font-family: var(--font-heading);
    font-size: var(--fs-lg);
    font-weight: var(--fw-bold);
    line-height: 1.3;
}

/* Paragraph */
p {
    margin-bottom: 1em;
    line-height: 1.6;
}

/* Small */
.small {
    font-size: var(--fs-sm);
}

.caption {
    font-size: var(--fs-xs);
    color: var(--text-secondary);
}
```

---

## Lesson 1.2.4: Responsive Typography

Typography should scale with screen size.

### Using Fluid Typography

Instead of fixed breakpoints, use `clamp()` for smooth scaling.

```css
/* Clamp: min, preferred, max */

/* Body text: min 14px, grows with viewport, max 18px */
body {
    font-size: clamp(0.875rem, 1vw, 1.125rem);
    line-height: 1.6;
}

/* Heading: min 32px, grows with viewport, max 64px */
h1 {
    font-size: clamp(2rem, 8vw, 4rem);
    line-height: 1.1;
}

h2 {
    font-size: clamp(1.5rem, 5vw, 2.5rem);
    line-height: 1.2;
}

h3 {
    font-size: clamp(1.25rem, 3vw, 1.75rem);
    line-height: 1.3;
}
```

### Traditional Media Queries Approach

```css
/* Mobile first */
body {
    font-size: 14px;
    line-height: 1.5;
}

h1 {
    font-size: 24px;
    line-height: 1.2;
}

/* Tablet */
@media (min-width: 768px) {
    body {
        font-size: 16px;
    }
    
    h1 {
        font-size: 36px;
    }
}

/* Desktop */
@media (min-width: 1024px) {
    body {
        font-size: 18px;
    }
    
    h1 {
        font-size: 48px;
    }
}
```

---

## Practice Exercise 1.2.4.1

Create a typography system for a **marketing blog**.

Requirements:
1. Choose 2 font families (heading + body)
2. Create a font scale with 6 sizes
3. Define font weights (at least 2-3)
4. Create CSS classes for h1, h2, h3, p, small, caption
5. Make it responsive using clamp()

**Solution Framework**:

```css
@import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&family=Open+Sans:wght@400;600&display=swap');

:root {
    --font-heading: 'Merriweather', serif;
    --font-body: 'Open Sans', sans-serif;
    
    --fs-sm: 0.875rem;
    --fs-base: 1rem;
    --fs-lg: 1.5rem;
    --fs-xl: 2rem;
    --fs-2xl: 2.5rem;
    --fs-3xl: 3.5rem;
    
    --fw-normal: 400;
    --fw-bold: 700;
}

body {
    font-family: var(--font-body);
    font-size: clamp(0.875rem, 1vw, 1.125rem);
    line-height: 1.6;
}

h1 {
    font-family: var(--font-heading);
    font-size: clamp(2.5rem, 7vw, 3.5rem);
    font-weight: var(--fw-bold);
    line-height: 1.1;
}

h2 {
    font-family: var(--font-heading);
    font-size: clamp(1.75rem, 5vw, 2.5rem);
    font-weight: var(--fw-bold);
    line-height: 1.2;
}

h3 {
    font-family: var(--font-heading);
    font-size: clamp(1.25rem, 3vw, 1.75rem);
    font-weight: var(--fw-bold);
    line-height: 1.3;
}

p {
    margin-bottom: 1em;
}

.small {
    font-size: 0.875rem;
}

.caption {
    font-size: 0.75rem;
    color: var(--text-secondary);
}
```

---

## Summary: Module 1.2

You've learned:
- ✅ Font families and selection
- ✅ Font sizes, weights, and line-height
- ✅ Proper font pairing techniques
- ✅ Creating scalable typography systems
- ✅ Responsive typography with clamp()

**Key Takeaway**: A well-designed typography system creates hierarchy, improves readability, and guides user attention.

---

## Module 1.3: Figma-to-Code Workflow
### Duration: 12 hours | Level: Intermediate

---

## Lesson 1.3.1: Understanding Figma for Developers

Figma is a design tool. As a developer, you need to:
1. **Read designs** accurately
2. **Extract measurements** precisely
3. **Understand design intent** (why elements are positioned certain ways)
4. **Translate to code** without losing quality

### Key Figma Concepts

#### Design Hierarchy in Figma

```
Figma File (Project)
  ├── Page (e.g., "Homepage", "Components")
  │   ├── Frame (e.g., "Desktop", "Mobile")
  │   │   ├── Component (e.g., "Button", "Card")
  │   │   │   ├── Group (e.g., "Icon + Text")
  │   │   │   └── Element (e.g., "Text", "Rectangle")
```

When translating to code:
- **Frame** → Container/Page
- **Component** → React Component
- **Group** → Div
- **Element** → Actual HTML element

---

## Lesson 1.3.2: Extracting Measurements from Figma

### Method 1: Using Figma DevMode (Recommended)

Figma DevMode shows exact CSS values.

**Steps**:
1. Open Figma file
2. Click "Dev" tab (top right)
3. Select element
4. View measurements on right panel
5. Copy values directly

**What you'll see**:
```
Position: X, Y
Size: Width, Height
Padding: Top, Right, Bottom, Left
Gap: Value
Border: Style, Color, Width
Border Radius: Value
Shadow: X, Y, Blur, Spread, Color, Opacity
Font: Family, Size, Weight, Line Height
```

### Method 2: Manual Inspection

If DevMode isn't available:

1. **Select element** in Figma
2. **Right panel shows**:
   - Position (X, Y)
   - Size (W, H)
   - Fill (colors)
   - Stroke (borders)
   - Padding
   - Gap
   - Radius
   - Shadow

3. **Copy values** and convert to CSS

### Example: Extracting a Button

**In Figma**:
- Position: X=10, Y=10
- Size: W=120, H=40
- Fill: #FF6B35
- Padding: 10px 20px (uniform)
- Border Radius: 4px
- Font: Inter, 14px, Weight 600

**Convert to CSS**:

```css
.button {
    /* Position (if absolute) */
    position: absolute;
    top: 10px;
    left: 10px;
    
    /* Size */
    width: 120px;
    height: 40px;
    
    /* Padding */
    padding: 10px 20px;
    
    /* Color */
    background: #FF6B35;
    color: white;
    
    /* Border */
    border: none;
    border-radius: 4px;
    
    /* Typography */
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    font-weight: 600;
}
```

---

## Lesson 1.3.3: Extracting Colors from Figma

### Color Values in Figma

Figma shows colors in multiple formats. Copy the one you need.

```
Figma shows:
├── HEX: #FF6B35
├── RGB: RGB(255, 107, 53)
├── HSL: HSL(14, 100%, 60%)
└── CSS: rgba(255, 107, 53, 1)
```

### Converting Figma Colors to CSS

**From Figma color panel**:

1. Click the color square
2. Select format (Hex, RGB, HSL, OKLCH)
3. Copy value
4. Paste in CSS

**Example**:
```css
/* Figma shows: #FF6B35 */
.button {
    background: #FF6B35;
}

/* With transparency */
.overlay {
    background: rgba(255, 107, 53, 0.8);
}

/* In HSL (easier for variants) */
.button {
    background: hsl(14, 100%, 60%);
}

.button:hover {
    background: hsl(14, 100%, 50%);  /* Darker */
}
```

### Creating Design Tokens from Figma

Instead of copying colors individually, create a token system:

```css
:root {
    /* Extract from Figma color library */
    --primary: #FF6B35;
    --secondary: #004E89;
    --success: #06A77D;
    --warning: #F4A261;
    --danger: #E63946;
    
    --text-primary: #1A1A1A;
    --text-secondary: #555555;
    --bg-primary: #FFFFFF;
    --bg-secondary: #F5F5F5;
}

.button { background: var(--primary); }
.alert-success { background: var(--success); }
.alert-danger { background: var(--danger); }
```

---

## Lesson 1.3.4: Extracting Typography from Figma

### Reading Font Properties in Figma

When you select text in Figma:

```
Right Panel Shows:
├── Font: Family (e.g., "Inter")
├── Weight: (e.g., "600")
├── Size: (e.g., "16px")
├── Line Height: (e.g., "1.5" or "24px")
├── Letter Spacing: (e.g., "0px")
└── Text Transform: (e.g., "None")
```

### Converting to CSS

**Figma values**:
- Font: Inter
- Weight: 600
- Size: 16px
- Line Height: 1.5
- Letter Spacing: 0

**CSS**:
```css
.heading {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 16px;
    line-height: 1.5;
    letter-spacing: 0;
}
```

### Complete Typography Extraction Example

**Figma Design System** (what you'll see):
```
Display Large:
  Font: Playfair Display, Bold, 48px, 1.1 line-height

Heading 1:
  Font: Playfair Display, Bold, 36px, 1.2 line-height

Heading 2:
  Font: Playfair Display, SemiBold, 28px, 1.2 line-height

Body:
  Font: Inter, Regular, 16px, 1.6 line-height, 0px letter-spacing

Small:
  Font: Inter, Regular, 14px, 1.5 line-height
```

**CSS from Figma**:
```css
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;600&display=swap');

:root {
    --font-display: 'Playfair Display', serif;
    --font-body: 'Inter', sans-serif;
}

.display-large {
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 48px;
    line-height: 1.1;
}

h1 {
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 36px;
    line-height: 1.2;
}

h2 {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 28px;
    line-height: 1.2;
}

body {
    font-family: var(--font-body);
    font-weight: 400;
    font-size: 16px;
    line-height: 1.6;
}

.small {
    font-family: var(--font-body);
    font-weight: 400;
    font-size: 14px;
    line-height: 1.5;
}
```

---

## Lesson 1.3.5: Extracting Spacing & Layout from Figma

### Understanding Figma Auto Layout

Figma has "Auto Layout" which maps directly to CSS Flexbox.

**Figma Auto Layout** → **CSS Flexbox**

```
Figma Setting          | CSS Property
---                    | ---
Direction: Horizontal | flex-direction: row
Direction: Vertical   | flex-direction: column
Gap: 16px             | gap: 16px
Padding: 20px         | padding: 20px
Align: Top            | align-items: flex-start
Align: Center         | align-items: center
Justify: Space-between| justify-content: space-between
```

### Reading Spacing in Figma

When you select element:

```
Right Panel:
├── Position: X, Y (absolute position)
├── Size: W, H (width, height)
├── Padding: Top, Right, Bottom, Left
├── Gap: Value (space between children)
└── Constraints: How it scales
```

### Converting Figma Layout to CSS

**Figma Card Layout**:
```
Frame "Card":
  ├── Position: X=0, Y=0
  ├── Size: 300×400
  ├── Padding: 20px
  ├── Gap: 16px
  └── Children: Image, Title, Description, Button
```

**CSS**:
```css
.card {
    width: 300px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.card-image {
    width: 100%;
    height: auto;
}

.card-title {
    font-size: 18px;
    font-weight: 600;
}

.card-description {
    font-size: 14px;
    color: #666;
    line-height: 1.5;
}

.card-button {
    width: 100%;
    padding: 12px;
    background: #FF6B35;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}
```

---

## Lesson 1.3.6: Creating a Figma Specs Document

The best way to stay organized is to document everything.

### Specs Document Template

Create a document (in Notion, Google Doc, or your README) with:

```markdown
# Design Specifications

## Colors
- Primary Blue: #004E89
- Secondary Orange: #FF6B35
- Success Green: #06A77D
- Text Dark: #1A1A1A
- Text Light: #555555
- Background: #FFFFFF

## Typography
- Heading Font: Playfair Display
- Body Font: Inter
- Display Large: 48px, Bold, 1.1 line-height
- Heading 1: 36px, Bold, 1.2 line-height
- Body: 16px, Regular, 1.6 line-height
- Small: 14px, Regular, 1.5 line-height

## Spacing Scale
- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px
- 2xl: 48px

## Components

### Button (Primary)
- Size: 120px × 40px
- Padding: 10px 20px
- Background: Primary Blue
- Border Radius: 4px
- Font: Inter, 14px, Weight 600
- States:
  - Default: Primary Blue
  - Hover: Dark Blue
  - Active: Darker Blue
  - Disabled: Gray

### Card
- Size: 300px × auto
- Padding: 20px
- Gap: 16px
- Border Radius: 8px
- Shadow: 0 2px 8px rgba(0,0,0,0.1)

### Input
- Height: 40px
- Padding: 10px 12px
- Border: 1px solid #CCCCCC
- Border Radius: 4px
- Font: Inter, 14px
```

### Creating a CSS File from Specs

```css
/* Color Variables */
:root {
    --primary: #004E89;
    --secondary: #FF6B35;
    --success: #06A77D;
    --text-primary: #1A1A1A;
    --text-secondary: #555555;
    --bg-primary: #FFFFFF;
}

/* Spacing Scale */
:root {
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
    --space-2xl: 48px;
}

/* Typography */
:root {
    --font-display: 'Playfair Display', serif;
    --font-body: 'Inter', sans-serif;
    
    --fs-small: 14px;
    --fs-body: 16px;
    --fs-h1: 36px;
    --fs-display: 48px;
}

/* Components */
.button-primary {
    width: 120px;
    height: 40px;
    padding: 10px 20px;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 4px;
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background 200ms ease-out;
}

.button-primary:hover {
    background: #003A5C;  /* Darker blue */
}

.button-primary:active {
    background: #002A42;  /* Even darker */
}

.button-primary:disabled {
    background: #CCCCCC;
    cursor: not-allowed;
}

.card {
    width: 300px;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    background: var(--bg-primary);
}

.input {
    width: 100%;
    height: 40px;
    padding: 10px 12px;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    font-family: var(--font-body);
    font-size: 14px;
    transition: border-color 200ms ease-out;
}

.input:focus {
    outline: none;
    border-color: var(--primary);
}
```

---

## Practice Exercise 1.3.6.1

Create a complete Figma Specs Document for a simple **Landing Page**.

Requirements:
1. Define color palette (5-8 colors minimum)
2. Define typography system (4-5 sizes minimum)
3. Define spacing scale (6-8 values)
4. Document 3 components:
   - Button (with states)
   - Card
   - Hero Section
5. Write CSS variables for all values

**Solution Framework**:

```markdown
# Landing Page Design Specifications

## Colors
- Primary: #0066CC
- Accent: #FF6B35
- Success: #06A77D
- Danger: #E63946
- Text Dark: #1A1A1A
- Text Light: #666666
- Background Light: #FFFFFF
- Background Dark: #F5F5F5

## Typography
- Display Font: Playfair Display
- Body Font: Inter
- Sizes:
  - Display: 64px
  - H1: 48px
  - H2: 36px
  - Body: 16px
  - Small: 14px

## Spacing
- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px
- 2xl: 48px

## Components

### Hero Section
- Height: 600px
- Padding: 48px
- Background: Primary Blue
- Text: White
- Heading: Display 64px
- Description: Body 16px
- Button: Primary, 140px × 44px

### Card
- Width: 300px
- Padding: 24px
- Border Radius: 8px
- Shadow: 0 4px 12px rgba(0,0,0,0.08)
- Gap: 16px

### Button
- Height: 44px
- Padding: 12px 24px
- Border Radius: 4px
- Font: Inter, 14px, Weight 600
```

---

## Summary: Week 1

You've learned:
- ✅ Color theory and psychology
- ✅ How to create and apply color palettes
- ✅ Typography fundamentals and systems
- ✅ How to extract specs from Figma
- ✅ How to convert design to CSS
- ✅ Creating design documentation

**Key Deliverables**:
1. A color palette (light + dark mode)
2. A typography system
3. A specs document for a simple design
4. CSS variables for colors and typography

**Next Week**: CSS Fundamentals & Cascade (where you'll apply these colors and typography!)

---

## Week 1 Practical Project: Create Your First Design System

### Project Requirements

Create a complete design system for a **Simple SaaS Dashboard** including:

1. **Color Palette**
   - 5 main colors (primary, secondary, success, warning, danger)
   - Light and dark modes
   - 3-4 variations for each main color

2. **Typography System**
   - 2 font families (heading + body)
   - 5 font sizes
   - All CSS variables

3. **Spacing System**
   - 8-point grid scale (4px, 8px, 12px, 16px, 20px, 24px, 32px, 48px)

4. **Component Library (CSS)**
   - Button (primary, secondary, disabled states)
   - Card
   - Input field
   - Badge

5. **Design Specs Document**
   - All measurements
   - All color values
   - All typography values

### Deliverables

```
design-system/
├── colors.css         (Color variables)
├── typography.css     (Font & size variables)
├── spacing.css        (Spacing scale)
├── components.css     (Component styles)
├── dark-mode.css      (Dark mode overrides)
└── README.md          (Design specs document)
```

### Example File Structure

**colors.css**:
```css
:root {
    --primary: hsl(210, 80%, 45%);
    --primary-dark: hsl(210, 80%, 35%);
    --secondary: hsl(30, 90%, 50%);
    --success: hsl(120, 70%, 40%);
    --warning: hsl(45, 100%, 50%);
    --danger: hsl(0, 90%, 50%);
    
    --text-primary: hsl(0, 0%, 15%);
    --text-secondary: hsl(0, 0%, 50%);
    --bg-primary: hsl(0, 0%, 100%);
    --bg-secondary: hsl(0, 0%, 95%);
}

@media (prefers-color-scheme: dark) {
    :root {
        --primary: hsl(210, 80%, 55%);
        --text-primary: hsl(0, 0%, 95%);
        --bg-primary: hsl(0, 0%, 10%);
    }
}
```

This project prepares you for Week 2 where you'll apply these values in actual layouts.

---

**End of Week 1 Content**

Next: Week 2 - CSS Fundamentals & Cascade Model (the crucial module!)
