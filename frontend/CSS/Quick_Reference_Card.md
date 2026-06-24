# 📋 CSS & Inspector Quick Reference Card
## Print This. Keep It Handy. Use Daily.

---

## CSS SPECIFICITY QUICK CALC

```
Specificity = [a, b, c, d]

| Selector              | Score    | Example |
|--------------------|----------|---------|
| Inline style       | 1,0,0,0  | style="..." |
| ID                 | 0,1,0,0  | #header |
| Class/Attribute    | 0,0,1,0  | .button, [type] |
| Element/Pseudo     | 0,0,0,1  | div, ::before |

Higher [a] always wins first.
Then higher [b], then [c], then [d].
Source order wins if all equal.
!important overrides everything.
```

---

## BOX MODEL AT A GLANCE

```
Margin (outside, no bg) → space between elements
    ↓
Border → frame around element
    ↓
Padding (inside, has bg) → space inside element
    ↓
Content → your text/images

Total Width = width + padding + border (if border-box)
              width alone (if content-box)

DEFAULT: box-sizing: content-box (confusing!)
ALWAYS USE: box-sizing: border-box (predictable!)
```

---

## DISPLAY TYPE QUICK REFERENCE

```
┌─────────────┬─────────┬─────────┬────────────┬──────────┐
│ Display     │ Margin  │ Padding │ Width/Ht   │ Collapse │
│             │ Top/Bot │ All 4   │            │ Margins? │
├─────────────┼─────────┼─────────┼────────────┼──────────┤
│ block       │ ✅      │ ✅      │ ✅         │ YES      │
│ inline      │ ❌      │ ⚠️      │ ❌         │ NO       │
│ inline-blk  │ ✅      │ ✅      │ ✅         │ NO       │
│ flex        │ ✅      │ ✅      │ ✅         │ NO       │
│ grid        │ ✅      │ ✅      │ ✅         │ NO       │
└─────────────┴─────────┴─────────┴────────────┴──────────┘

KEY: ✅=Works | ❌=Ignored | ⚠️=Works but might be weird
```

---

## COMMON PROBLEMS & QUICK FIXES

```
PROBLEM: Inline element margin-top doesn't work
FIX: display: inline-block;

PROBLEM: Element wider than expected
FIX: * { box-sizing: border-box; }

PROBLEM: Two block elements have gap of 30px not 50px
FIX: Use flexbox instead, or prevent collapsing with overflow

PROBLEM: Absolute positioned element in wrong place
FIX: Add position: relative; to parent

PROBLEM: z-index not working
FIX: Add position: relative; (or any non-static value)

PROBLEM: Flex items not evenly spaced
FIX: gap: 20px; (better than margin)

PROBLEM: Vertical alignment weird with inputs + buttons
FIX: Set explicit height, align-items: center on flex parent

PROBLEM: Overflow scrolling doesn't work
FIX: Check parent overflow: hidden, use flexbox instead
```

---

## INSPECTOR KEYBOARD SHORTCUTS

```
Open DevTools
├─ Windows/Linux: F12 or Ctrl+Shift+I
├─ Mac: Cmd+Option+I
└─ Right-click: Inspect Element

Toggle Element Picker
├─ Windows/Linux: Ctrl+Shift+C
├─ Mac: Cmd+Shift+C
└─ Click arrow icon in DevTools

Console Tab: Ctrl+Shift+J (or Cmd+Shift+J)
Elements Tab: Ctrl+Shift+I (or Cmd+Shift+I)
Styles Tab: In Elements, right panel
Box Model Tab: Bottom of Styles panel

View Computed Styles
├─ Elements tab > Computed tab (bottom)
├─ See all styles being applied
└─ Filter by property name
```

---

## READING THE BOX MODEL TAB

```
┌──────────────────────────────────────┐
│ MARGIN (orange outside)         20px │
│ ┌────────────────────────────────────┤
│ │ BORDER (yellow/tan)           2px  │
│ │ ┌──────────────────────────────────┤
│ │ │ PADDING (green inside)      10px │
│ │ │ ┌────────────────────────────────┤
│ │ │ │ CONTENT (blue)         300x100 │
│ │ │ └────────────────────────────────┤
│ │ └──────────────────────────────────┤
│ └────────────────────────────────────┤
└──────────────────────────────────────┘

What it means:
- Margin creates space around element
- Border is the frame
- Padding adds space inside (WITH background color)
- Content is actual text/images

Total width = 300 + 10 + 10 + 2 + 2 + 20 + 20 = 364px
```

---

## DEBUGGING CHECKLIST (IN ORDER)

When something looks wrong:

