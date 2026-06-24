# Week 2: CSS Fundamentals & Cascade Model
## Complete Course Content with Code Examples and Exercises

**Duration**: 40 hours | **Focus**: Master CSS specificity, box model, and understand how different display types affect spacing

---

## Module 2.0: CSS Cascade, Specificity & Inheritance
### Duration: 12 hours | Level: Beginner to Intermediate

This is the MOST IMPORTANT module. Master this and everything else clicks into place.

---

## Lesson 2.0.1: Understanding CSS Cascade

### What is the Cascade?

The cascade is the algorithm CSS uses to determine which rule applies when multiple rules target the same element.

Think of it like layers stacking on top of each other - the top layer wins.

### The Cascade Order (From Lowest to Highest Priority)

```
1. Browser defaults
   └─ <h1> is bold by default
   └─ <a> is blue by default
   
2. Author stylesheets (YOUR CSS)
   ├─ External stylesheet
   ├─ Internal <style> tag
   └─ Inline style attribute
   
3. Specificity (within your CSS)
   ├─ Element selectors (1 point)
   ├─ Class selectors (10 points)
   ├─ ID selectors (100 points)
   └─ Inline styles (1000 points)
   
4. Source order
   └─ Last rule in CSS file wins (if everything else is equal)
   
5. !important (overrides everything except higher specificity !important)
   └─ Use sparingly - nuclear option
```

### Real Example: The Cascade in Action

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        /* Rule 1: Element selector (1 point) */
        p {
            color: blue;
        }
        
        /* Rule 2: Class selector (10 points) - WINS */
        .highlight {
            color: red;
        }
        
        /* Rule 3: ID selector (100 points) - WINS EVERYTHING */
        #special {
            color: green;
        }
    </style>
</head>
<body>
    <p>Blue text (element selector)</p>
    
    <p class="highlight">Red text (class wins over element)</p>
    
    <p id="special">Green text (ID wins over all)</p>
    
    <p id="special" style="color: yellow;">Yellow text (inline wins over ID)</p>
    
    <p style="color: purple !important;">Purple text (!important wins)</p>
</body>
</html>
```

**Visual Result**:
```
Blue text (element selector)
Red text (class wins over element)
Green text (ID wins over all)
Yellow text (inline wins over ID)
Purple text (!important wins)
```

### Why Cascade Matters

Understanding the cascade helps you:
- ✅ Predict which CSS will apply
- ✅ Debug styling issues quickly
- ✅ Avoid specificity wars
- ✅ Write maintainable CSS

---

## Lesson 2.0.2: CSS Specificity - The Scoring System

Specificity is how CSS calculates which rule wins when multiple rules target the same element.

### Specificity Score

Specificity is calculated as a 4-part number: `[a, b, c, d]`

```
[a, b, c, d]
 | | | |
 | | | └─ Element selectors, pseudo-elements (1 point each)
 | | └─── Class selectors, attribute selectors, pseudo-classes (10 points each)
 | └───── ID selectors (100 points each)
 └─────── Inline styles (1000 points each)
```

### Calculating Specificity

Let's score some selectors:

```css
/* Example 1: Element only */
p { }
/* Specificity: [0, 0, 0, 1] */

/* Example 2: Class */
.button { }
/* Specificity: [0, 0, 1, 0] */

/* Example 3: Element + Class */
p.error { }
/* Specificity: [0, 0, 1, 1] */

/* Example 4: Multiple classes */
.container.active { }
/* Specificity: [0, 0, 2, 0] */

/* Example 5: ID */
#header { }
/* Specificity: [0, 1, 0, 0] */

/* Example 6: ID + Class + Element */
#header .nav li { }
/* Specificity: [0, 1, 1, 2] */
/*              └─ 1 ID
                 └─ 1 class
                 └─ 2 elements */

/* Example 7: Attribute selector (counts as class) */
input[type="text"] { }
/* Specificity: [0, 0, 1, 1] */
/*              └─ 1 attribute (like class)
                 └─ 1 element */

/* Example 8: Pseudo-class (counts as class) */
a:hover { }
/* Specificity: [0, 0, 1, 1] */
/*              └─ 1 pseudo-class
                 └─ 1 element */

/* Example 9: Multiple pseudo-classes */
button:hover:active { }
/* Specificity: [0, 0, 2, 1] */
/*              └─ 2 pseudo-classes
                 └─ 1 element */

/* Example 10: Pseudo-element (counts as element) */
p::before { }
/* Specificity: [0, 0, 0, 2] */
/*              └─ 1 pseudo-element
                 └─ 1 element */

/* Example 11: Inline style (HIGHEST) */
<p style="color: red;"> </p>
/* Specificity: [1, 0, 0, 0] */

/* Example 12: !important (overrides inline) */
p { color: blue !important; }
/* Specificity: [2, 0, 0, 0] (conceptually) */
```

### Specificity Comparison Rules

**Compare left to right**. First number that's different determines the winner.

```
[1, 0, 0, 0]  vs  [0, 5, 0, 0]
 ▲                 ▲
 First position    First position
 1 > 0  → LEFT WINS (inline style beats anything)

[0, 1, 0, 0]  vs  [0, 0, 5, 0]
    ▲                 ▲
    Second position   Second position
    1 > 0  → LEFT WINS (ID beats all classes)

[0, 0, 2, 0]  vs  [0, 0, 1, 5]
       ▲                ▲
       Third position   Third position
       2 > 1  → LEFT WINS (2 classes beat 5 elements)
```

### Practical Examples: Which Rule Wins?

**Example 1: Class vs Element**

```css
p { color: blue; }              /* [0, 0, 0, 1] */
.error { color: red; }          /* [0, 0, 1, 0] */

<p class="error">Text</p>
/* Result: RED (class is higher specificity) */
```

**Example 2: Class vs ID**

```css
.button { background: blue; }   /* [0, 0, 1, 0] */
#submit { background: green; }  /* [0, 1, 0, 0] */

<button id="submit" class="button">Click</button>
/* Result: GREEN (ID is higher specificity) */
```

**Example 3: Inline vs ID**

```css
#header { color: blue; }        /* [0, 1, 0, 0] */