- [ ] **1. Inspect the element** (Ctrl+Shift+C)
- [ ] **2. Look at display type** (block/inline/flex/grid?)
- [ ] **3. Check margins** (Does this display type support it?)
- [ ] **4. Check padding** (Expected space inside?)
- [ ] **5. Check borders** (Adding to width?)
- [ ] **6. Check box-sizing** (border-box or content-box?)
- [ ] **7. Look for strikethrough** (Overridden by higher specificity?)
- [ ] **8. Check position property** (static/relative/absolute/fixed?)
- [ ] **9. Look at parent** (What's the layout context?)
- [ ] **10. Check gap property** (Using flex/grid with gap?)

---

## ANIMATION TIMING CHEAT SHEET

```
Hover states:        0.2-0.3s (snappy)
Page transitions:    0.3-0.5s (smooth)
Entrance animation:  0.4-0.6s (graceful)
Complex animation:   0.6-1.0s (max comfortable)
Anything over 1s:    Feels slow

Timing functions:
- ease-out:   Things slow down (entering feels good)
- ease-in:    Things speed up (leaving feels good)
- ease-in-out: Smooth S-curve (most natural)
- linear:     Same speed (for spinners, etc.)

Better to use: cubic-bezier() for precise control
```

---

## FLEXBOX CHEAT SHEET

```
Main Container:
.flex-container {
    display: flex;
    
    /* Direction of items */
    flex-direction: row; /* or column */
    
    /* Space along main axis */
    justify-content: center; /* start, end, space-between, space-around */
    
    /* Space on cross axis */
    align-items: center; /* start, end, stretch, center */
    
    /* Wrap to new line */
    flex-wrap: wrap; /* or nowrap, wrap-reverse */
    
    /* Space between rows */
    gap: 20px; /* Cleaner than margin */
}

Flex Items:
.flex-item {
    /* Grow to fill space */
    flex: 1; /* Equal share */
    flex: 2; /* Double share */
    
    /* Or specific: */
    flex: 0 0 100px; /* don't grow, fixed 100px */
    
    /* Magic: centers item */
    margin: auto;
    
    /* Push to side */
    margin-left: auto; /* Pushes right */
    margin-right: auto; /* Pushes left */
}
```

---

## GRID CHEAT SHEET

```
Main Container:
.grid-container {
    display: grid;
    
    /* Define columns */
    grid-template-columns: 1fr 2fr 1fr; /* 3 cols, ratios */
    grid-template-columns: repeat(3, 1fr); /* 3 equal cols */
    grid-template-columns: repeat(auto-fit, 300px); /* Responsive */
    
    /* Define rows */
    grid-template-rows: 100px 200px; /* Fixed heights */
    grid-auto-rows: auto; /* Auto height */
    
    /* Space between cells */
    gap: 20px; /* Same as row-gap + column-gap */
    row-gap: 20px;
    column-gap: 10px;
    
    /* Alignment */
    align-items: center; /* Cross axis */
    justify-items: center; /* Main axis */
    place-items: center; /* Both */
}

Grid Items:
.grid-item {
    /* Span multiple cells */
    grid-column: span 2; /* 2 columns wide */
    grid-row: span 3; /* 3 rows tall */
}
```

---

## POSITIONING QUICK GUIDE

```
position: static       → Default, ignores top/left/etc
position: relative    → Offset from normal position, takes space
position: absolute    → Out of flow, relative to nearest positioned parent
position: fixed       → Out of flow, relative to viewport
position: sticky      → Hybrid relative/fixed

When using position: absolute:
- Parent MUST have position: relative (or other non-static)
- Without it: positioned to document instead of parent
```

---

## RESPONSIVE BREAKPOINTS (COMMON)

```
Mobile:      0px - 480px
Tablet:      481px - 768px
Desktop:     769px - 1024px
Large:       1025px - 1440px
XL:          1441px+

In CSS:
@media (min-width: 768px) { /* Tablet and up */ }
@media (min-width: 1024px) { /* Desktop and up */ }

In Tailwind:
sm: 640px
md: 768px
lg: 1024px
xl: 1280px
2xl: 1536px

Mobile-first approach:
Start with mobile styles, add media queries for larger screens.
```

---

## ACCESSIBILITY QUICK CHECKLIST

```
Colors:
- Text vs background contrast ≥ 4.5:1 (WCAG AA)
- Use https://webaim.org/resources/contrastchecker/

Typography:
- Minimum 16px font for body text
- Line height ≥ 1.5 for readability
- Maximum 75 characters per line

Spacing:
- Touch targets minimum 44×44 pixels
- Enough space between clickable elements

Keyboard:
- Tab through page (can reach everything?)
- Focus indicator visible (not transparent)
- Can you use without mouse?

Motion:
- Respect prefers-reduced-motion
- No animation should distract or cause seizures

Images:
- Every img has alt text (describe content)
- Don't use image for text (use CSS instead)
```

---

## DEBUGGING FLOW (VISUAL)

```
Something looks wrong
        ↓
Open DevTools (F12)
        ↓
Click element (Ctrl+Shift+C)
        ↓
Check Box Model tab
        ↓
Does margin/padding look right?
├─ NO → Check display type
│       └─ Is top/bottom margin on inline? Change to inline-block
│
├─ NO → Check width calculation
│       └─ Is content-box? Change to border-box
│
├─ NO → Check parent layout
│       └─ Is it flex/grid? Use gap instead of margin
│
└─ YES → Check Styles panel
         └─ Is CSS rule struck through?
            └─ Is there higher specificity rule?
```

---

## MOST IMPORTANT MINDSET

```
Before debugging:
"Why is this not working?"

Better mindset:
"What CSS rule am I applying?
 What does that rule do?
 Is that what I expected?"

Even better:
Use DevTools to see EXACTLY what CSS is applied.
Read it. Understand it. Fix it.

Pro level:
Inspect websites constantly.
Try to predict what CSS they're using.
Verify with DevTools.
This builds intuition.
```

---

## RESOURCES YOU'LL USE CONSTANTLY

```
MDN CSS Reference
→ https://developer.mozilla.org/en-US/docs/Web/CSS

Specificity Calculator
→ https://specificity.keegan.st/

Contrast Checker
→ https://webaim.org/resources/contrastchecker/

Easing Functions
→ https://easings.net/

Your Browser DevTools
→ F12 (built in, always available)

Tailwind Docs
→ https://tailwindcss.com/docs

Motion Docs
→ https://motion.dev/
```

---

## PRINT THESE 3 THINGS

1. **Box Model Diagram** (above)
2. **Display Type Table** (above)
3. **Common Problems & Fixes** (above)

Tape them to your monitor for week 1-4. You'll reference constantly.

---

**Keep this page open while learning. Refer to it constantly.**

**Memorize by repetition, not cramming. You'll use these daily.**