<div id="header" style="color: red;">Text</div>
/* Result: RED (inline style is higher specificity) */
```

**Example 4: Multiple Classes**

```css
.primary { color: blue; }                          /* [0, 0, 1, 0] */
.primary.active { color: red; }                    /* [0, 0, 2, 0] */
.primary.active.large { color: green; }            /* [0, 0, 3, 0] */

<button class="primary active large">Click</button>
/* Result: GREEN (highest specificity) */
```

**Example 5: Source Order (When Specificity is EQUAL)**

```css
.button { background: blue; }    /* [0, 0, 1, 0] - comes first */
.button { background: red; }     /* [0, 0, 1, 0] - comes second - WINS! */

<button class="button">Click</button>
/* Result: RED (same specificity, so last one wins) */
```

### The !important Declaration

`!important` overrides normal specificity rules. Use sparingly (it's a code smell).

```css
p { color: blue; }                              /* Normal rule */
p { color: red !important; }                    /* !important wins */

/* Even inline styles lose to !important */
<p style="color: green;">Text</p>
/* Result: RED (from !important) */

/* Only !important beats !important */
p { color: blue !important; }
p { color: red !important; }
/* Result: RED (last !important wins) */
```

**When to use !important**:
- Utility frameworks (Tailwind uses it)
- Overriding third-party CSS
- System-critical styles

**When NOT to use**:
- In normal application code
- In libraries
- To fight specificity wars

---

## Lesson 2.0.3: Inheritance in CSS

Some CSS properties inherit from parent to child. Others don't.

### Properties That Inherit

```css
/* Typography - inherits by default */
font-family: 'Inter';
font-size: 16px;
font-weight: 400;
line-height: 1.5;
color: #333;
text-align: left;
letter-spacing: 0;

/* Example */
.container {
    font-family: 'Arial';
    color: red;
}

.container p {
    /* Inherits font-family and color from .container */
    /* But can override */
    color: blue;  /* Overrides inherited color */
}
```

### Properties That DON'T Inherit

```css
/* Box model - does NOT inherit */
width
height
margin
padding
border
background
display

/* Positioning - does NOT inherit */
position
top, right, bottom, left
z-index

/* Transform - does NOT inherit */
transform
opacity
```

### The `inherit` Keyword

Force inheritance of non-inherited properties:

```css
.button {
    width: 100px;
    border: 1px solid black;
}

.button::before {
    content: '→';
    width: inherit;          /* Inherits from button */
    border: inherit;         /* Inherits from button */
}
```

### The `initial` Keyword

Reset to browser default:

```css
.text {
    color: red;
    border: 1px solid black;
}

.text.reset {
    color: initial;          /* Back to black (browser default) */
    border: initial;         /* Back to no border (browser default) */
}
```

### The `unset` Keyword

Remove all CSS - use either inherited or initial value:

```css
.text {
    color: red;              /* Inherited property */
    margin: 20px;            /* Non-inherited property */
}

.text.reset {
    color: unset;            /* Goes to inherited value */
    margin: unset;           /* Goes to initial (0) */
}
```

---

## Lesson 2.0.4: Understanding DevTools and Strikethrough

When you inspect an element in DevTools, you see which CSS rules apply and which are overridden.

### Reading DevTools Styles Panel

```
Styles Panel shows:

✓ color: red;                    /* APPLIED (solid) */
✗ color: blue;  (strikethrough)  /* NOT APPLIED (overridden) */
✗ color: green; (strikethrough)  /* NOT APPLIED (overridden) */
```

### Why Rules Get Strikethrough

A rule is strikethrough when:
1. **Lower specificity** - A higher specificity rule wins
2. **Earlier in file** - A later rule with same specificity wins
3. **Overridden by !important** - An !important rule wins

### Example: Reading DevTools

```css
/* Your CSS file */
p { color: blue; }              /* Line 1 */
.text { color: red; }           /* Line 2 */
p.text { color: green; }        /* Line 3 */
#special { color: yellow; }     /* Line 4 */
```

```html
<p id="special" class="text">Hello</p>
```

**In DevTools, you'd see**:

```
Styles for <p>

✓ #special { color: yellow; }           /* WINS - ID (0,1,0,0) */
✗ p.text { color: green; }              /* Strikethrough - class+element (0,0,1,1) */
✗ .text { color: red; }                 /* Strikethrough - class (0,0,1,0) */
✗ p { color: blue; }                    /* Strikethrough - element (0,0,0,1) */
```

### DevTools Tip: Hover to See Details

Hover over strikethrough text to see why it's not applied:
- "Overridden by" shows the winning rule
- Specific line number in CSS file

---

## Practice Exercise 2.0.4.1

**Predict the winners**:

For each scenario, predict which color will be applied:

1. 
```css
p { color: blue; }
p.error { color: red; }

<p class="error">Text</p>
```
**Answer**: RED (class has higher specificity)

2.
```css
.button { color: blue; }
.button.primary { color: red; }
.button.primary.large { color: green; }

<button class="button primary large">Click</button>
```
**Answer**: GREEN (most classes = highest specificity)

3.
```css
#header p { color: blue; }
.section p { color: red; }

<div id="header"><p>Text</p></div>
```
**Answer**: BLUE (ID selector = higher specificity)

4.
```css
p { color: blue !important; }
p.error { color: red; }

<p class="error">Text</p>
```
**Answer**: BLUE (!important overrides higher specificity)

5.
```css
.button { color: blue; }
.btn { color: red; }
.button { color: green; }

<button class="button btn">Click</button>
```
**Answer**: GREEN (same specificity, last one wins)

---

## Summary: Module 2.0

You've learned:
- ✅ How the cascade algorithm works
- ✅ How to calculate specificity scores
- ✅ Compare specificity scores
- ✅ Inheritance in CSS
- ✅ Why DevTools shows strikethrough
- ✅ How to predict which CSS wins

**Key Takeaway**: Understanding cascade and specificity lets you predict exactly which CSS rule applies without guessing.

---

## Module 2.1: The CSS Box Model
### Duration: 8 hours | Level: Beginner

---

## Lesson 2.1.1: The Four Layers of the Box Model

Every HTML element is a box with four layers.

### Visual Diagram

```
┌─────────────────────────────────────────┐
│                                         │
│         MARGIN (Orange)                 │
│     (space OUTSIDE the element)         │
│                                         │
│     ┌─────────────────────────────────┐ │
│     │                                 │ │
│     │   BORDER (Yellow/Red)           │ │
│     │   (frame around the element)    │ │
│     │                                 │ │
│     │ ┌─────────────────────────────┐ │ │
│     │ │                             │ │ │
│     │ │ PADDING (Green)             │ │ │
│     │ │ (space INSIDE, with bg)     │ │ │
│     │ │                             │ │ │
│     │ │ ┌──────────────────────────┐│ │ │
│     │ │ │                          ││ │ │
│     │ │ │ CONTENT (Blue)           ││ │ │
│     │ │ │ (your text/images)       ││ │ │
│     │ │ │                          ││ │ │
│     │ │ └──────────────────────────┘│ │ │
│     │ │                             │ │ │
│     │ └─────────────────────────────┘ │ │
│     │                                 │ │
│     └─────────────────────────────────┘ │
│                                         │
└─────────────────────────────────────────┘
```

### What Each Layer Does

| Layer | Purpose | Has Background? | Example |
|-------|---------|-----------------|---------|
| **Content** | Your actual text/images | No (shows element's content) | Text, images |
| **Padding** | Space inside element | YES - respects background | Inner spacing |
| **Border** | Frame around element | Can be styled | 1px solid black |
| **Margin** | Space between elements | No - transparent | Gap between cards |

---

## Lesson 2.1.2: Box Sizing - The Critical Decision

**This ONE decision affects everything** in CSS layout.

### box-sizing: content-box (Default, Confusing)

```css
.box {
    box-sizing: content-box;  /* Default */
    width: 200px;
    padding: 20px;
    border: 2px solid;
}

/* Actual width = 200 + 20 + 20 + 2 + 2 = 244px */
/*                width + padding + border   */
```

**Why it's confusing**:
- You set width: 200px
- But element is actually 244px wide!
- Padding and border get added on top

### box-sizing: border-box (Better)

```css
.box {
    box-sizing: border-box;  /* Modern, predictable */
    width: 200px;
    padding: 20px;
    border: 2px solid;
}

/* Actual width = 200px (padding and border subtracted from content) */
```

**Why it's better**:
- You set width: 200px
- Element is exactly 200px wide
- Padding and border eat into the content area
- Much more predictable

### Global Reset (Use This!)

```css
/* Apply to all elements */
* {
    box-sizing: border-box;
}

/* Now all elements use border-box by default */
```

### Real Example Comparison

**Scenario**: Creating a grid of 3 equal cards

```html
<div class="grid">
    <div class="card">Card 1</div>
    <div class="card">Card 2</div>
    <div class="card">Card 3</div>
</div>
```

**With content-box (PROBLEMATIC)**:
```css
.grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

.card {
    /* DON'T set box-sizing (uses default content-box) */
    width: 100%;         /* Full width of column */
    padding: 20px;       /* Adds to width */
}

/* Result: Cards overflow! */
/* Each card = 100% width + 40px padding = too wide */
```

**With border-box (WORKS PERFECTLY)**:
```css
* {
    box-sizing: border-box;  /* Set globally */
}

.grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

.card {
    width: 100%;         /* Full width of column */
    padding: 20px;       /* Subtracted from width */
}

/* Result: Perfect fit! */
/* Each card = 100% (including padding) */
```

---

## Lesson 2.1.3: Margin Explained

Margin is space OUTSIDE an element. No background color.

### Margin Syntax

```css
/* All four sides */
margin: 20px;

/* Vertical (top/bottom) | Horizontal (left/right) */
margin: 20px 10px;

/* Top | Right | Bottom | Left */
margin: 20px 10px 15px 5px;

/* Individual sides */
margin-top: 20px;
margin-right: 10px;
margin-bottom: 15px;
margin-left: 5px;
```

### Margin Shorthand Breakdown

```css
/* margin: Top Right Bottom Left */
margin: 20px 10px 15px 5px;
margin-top:    20px;  ▲
margin-right:  10px;  ▲
margin-bottom: 15px;  ▲
margin-left:   5px;   ▲

/* Common patterns */
margin: 20px;              /* All sides: 20px */
margin: 20px 10px;         /* Top/bottom: 20px, Left/right: 10px */
margin: 0 auto;            /* Centers element horizontally */
margin: 20px 0;            /* Only top/bottom margin */
```

### Centering with Margin

```css
/* Horizontal center (for block elements) */
.centered {
    width: 300px;
    margin: 0 auto;  /* 0 top/bottom, auto left/right */
}

/* Center in flexible container */
.flex-center {
    display: flex;
    justify-content: center;  /* Better for flex */
}
```

### Negative Margin (Advanced)

```css
/* Negative margin pulls element inward */
.overlap {
    margin-top: -20px;  /* Pulls up 20px */
}

/* Use case: Overlapping elements */
.card-image {
    margin-bottom: -40px;  /* Overlaps the next element */
}

.card-content {
    padding-top: 50px;  /* Make room for overlap */
}
```

---

## Lesson 2.1.4: Padding Explained

Padding is space INSIDE an element. HAS background color.

### Padding Syntax

Same syntax as margin:

```css
/* All four sides */
padding: 20px;

/* Vertical | Horizontal */
padding: 20px 10px;

/* Top | Right | Bottom | Left */
padding: 20px 10px 15px 5px;

/* Individual sides */
padding-top: 20px;
padding-right: 10px;
padding-bottom: 15px;
padding-left: 5px;
```

### Key Difference: Margin vs Padding

```css
.container {
    background: lightblue;
    margin: 20px;      /* Space OUTSIDE (no background) */
    padding: 20px;     /* Space INSIDE (HAS background) */
}
```

**Visual**:
```
┌─────────────────────────────────────┐
│ (20px margin - no color)            │
│  ┌──────────────────────────────────┤
│  │ (20px padding - light blue)      │
│  │  ┌───────────────────────────────┤
│  │  │ Content (text)                │
│  │  │                               │
│  │  └───────────────────────────────┤
│  │                                  │
│  └──────────────────────────────────┤
│                                     │
└─────────────────────────────────────┘
```

### Practical Decision Tree

**Do I want space with color?**
- YES → Use padding
- NO → Use margin

**Do I want space between elements?**
- YES → Use margin (on one element) or gap (if flex/grid)
- NO → Use padding (inside the element)

---

## Lesson 2.1.5: Border Explained

Border is a frame around the padding.

### Border Syntax

```css
/* Style: solid, dashed, dotted, double, groove, ridge, inset, outset */
border: 2px solid black;

/* More specific */
border-width: 2px;
border-style: solid;
border-color: black;

/* Individual sides */
border-top: 2px solid black;
border-right: 1px dashed gray;
border-bottom: 2px solid black;
border-left: none;

/* Border radius (rounded corners) */
border-radius: 4px;
border-radius: 4px 8px;  /* Top-left/bottom-right | Top-right/bottom-left */
border-radius: 50%;      /* Circle */
```

### Border Examples

```css
/* Solid border */
.card {
    border: 1px solid #ccc;
    border-radius: 8px;
}

/* Dashed border */
.outline {
    border: 2px dashed blue;
}

/* Different borders on each side */
.left-accent {
    border-left: 4px solid red;
    border-top: 1px solid #ccc;
    border-right: 1px solid #ccc;
    border-bottom: 1px solid #ccc;
}

/* or shorthand */
.left-accent {
    border: 1px solid #ccc;
    border-left: 4px solid red;
}

/* Circle element */
.avatar {
    width: 100px;
    height: 100px;
    border-radius: 50%;  /* Makes it circular */
}

/* Rounded rectangle */
.button {
    padding: 10px 20px;
    border-radius: 4px;  /* Slightly rounded */
}
```

### Border vs Outline

```css
.border {
    border: 2px solid blue;  /* Part of box model */
    width: 100px;           /* Takes up space */
}

.outline {
    outline: 2px solid red;  /* NOT part of box model */
    width: 100px;            /* Doesn't affect width */
}
```

**When to use**:
- Border: Visual styling
- Outline: Focus indicators (for accessibility)

```css
.button:focus {
    outline: 2px solid blue;  /* Keyboard focus indicator */
    outline-offset: 2px;      /* Gap between outline and element */
}
```

---

## Lesson 2.1.6: Calculating Total Width and Height

This is crucial for layout predictability.

### With box-sizing: content-box (Default)

```
Total Width = content width + padding-left + padding-right + border-left + border-right

Example:
.box {
    width: 200px;
    padding: 20px;
    border: 2px solid;
}

Total = 200 + 20 + 20 + 2 + 2 = 244px
```

### With box-sizing: border-box (Better)

```
Total Width = width (includes padding + border)

Example:
.box {
    box-sizing: border-box;
    width: 200px;
    padding: 20px;
    border: 2px solid;
}

Total = 200px (padding and border subtracted from content area)
```

### Real Scenario: Creating Equal Width Cards

**Problem**: Make 3 equal cards with padding

```html
<div class="container">
    <div class="card">Card 1</div>
    <div class="card">Card 2</div>
    <div class="card">Card 3</div>
</div>
```

**Solution with border-box**:

```css
* {
    box-sizing: border-box;  /* Enable border-box globally */
}

.container {
    width: 900px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

.card {
    width: 100%;          /* Full width of column */
    padding: 20px;        /* Subtracted from width */
    background: white;
    border: 1px solid #ccc;
}

/* Each card: 300px total (including padding) */
/* Content area: 300 - 20 - 20 = 260px */
```

---

## Lesson 2.1.7: Margin Collapsing (Block Elements Only)

This is a CSS feature that confuses many developers.

### What is Margin Collapsing?

Adjacent block elements' margins "collapse" - they don't add together.

```css
/* Without margin collapsing */
.box1 { margin-bottom: 30px; }
.box2 { margin-top: 20px; }

/* You might expect: 30 + 20 = 50px gap */
/* But actually: max(30, 20) = 30px gap */
```

**Visual**:
```
┌──────────────┐
│ Box 1        │ margin-bottom: 30px
└──────────────┘
        ↓ (30px - the larger margin wins)
┌──────────────┐
│ Box 2        │ margin-top: 20px
└──────────────┘
```

### When Does Margin Collapsing Happen?

**Happens With**:
- Adjacent block elements
- Parent and first child (vertical margin)
- Empty elements with margin

**Does NOT Happen With**:
- Inline elements
- Flexbox items
- Grid items
- Absolutely positioned elements
- Elements with overflow: hidden

### Example: When It Happens

```css
h1 { margin-bottom: 30px; }
p { margin-top: 20px; }

/* Gap between h1 and p: 30px (not 50px) */
```

### Example: When It Doesn't

```css
/* With flexbox - NO collapsing */
.container {
    display: flex;
    flex-direction: column;
}

.item1 { margin-bottom: 30px; }
.item2 { margin-top: 20px; }

/* Gap: 30px + 20px = 50px (margins don't collapse) */
```

### How to Prevent Margin Collapsing

**Option 1: Use Flexbox** (Recommended)
```css
.container {
    display: flex;
    flex-direction: column;
    gap: 20px;  /* Cleaner than margins */
}
```

**Option 2: Add Padding to Parent**
```css
.container {
    padding-top: 1px;  /* Prevents collapsing */
}
```

**Option 3: Add Overflow**
```css
.container {
    overflow: hidden;  /* Creates new block formatting context */
}
```

**Option 4: Use `border-collapse` CSS**
```css
.container {
    border: 1px solid transparent;  /* Prevents collapsing */
}
```

---

## Practice Exercise 2.1.7.1

**Debug These Box Model Issues**:

1. **Cards are too wide**
```css
.grid { display: grid; grid-template-columns: repeat(3, 300px); gap: 20px; }
.card { width: 300px; padding: 20px; }

/* Why are cards wider than 300px? Fix it. */
```
**Answer**: Cards are 300px + 40px (padding) = 340px
**Fix**: `* { box-sizing: border-box; }`

2. **Spacing between elements looks weird**
```css
.list { display: flex; flex-direction: column; }
.item { margin: 20px; }
```

**What's the gap between items?**
**Answer**: 40px (margins don't collapse in flexbox, they add)
**Fix**: Use `gap: 20px;` instead of `margin`

3. **Vertical spacing wrong with block elements**
```css
h1 { margin-bottom: 30px; }
p { margin-top: 20px; }

/* Gap between h1 and p? */
```
**Answer**: 30px (margin collapsing - larger margin wins)
**Fix**: Use flexbox with gap, or accept the behavior

---

## Summary: Module 2.1

You've learned:
- ✅ The four layers: content, padding, border, margin
- ✅ box-sizing: content-box vs border-box
- ✅ When to use margin vs padding
- ✅ Border styling and radius
- ✅ How to calculate total width
- ✅ Margin collapsing and how to prevent it

**Key Takeaway**: Always use `box-sizing: border-box` globally. It makes width calculations predictable.

---

## Module 2.2: Display Property & Box Model Effects
### Duration: 12 hours | Level: Beginner to Intermediate

This module shows how the display property CHANGES how box model properties work.

---

## Lesson 2.2.1: display: block

Block elements take the full width of their container.

### Characteristics

```css
display: block;

/* Behavior */
└─ Takes 100% width of parent
└─ Forces new line before and after
└─ Respects ALL margins (top, right, bottom, left) ✅
└─ Respects ALL padding ✅
└─ Respects width and height ✅
└─ Margins collapse vertically ⚠️
```

### Examples of Block Elements

```html
<div>      <!-- Block by default -->
<p>        <!-- Block by default -->
<h1>-<h6> <!-- Block by default -->
<section>  <!-- Block by default -->
<header>   <!-- Block by default -->
<footer>   <!-- Block by default -->
```

### Code Example

```html
<style>
    .box {
        display: block;
        width: 200px;
        margin: 20px;
        padding: 20px;
        background: lightblue;
    }
</style>

<div class="box">Block Element 1</div>
<div class="box">Block Element 2</div>
```

**Result**:
```
┌──────────────────────────────────────┐
│ ┌────────────────────────────────────┤ (20px margin)
│ │ BLOCK ELEMENT 1                    │
│ └────────────────────────────────────┤
│                                      │
│                  (30px gap - margin collapse)
│
│ ┌────────────────────────────────────┤ (20px margin)
│ │ BLOCK ELEMENT 2                    │
│ └────────────────────────────────────┤
└──────────────────────────────────────┘
```

### Centering Block Elements

```css
.centered {
    width: 300px;
    margin: 0 auto;  /* Horizontal center */
}
```

---

## Lesson 2.2.2: display: inline

Inline elements flow with text. Only left/right margins work.

### Characteristics

```css
display: inline;

/* Behavior */
└─ Takes only necessary width (content width)
└─ Flows with text (no new line)
└─ Respects LEFT/RIGHT margins only ✅
└─ Respects TOP/BOTTOM margins ❌ (IGNORED!)
└─ Respects LEFT/RIGHT padding ✅
└─ Respects TOP/BOTTOM padding ⚠️ (works but weird overlap)
└─ Width and height IGNORED ❌
└─ NO margin collapsing
```

### Examples of Inline Elements

```html
<span>       <!-- Inline by default -->
<a>          <!-- Inline by default -->
<strong>     <!-- Inline by default -->
<em>         <!-- Inline by default -->
<button>     <!-- Sometimes inline -->
```

### Code Example

```html
<style>
    .inline {
        display: inline;
        width: 200px;        /* IGNORED */
        height: 100px;       /* IGNORED */
        margin-top: 20px;    /* IGNORED */
        margin-left: 10px;   /* WORKS */
        padding: 20px;       /* ⚠️ Works but overlap */
        background: lightblue;
    }
</style>

<span class="inline">Inline 1</span>
<span class="inline">Inline 2</span>
```

**Result**:
```
Inline 1      Inline 2  (flows on same line)
└─ 10px margin (left only)
```

### The Problem: margin-top on Inline

```css
span {
    display: inline;
    margin-top: 20px;  /* DOESN'T WORK! */
}
```

In DevTools, you'd see:
```
✓ margin-top: 20px;  (strikes through in gray - not applied)
```

**Why?** Inline elements only respect left/right margins. Top/bottom are ignored.

**Fix**:
```css
span {
    display: inline-block;  /* Change to inline-block */
    margin-top: 20px;       /* NOW IT WORKS */
}
```

---

## Lesson 2.2.3: display: inline-block

Hybrid: flows inline but respects full box model.

### Characteristics

```css
display: inline-block;

/* Behavior */
└─ Flows inline (doesn't create new line)
└─ BUT respects full box model
└─ Respects ALL margins (top, right, bottom, left) ✅
└─ Respects ALL padding ✅
└─ Respects width and height ✅
└─ NO margin collapsing
└─ Whitespace in HTML creates gaps ⚠️
```

### Code Example

```html
<style>
    .inline-block {
        display: inline-block;
        width: 150px;
        margin: 10px;
        padding: 20px;
        background: lightblue;
    }
</style>

<button class="inline-block">Save</button>
<button class="inline-block">Cancel</button>
```

**Result**:
```
┌─────────────────┐  ┌─────────────────┐
│ Save (10px gap) │  │ Cancel (10px gap) │
└─────────────────┘  └─────────────────┘
```

### The Whitespace Problem

```html
<button class="inline-block">Save</button>
<button class="inline-block">Cancel</button>
```

Creates a gap because of the whitespace between tags in HTML!

```
Space in HTML:
</button>  <button>
      ↑
    This creates a gap
```

**Solutions**:

**Option 1: Remove whitespace**
```html
<button class="inline-block">Save</button><button class="inline-block">Cancel</button>
```

**Option 2: Use flexbox** (Modern, recommended)
```css
.button-group {
    display: flex;
    gap: 10px;
}
```

**Option 3: Font-size: 0 on parent**
```css
.button-group {
    font-size: 0;  /* Removes whitespace gap */
}

.button-group button {
    display: inline-block;
    font-size: 16px;  /* Reset font size */
}
```

### When to Use inline-block

- Buttons (sometimes)
- Badges
- Inline images
- When flexbox isn't available (older browsers)

**Modern recommendation**: Use flexbox instead.

---

## Lesson 2.2.4: display: flex (NEW BOX MODEL!)

Flexbox is a new layout mode. Margin/padding work differently here.

### Characteristics

```css
display: flex;

/* Container behavior */
└─ Children become flex items
└─ Children no longer affect sibling margins
└─ Margin on children works for spacing
└─ Margin: auto centers item! ✨
└─ NO margin collapsing
└─ Gap property for clean spacing
```

### Container Properties

```css
.flex-container {
    display: flex;
    
    /* Direction of items */
    flex-direction: row;              /* left to right (default) */
    flex-direction: column;           /* top to bottom */
    flex-direction: row-reverse;      /* right to left */
    flex-direction: column-reverse;   /* bottom to top */
    
    /* Spacing along main axis */
    justify-content: flex-start;      /* Items at start */
    justify-content: center;          /* Items centered */
    justify-content: space-between;   /* Items spread out */
    justify-content: space-around;    /* Items with space around */
    justify-content: space-evenly;    /* Items with equal space */
    
    /* Alignment on cross axis */
    align-items: flex-start;          /* Items at start */
    align-items: center;              /* Items centered */
    align-items: stretch;             /* Items full height */
    
    /* Handle wrapping */
    flex-wrap: nowrap;                /* Single line (default) */
    flex-wrap: wrap;                  /* Multiple lines */
    flex-wrap: wrap-reverse;          /* Wrap but reverse */
    
    /* Space between items */
    gap: 20px;                        /* Between flex items */
    gap: 20px 10px;                   /* row-gap, column-gap */
}
```

### Code Example

```html
<style>
    .flex-container {
        display: flex;
        gap: 20px;
        padding: 20px;
        background: lightgray;
    }
    
    .flex-item {
        flex: 1;             /* Grow equally */
        padding: 20px;
        background: lightblue;
    }
</style>

<div class="flex-container">
    <div class="flex-item">Item 1</div>
    <div class="flex-item">Item 2</div>
    <div class="flex-item">Item 3</div>
</div>
```

**Result**: Three equal-width items with 20px gap between them

### The Magic: margin: auto in Flexbox

```css
.flex-container {
    display: flex;
    width: 300px;
    height: 300px;
    background: lightgray;
}

.flex-item {
    width: 100px;
    height: 100px;
    margin: auto;  /* CENTERS BOTH AXES! */
    background: blue;
}
```

**Result**: Item centered both horizontally AND vertically

### Spacing in Flexbox

```css
/* Option 1: Gap (recommended) */
.container {
    display: flex;
    gap: 20px;  /* Space between items */
}

/* Option 2: Margin (works but less clean) */
.container {
    display: flex;
}

.item {
    margin: 10px;  /* Space around each item */
}

/* Option 3: Margin to push item */
.container {
    display: flex;
}

.item:last-child {
    margin-left: auto;  /* Pushes last item to right */
}
```

---

## Lesson 2.2.5: display: grid (2D LAYOUT!)

Grid is for 2-dimensional layouts. Like a spreadsheet.

### Characteristics

```css
display: grid;

/* Container behavior */
└─ Children become grid items
└─ Define rows and columns
└─ Place items in cells
└─ Margin/padding work normally
└─ NO margin collapsing
└─ Gap for clean spacing
```

### Container Properties

```css
.grid-container {
    display: grid;
    
    /* Define columns */
    grid-template-columns: 200px 300px 200px;  /* Fixed sizes */
    grid-template-columns: 1fr 2fr 1fr;         /* Fractions */
    grid-template-columns: repeat(3, 1fr);      /* Repeat 3 times */
    grid-template-columns: repeat(auto-fit, 300px);  /* Responsive */
    
    /* Define rows */
    grid-template-rows: 100px 200px;   /* Fixed sizes */
    grid-auto-rows: auto;               /* Auto size */
    
    /* Space between cells */
    gap: 20px;                          /* All gaps */
    gap: 20px 10px;                     /* row-gap, column-gap */
    
    /* Alignment */
    align-items: center;    /* Align items in cells */
    justify-items: center;  /* Justify items in cells */
}
```

### Code Example

```html
<style>
    .grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        padding: 20px;
    }
    
    .grid-item {
        padding: 20px;
        background: lightblue;
        border: 1px solid #ccc;
    }
</style>

<div class="grid">
    <div class="grid-item">Item 1</div>
    <div class="grid-item">Item 2</div>
    <div class="grid-item">Item 3</div>
    <div class="grid-item">Item 4</div>
    <div class="grid-item">Item 5</div>
    <div class="grid-item">Item 6</div>
</div>
```

**Result**: 2 rows × 3 columns grid with 20px gaps

### Responsive Grid

```css
/* Desktop: 3 columns */
@media (min-width: 1024px) {
    .grid {
        grid-template-columns: repeat(3, 1fr);
    }
}

/* Tablet: 2 columns */
@media (min-width: 768px) and (max-width: 1023px) {
    .grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Mobile: 1 column */
@media (max-width: 767px) {
    .grid {
        grid-template-columns: 1fr;
    }
}

/* Or use auto-fit for automatic responsiveness */
.grid {
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    /* At least 300px per column, auto-fit to container */
}
```

---

## Lesson 2.2.6: Quick Reference - Box Model by Display Type

This is your quick lookup table:

```
┌────────────────┬───────────────┬───────────────┬────────────────┬──────────────┐
│ Display Type   │ Margin Top/Bot│ Margin L/R    │ Padding All    │ Width/Height │
├────────────────┼───────────────┼───────────────┼────────────────┼──────────────┤
│ block          │ ✅ Works      │ ✅ Works      │ ✅ Works       │ ✅ Works     │
│ inline         │ ❌ Ignored    │ ✅ Works      │ ⚠️ Works       │ ❌ Ignored   │
│ inline-block   │ ✅ Works      │ ✅ Works      │ ✅ Works       │ ✅ Works     │
│ flex           │ ✅ Works      │ ✅ Works      │ ✅ Works       │ ✅ Works     │
│ grid           │ ✅ Works      │ ✅ Works      │ ✅ Works       │ ✅ Works     │
└────────────────┴───────────────┴───────────────┴────────────────┴──────────────┘

Additional:
- block/inline-block: Margin collapsing happens
- flex/grid: Margin collapsing DOES NOT happen
- flex: margin: auto centers item
- flex/grid: Use gap for spacing (cleaner than margin)
```

---

## Summary: Module 2.2

You've learned:
- ✅ How display: block works (full width, all margins)
- ✅ How display: inline works (content width, left/right margin only)
- ✅ How display: inline-block works (hybrid)
- ✅ How display: flex works (NEW box model, margin: auto magic)
- ✅ How display: grid works (2D layout)
- ✅ When to use each display type

**Key Takeaway**: The display property fundamentally changes how margin, padding, and width work. Understanding this is crucial.

---

## Practice Exercise 2.2.6.1

**For each HTML snippet, predict the result**:

1. 
```css
span { margin-top: 20px; }
```
Will the margin-top apply?
**Answer**: NO (inline elements ignore top margin)

2.
```css
.flex { display: flex; }
.item { margin: 20px; }
```
What's the gap between items?
**Answer**: 40px (margins don't collapse in flex, they add)

3.
```css
.flex { display: flex; }
.item { margin: auto; }
```
What happens to the item?
**Answer**: Item centers both horizontally AND vertically

4.
```css
div { width: 300px; padding: 20px; }
```
What's the actual width?
**Answer**: Depends on box-sizing
- content-box (default): 340px
- border-box: 300px

---

## Module 2.3: Inspector Debugging (Masterclass)
### Duration: 6 hours | Level: Intermediate

Now you know the fundamentals. Let's use DevTools to debug like a pro.

---

## Lesson 2.3.1: Opening and Using DevTools

### Opening DevTools

**Windows/Linux**:
- F12
- Ctrl+Shift+I
- Right-click → Inspect

**Mac**:
- Cmd+Option+I
- Cmd+Shift+I (sometimes)
- Right-click → Inspect

### The Elements Tab

When you open DevTools, you're in the Elements (or Inspector) tab.

```
┌─────────────────────────────────────────────────────────────┐
│ Elements | Console | Sources | Network | ...                │
├─────────────────────────────────────────────────────────────┤
│ │ HTML Tree (left)         │ Styles Panel (right)            │
│ │                          │                                 │
│ │ <html>                   │ Styles for selected element     │
│ │   <head>...              │ ✓ color: red;                   │
│ │   <body>                 │ ✗ color: blue; (strikethrough)  │
│ │     <div class="box">    │                                 │
│ │       Content            │ Box Model Tab (below)            │
│ │     </div>   ← Selected  │ ┌─────────────────────────────┐ │
│ │                          │ │ Margin/Padding/Border viz  │ │
│ └──────────────────────────┴─────────────────────────────────┘
```

### The Element Picker

```
Chrome DevTools has an "Element Picker" button (arrow icon top-left).
Click it, then click element on page to select it.

Keyboard: Ctrl+Shift+C (Windows) or Cmd+Shift+C (Mac)
```

---

## Lesson 2.3.2: Reading the Styles Panel

The Styles panel shows all CSS rules for the selected element.

### Understanding Strikethrough

```
✓ color: red;           /* APPLIED - this rule is active */
✗ color: blue;          /* STRIKETHROUGH - overridden */
```

**Why strikethrough?** Either:
1. Lower specificity (higher specificity rule won)
2. Earlier in file (later rule with same specificity won)
3. Different selector (this rule doesn't match)

### Hover to See Details

When you hover over strikethrough text in DevTools, it shows:
```
"Overridden by [filename.css:42]"
```

This shows you exactly which rule is beating this one.

### Pseudo-Classes and Pseudo-Elements

DevTools shows styles for different states:

```
h1 {}
h1:hover {}
h1:focus {}
h1::before {}
```

You can see styles for each state separately.

---

## Lesson 2.3.3: Reading the Box Model Tab

The Box Model tab shows visual representation of margin/padding/border.

### Visual Breakdown

```
┌──────────────────────────────────────────┐
│ MARGIN (orange/tan)            20px      │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ BORDER (tan/red)               2px   │ │
│ │ ┌──────────────────────────────────┐ │ │
│ │ │ PADDING (green)           10px   │ │ │
│ │ │ ┌──────────────────────────────┐ │ │ │
│ │ │ │ CONTENT (blue)    300x100    │ │ │ │
│ │ │ └──────────────────────────────┘ │ │ │
│ │ └──────────────────────────────────┘ │ │
│ └──────────────────────────────────────┘ │
│                                          │
└──────────────────────────────────────────┘

Calculations shown:
Total Width = 300 + 10 + 10 + 2 + 2 + 20 + 20 = 364px
```

### Hovering Over Box Model

When you hover over each section:
- **Margin (orange)**: Highlights margin area on page
- **Border (red)**: Highlights border area
- **Padding (green)**: Highlights padding area
- **Content (blue)**: Highlights content area

This helps visualize what each property does.

### Reading Numbers

The box model shows exact pixel values:
- Top, Right, Bottom, Left for each property
- Total dimensions

---

## Lesson 2.3.4: Debugging Common Issues

### Issue 1: "Why is my spacing wrong?"

**Steps**:
1. Inspect element with wrong spacing
2. Look at Box Model tab
3. Check if margins are what you expected
4. Check if padding is correct
5. For multiple elements, check if margin collapsing is happening

**Example**:
```css
h1 { margin-bottom: 30px; }
p { margin-top: 20px; }
/* Expected gap: 50px
   Actual gap: 30px (margin collapse)
   
   DevTools shows: Box model of h1 has 30px bottom margin
                   Box model of p has 20px top margin
                   But visual gap is only 30px
```

### Issue 2: "Why is my width/height wrong?"

**Steps**:
1. Inspect element
2. Look at Styles panel for width/height
3. Look at Box Model tab
4. Check box-sizing property
5. Calculate: Is it content-box or border-box?

**Example**:
```css
.box {
    width: 200px;
    padding: 20px;
    border: 2px solid;
    /* Actual width = ? */
}

In DevTools Box Model:
- Content: 200px
- Padding: 20px each side
- Border: 2px each side
- Total: 200 + 40 + 4 = 244px

If you expected 200px, check box-sizing!
```

### Issue 3: "Why won't margin-top work?"

**Steps**:
1. Inspect element
2. Look at display type
3. If display: inline, that's the problem!
4. Check Styles panel - margin-top will be strikethrough/grayed out

**Example**:
```css
span {
    margin-top: 20px;  /* Won't work */
}

In DevTools:
display: inline  ← Ah! inline elements ignore top margin
margin-top: 20px;  (grayed out - not applied)

Fix: Change to display: inline-block;
```

### Issue 4: "Why is z-index not working?"

**Steps**:
1. Inspect element
2. Look at position property
3. If position: static, that's the problem!
4. z-index only works with position != static

**Example**:
```css
.overlay {
    position: static;  ← Problem here
    z-index: 100;      /* Won't work without position */
}

In DevTools:
z-index: 100;  (likely grayed out - not applied)
position: static  ← This is why

Fix: Add position: relative;
```

### Issue 5: "Elements are misaligned"

**Steps**:
1. Inspect parent container
2. Check if it's flex or grid
3. If flex/grid, check justify-content and align-items
4. If not flex/grid, elements may not align properly

**Example**:
```css
.container {
    display: flex;  ← Good, it's a flex container
}

.item {
    /* Will be aligned by parent's align-items */
}

In DevTools:
Check .container's align-items property
If not set, items will align to default (stretch)
```

---

## Lesson 2.3.5: Live Editing in DevTools

You can edit CSS in DevTools and see changes in real-time!

### How to Edit

1. Right-click CSS property in Styles panel
2. Click "Edit as Text" or double-click value
3. Type new value
4. Press Enter
5. See result instantly!

### Workflow

```
1. See problem on page
2. Inspect element (Ctrl+Shift+C)
3. Double-click value in Styles panel
4. Try different values
5. When it looks good, copy value
6. Paste into your actual CSS file
```

### Example Session

```
Problem: Button padding is wrong

1. Inspect button
2. See: padding: 5px 10px;
3. Double-click the "5" (padding-top)
4. Change to "12"
5. Press Enter - see it change instantly
6. Try different values until happy
7. Copy from DevTools, paste into CSS
```

### Screenshot in DevTools

DevTools can take screenshots:
```
Hamburger menu (⋮) → More tools → Screenshot
Or: Ctrl+Shift+P → "Screenshot"
```

This helps document correct styling before/after.

---

## Lesson 2.3.6: The Debugging Workflow

When CSS looks wrong, follow this systematic approach:

### Step 1: Identify the Problem
- What looks wrong?
- Is it spacing, size, color, position, or alignment?

### Step 2: Inspect the Element
- Open DevTools
- Click element picker
- Click the element with problem

### Step 3: Check Display Type
- Look at display property
- Does margin/padding work with this display type?

### Step 4: Check Box Model
- Look at Box Model tab
- Verify padding/border/margin values
- Calculate total width/height if needed

### Step 5: Check Specificity
- Look at Styles panel
- Any strikethrough rules?
- Is a higher specificity rule winning?

### Step 6: Check Parent Context
- If flex/grid parent, check justify-content/align-items
- If absolute positioned, check position: relative on parent
- Check for overflow: hidden

### Step 7: Live Edit to Test
- Double-click values in DevTools
- Try different values
- Once fixed, copy to CSS file

### Step 8: Verify in CSS File
- Make sure change is actually in your CSS
- Not just in DevTools (changes revert on refresh!)

---

## Practice Exercise 2.3.6.1

**Debug These Live Issues**:

Use Chrome DevTools on any website:

1. **Find an element with wrong spacing**
   - Inspect it
   - Check Box Model
   - Identify: is it margin, padding, or border?
   - Try changing it in DevTools
   - Document what you found

2. **Find an element with strikethrough CSS**
   - Inspect element
   - Find CSS rules with strikethrough
   - Identify why (specificity or source order)
   - Hover to see which rule is winning
   - Document the specificity scores

3. **Find an inline element**
   - Inspect it
   - Verify it has display: inline
   - Check if it has margin-top (should be ignored)
   - Document what you discover

---

## Summary: Week 2

You've learned:
- ✅ CSS cascade and how rules resolve
- ✅ CSS specificity scoring system
- ✅ Box model (margin, padding, border, content)
- ✅ box-sizing: content-box vs border-box
- ✅ How display type affects box model
- ✅ block, inline, inline-block, flex, grid
- ✅ DevTools debugging like a pro
- ✅ Reading Styles and Box Model tabs
- ✅ Live editing CSS in DevTools
- ✅ Systematic debugging workflow

**Key Deliverables**:
1. Understand specificity deeply
2. Know box model calculations
3. Know which margins/padding work with each display
4. Debug CSS issues using DevTools

**Next Week**: CSS Styling & Design Patterns (applying these fundamentals!)

---

## Week 2 Practical Project: Build and Debug a Component

### Project: Build a "Card Component" and Debug It

Create a card component with:
- Image (top)
- Title
- Description
- Button
- Proper spacing using margins, padding, gaps
- Responsive sizing
- Hover effects

### Requirements

**HTML**:
```html
<div class="card">
    <img src="image.jpg" alt="..." class="card-image">
    <div class="card-content">
        <h3 class="card-title">Card Title</h3>
        <p class="card-description">Card description text goes here.</p>
        <button class="card-button">Learn More</button>
    </div>
</div>
```

**CSS**:
- Use box-sizing: border-box
- Define spacing using CSS variables
- Use flexbox for layout
- Document all measurements
- Make it responsive

### Deliverables

```
week-2-project/
├── index.html
├── styles.css
├── README.md (specs document)
└── screenshot.png (from DevTools)
```

### What to Document

1. All measurements (width, padding, margin)
2. Why you chose each spacing value
3. Why you chose flex vs other display types
4. DevTools screenshot showing box model
5. What you learned about margin collapsing or other gotchas

This project solidifies your understanding of the box model and display types.

---

**End of Week 2 Content**

Next: Week 3 - CSS Styling & Design Patterns (continuing...)
