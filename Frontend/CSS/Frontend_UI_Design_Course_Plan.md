# Professional Frontend UI/UX Design Course Plan
## Target: Senior Software Engineer → Frontend Design Pro
### Duration: 8 Weeks | 40 Hours/Week | Learn-by-Doing Approach

---

## COURSE OVERVIEW

You'll master the complete frontend design ecosystem:
- **Vanilla CSS** fundamentals + **Tailwind CSS** utility-first workflow
- **Design thinking**: color theory, typography, spacing, hierarchy
- **Layout systems**: Flexbox, Grid, positioning with real-world patterns
- **Animations**: Pure CSS → Framer Motion (formerly Motion) in React
- **Figma-to-Code**: Extract specs and translate designs pixel-perfectly
- **Accessibility**: WCAG 2.2 standards, responsive design, inclusive UX
- **Design trends**: Glassmorphism, Neumorphism, modern UI patterns
- **Real projects**: Portfolio site with wow animations + component library

---

## COURSE STRUCTURE (8 Weeks)

### **Week 1: Design Fundamentals & Figma Mastery**
**Goals**: Understand design thinking, extract specs from Figma like a pro

#### Module 1.1: Design Thinking & Color Theory (10 hours)
- **Color Psychology & Theory**
  - Color wheel: complementary, analogous, triadic schemes
  - Emotion mapping: reds = urgency, blues = trust, greens = growth
  - 60-30-10 color rule: dominant (60%), secondary (30%), accent (10%)
  - Dark mode & light mode design considerations
  
- **Key Resources**:
  - MDN Color & Web Design: https://developer.mozilla.org/en-US/docs/Web/CSS/color_value
  - Coolors.co: https://coolors.co (interactive color palette generator)
  - Adobe Color Wheel: https://color.adobe.com/
  - Dribbble Inspiration: https://dribbble.com/search/color-palettes
  
- **Practical Exercise 1.1.1**: 
  - Create 3 color palettes (tech startup, luxury brand, friendly app)
  - Document color psychology for each
  - Save as CSS variables: `--color-primary: #0077cc;`

#### Module 1.2: Typography Mastery (8 hours)
- **Typography Hierarchy**
  - Font pairing (serif + sans-serif, modern stacks)
  - Scale system: 12px, 14px, 16px, 18px, 24px, 32px, 48px, 64px
  - Line height: 1.5 for body, 1.2 for headings, 1.6 for readability
  - Font weights: 400 (regular), 600 (semi-bold), 700 (bold)
  
- **Key Resources**:
  - Google Fonts: https://fonts.google.com/
  - Font Pairing Guide: https://www.fontpair.co/
  - Typescale Generator: https://typescale.com/
  - MDN Typography: https://developer.mozilla.org/en-US/docs/Web/CSS/font
  
- **Practical Exercise 1.2.1**:
  - Design a typography system with 3 font families
  - Create CSS scale with 8 size variations
  - Apply to heading, body, and caption elements

#### Module 1.3: Figma-to-Code Workflow (12 hours)
- **Figma Best Practices for Developers**
  - Using Auto Layout (maps to flexbox)
  - Component variants & design tokens
  - Extracting exact measurements, colors, fonts
  - Using Figma DevMode/Inspect for pixel-perfect specs
  
- **Key Resources**:
  - Figma Dev Mode Tutorial: https://help.figma.com/hc/en-us/articles/15023121212247-Guide-to-Dev-Mode
  - Figma to Code Workflow: https://claudefordesigners.com/guide/figma-workflow
  - AI Design-to-Code Comparison 2026: https://www.sixtythirtyten.co/blog/from-figma-to-code-ai-design-to-dev-workflows-in-2026
  
- **Practical Exercise 1.3.1**:
  - Create a simple Figma design (landing page hero section)
  - Export assets (images, icons as SVG)
  - Extract: colors (as hex), font sizes, padding, margins
  - Build a "specs document" with exact measurements

---

### **Week 2: CSS Fundamentals & Cascade Model**
**Goals**: Master CSS precedence, box model, and how context affects properties

#### Module 2.0: CSS Specificity, Cascade & Inheritance (CRITICAL) (12 hours)

**This is the foundation that lets you explain ANY styling issue by inspection**

##### 2.0.1: CSS Specificity (6 hours)
- **Understanding What Overrides What**
  - Specificity calculation: inline > ID > class/attribute > element
  - Specificity score: 0,0,0 (start here)
  - Element selector: adds 0,0,1
  - Class selector (.class): adds 0,1,0
  - ID selector (#id): adds 1,0,0
  - Attribute selector ([type="text"]): adds 0,1,0 (same as class!)
  - Pseudo-class (:hover, :focus): adds 0,1,0
  - Pseudo-element (::before, ::after): adds 0,0,1
  - Inline styles (style="color: red"): adds 1,0,0,0 (highest)
  - !important: breaks specificity (use sparingly)
  - :is(), :where(), :has() specificity gotchas
  
- **Real Examples**:
  ```
  p { color: blue; }                    /* 0,0,1 */
  p.intro { color: green; }             /* 0,1,1 - wins */
  #header p { color: red; }             /* 1,0,1 - wins over both */
  <p style="color: yellow;">            /* 1,0,0,0 - wins over all */
  ```

- **Cascade Resolution Algorithm**
  - Importance: !important declarations win
  - Specificity: higher specificity wins
  - Source order: last declaration wins (if specificity is equal)
  
- **Key Resources**:
  - MDN Specificity: https://developer.mozilla.org/en-US/docs/Web/CSS/Specificity
  - CSS Specificity Calculator: https://specificity.keegan.st/
  
- **Practical Exercise 2.0.1.1**:
  - Open DevTools on any website
  - Find element with multiple CSS rules
  - Explain strikethrough styling in DevTools
  - Calculate specificity scores for 10 selectors
  - Practice overriding styles

##### 2.0.2: The CSS Box Model (8 hours)

**The foundation that affects EVERYTHING**

- **Box Model Anatomy**
  - Content: actual content (text, images)
  - Padding: space INSIDE element (has background color)
  - Border: frame around padding
  - Margin: space OUTSIDE element (no background)
  - Outline: drawn OUTSIDE border (doesn't affect layout)
  
- **box-sizing Property (CRITICAL)**
  - `content-box`: width = content only, padding/border added on top
  - `border-box`: width = content + padding + border (predictable!)
  - Always use `* { box-sizing: border-box; }`
  
- **Margin Collapsing (Block Elements)**
  - Adjacent block elements: margins collapse to largest margin
  - Parent-child: weird edge case
  - Flexbox/Grid: margins DON'T collapse
  
- **Margin vs Padding**
  - Margin: space between elements
  - Padding: space inside elements (with background)
  
- **Key Resources**:
  - MDN Box Model: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_box_model
  - MDN box-sizing: https://developer.mozilla.org/en-US/docs/Web/CSS/box-sizing
  
- **Practical Exercise 2.0.2.1**:
  - Open DevTools Box Model tab
  - Click on elements and understand their box model
  - Identify margin collapsing issues
  - Change margin/padding live and see effects

##### 2.0.3: Display Property & Layout Context (12 hours)

**THIS CHANGES HOW MARGIN/PADDING WORK**

- **display: block**
  - Takes full width (100%)
  - Respects all margins and padding
  - Margins collapse vertically
  - `margin: 0 auto` centers horizontally
  - Examples: `<div>`, `<p>`, `<h1>`

- **display: inline**
  - Takes only necessary width
  - Respects padding/border left/right ONLY
  - Respects margin left/right ONLY
  - Top/bottom margin IGNORED (won't work!)
  - Can't set width/height
  - Examples: `<span>`, `<a>`, `<strong>`
  - GOTCHA: margin-top/bottom don't work!

- **display: inline-block**
  - Flows inline, respects full box model
  - Respects ALL margins and padding
  - Can set width/height
  - Whitespace between elements creates gaps
  - Examples: buttons, badges

- **display: flex** (NEW BOX MODEL!)
  - Children become flex items
  - Margin/padding still work
  - `gap`: cleaner spacing alternative
  - `margin: auto`: centers flex item!
  - Margins don't collapse
  - `margin-left: auto`: pushes item right

- **display: grid** (NEW BOX MODEL!)
  - Children become grid items
  - Margin/padding work normally
  - `gap`: spacing between cells
  - Margins don't collapse

- **Quick Reference Table**:
  ```
  | Display      | Margin T/B | Margin L/R | Padding | Width/Height |
  |--------------|-----------|-----------|---------|--------------|
  | block        | ✅        | ✅       | ✅     | ✅          |
  | inline       | ❌ (no!)  | ✅       | ⚠️     | ❌          |
  | inline-block | ✅        | ✅       | ✅     | ✅          |
  | flex         | ✅        | ✅       | ✅     | ✅          |
  | grid         | ✅        | ✅       | ✅     | ✅          |
  ```

- **Key Resources**:
  - MDN Display: https://developer.mozilla.org/en-US/docs/Web/CSS/display
  - MDN Flex: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout
  
- **Practical Exercise 2.0.3.1**:
  - Find 5 inline elements on a page
  - Try to add margin-top (it won't work)
  - Change display to inline-block (now it works!)
  - Find flex containers and understand margin behavior
  - Document which margins/padding work for each display type

##### 2.0.4: Context-Specific Box Model Behavior (8 hours)

**How Layout Context Changes Margin/Padding Rules**

- **Flexbox Container Effects**
  - `gap`: spacing between items (cleaner than margin)
  - Margin on flex items: creates space outside
  - `margin: auto`: centers item both axes! (magic)
  - `margin-left: auto`: pushes item right
  - `margin-right: auto`: pushes item left
  - Margins don't collapse (unlike block)
  
  **Example**:
  ```css
  .flex { display: flex; gap: 16px; }  /* cleaner than margin */
  .item { margin: auto; }              /* centers both axes! */
  .nav-right { margin-left: auto; }   /* push to right */
  ```

- **Grid Container Effects**
  - `gap`: spacing between cells
  - Margin still works on grid items
  - Padding works normally
  - `place-self`: alignment of single item
  
- **Position: Absolute Effects**
  - Taken out of normal flow
  - `top`, `right`, `bottom`, `left`: positioning
  - Margin: affects distance from edges
  - Parent must be `position: relative`
  
  **Example**:
  ```css
  .container { position: relative; }
  .badge { position: absolute; top: 0; right: 0; margin: 8px; }
  ```

- **Position: Fixed Effects**
  - Fixed in viewport
  - `top`, `right`: relative to viewport
  - Margin/padding work normally
  - z-index: controls stacking

- **Overflow Effects**
  - `overflow: hidden`: clips content, prevents margin collapse
  - `overflow: auto`: shows scrollbar
  - Creates new stacking context

- **Key Resources**:
  - MDN Overflow: https://developer.mozilla.org/en-US/docs/Web/CSS/overflow
  - MDN Position: https://developer.mozilla.org/en-US/docs/Web/CSS/position
  
- **Practical Exercise 2.0.4.1**:
  - Find a navbar and identify if it uses gap or margin
  - Find a card with padding
  - Inspect absolute positioned elements (badges, overlays)
  - Explain margin behavior in each context

##### 2.0.5: Inspector Debugging Masterclass (6 hours)

**The Skill That Makes You Pro**

- **Chrome DevTools Elements Tab**
  - Selecting elements: Ctrl+Shift+C
  - HTML structure understanding
  - Overridden styles: strikethrough = not applied
  - Box model tab: visual representation
  - Computed styles: actual values being used

- **Reading the Box Model Panel**
  - Blue: content
  - Green: padding
  - Yellow/Tan: margin
  - Red/Orange: border
  - Hover to highlight on page
  - Numbers show exact pixel values

- **Debugging Issues**:
  - Wrong spacing? Check margin/padding/gap
  - margin-top not working? Check display type
  - Text cut off? Check overflow
  - Won't center? Check alignment
  - z-index not working? Check position
  - Animation janky? Check will-change

- **Live Editing**
  - Double-click values to edit
  - Test changes before coding
  - Take screenshot of correct style
  - Copy CSS to your file

- **Practical Exercise 2.0.5.1**:
  - Open 5 different websites
  - Pick an element you like
  - Inspect and explain:
    - Display type and why
    - Margin/padding values
    - Box model visualization
  - Build your own version

---

### **Week 2 (continued): CSS Fundamentals & Layout Systems**
**Goals**: Master Flexbox, Grid, and positioning; understand CSS rendering

#### Module 2.1: Advanced Flexbox (10 hours)
- **Flexbox Deep Dive**
  - Main axis vs cross axis
  - `justify-content`, `align-items`, `align-content`
  - `flex`, `flex-basis`, `flex-grow`, `flex-shrink`
  - gap property and spacing patterns
  - Responsive flex layouts (mobile-first)
  
- **Key Resources**:
  - MDN Flexbox Guide: https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Flexbox
  - CSS Tricks Flexbox: https://css-tricks.com/snippets/css/a-guide-to-flexbox/
  - Flexbox Froggy Game: https://flexboxfroggy.com/ (interactive learning)
  
- **Practical Exercise 2.1.1**:
  - Build 5 layouts using only flexbox: navbar, card grid, centered modal, sidebar layout, footer
  - Use flexbox for spacing, not margins
  - Make responsive without media queries first

#### Module 2.2: CSS Grid Mastery (10 hours)
- **Grid Deep Dive**
  - Grid template columns/rows
  - Grid auto flow, implicit vs explicit grid
  - Grid lines and naming
  - `grid-column`, `grid-row` placement
  - Subgrid (CSS Grid Level 2)
  - When Grid > Flexbox (2D layouts)
  
- **Key Resources**:
  - MDN Grid Guide: https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Grids
  - CSS Tricks Grid: https://css-tricks.com/snippets/css/complete-guide-grid/
  - Grid Garden Game: https://cssgridgarden.com/
  
- **Practical Exercise 2.2.1**:
  - Build a 12-column grid system for responsive design
  - Create: hero section (full-width), 2-column layout, 3-column card grid
  - Implement responsive: 1 col (mobile) → 2 col (tablet) → 3 col (desktop)

#### Module 2.3: Positioning & Stacking Context (5 hours)
- **Positioning Deep Dive**
  - `static`, `relative`, `absolute`, `fixed`, `sticky`
  - Z-index and stacking context gotchas
  - Absolute positioning patterns (badges, overlays)
  - Fixed positioning for navigation
  
- **Key Resources**:
  - MDN Positioning: https://developer.mozilla.org/en-US/docs/Web/CSS/position
  - MDN Stacking Context: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioned_Layout/Understanding_z-index/The_stacking_context
  
- **Practical Exercise 2.3.1**:
  - Create a complex layout: hero with floating elements, sticky header, modals with overlays

---

### **Week 3: Vanilla CSS Styling & Design Patterns**
**Goals**: Master modern CSS, spacing systems, creating reusable patterns

#### Module 3.1: CSS Variables & Design Tokens (8 hours)
- **Design Tokens System**
  - CSS custom properties (`--variable-name`)
  - Creating a token scale: colors, spacing, typography, shadows, radii
  - Dark mode switching with CSS variables
  - Mobile-first token scaling
  
- **Key Resources**:
  - MDN CSS Variables: https://developer.mozilla.org/en-US/docs/Web/CSS/--*
  - Design Tokens: https://www.designtokens.org/
  
- **Practical Exercise 3.1.1**:
  - Create a comprehensive design token system:
    - 8 color tokens (primary, secondary, success, warning, error, etc.)
    - Spacing scale: 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px
    - Typography scale
    - Shadow system (sm, md, lg)
    - Border radius scale
  - Implement dark mode toggle using CSS variables

#### Module 3.2: Spacing & Sizing Systems (8 hours)
- **Professional Spacing**
  - 8px base unit philosophy (why it works)
  - Vertical rhythm: consistent line-height, spacing
  - Margins vs padding patterns
  - White space as design element
  - Safe spacing around interactive elements
  
- **Key Resources**:
  - Design System Spacing: https://material.io/design/layout/spacing-methods.html
  - Baseline Grid: https://www.designsystems.com/
  
- **Practical Exercise 3.2.1**:
  - Design spacing scale for your project
  - Apply 8px rhythm to a landing page
  - Test white space impact on visual hierarchy

#### Module 3.3: Border Radius, Shadows & Depth (8 hours)
- **Visual Depth Techniques**
  - Subtle vs bold shadow strategies
  - Neumorphism shadows: inner + outer soft shadows
  - Drop shadows for elevation
  - Blur and opacity for depth
  - Shadow stacking (multiple shadows for realism)
  
- **Key Resources**:
  - Shadow Generator: https://www.cssmatic.com/box-shadow
  - Neumorphism Generator: https://neumorphism.io/
  
- **Practical Exercise 3.3.1**:
  - Create shadow scale: sm (1px blur), md (4px blur), lg (12px blur), xl (20px blur)
  - Build neumorphic components: buttons, cards, inputs
  - Create elevation system using shadows

#### Module 3.4: Responsive Design Patterns (8 hours)
- **Mobile-First RWD**
  - Mobile-first mindset (start small, enhance)
  - Breakpoints: 480px (mobile), 768px (tablet), 1024px (desktop), 1440px (large)
  - Fluid typography & spacing with `clamp()`
  - Container queries for component-level responsiveness
  - Touch-friendly sizing: 44×44px minimum tap targets
  
- **Key Resources**:
  - MDN Media Queries: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_media_queries/Using_media_queries
  - Container Queries: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_queries
  - Responsive Web Design Guide 2026: https://www.alfdesigngroup.com/post/best-practices-for-mobile-first-websites
  
- **Practical Exercise 3.4.1**:
  - Convert fixed-size design to responsive
  - Test on 5 breakpoints: 375px, 768px, 1024px, 1440px, 1920px
  - Implement `clamp()` for fluid scaling
  - Ensure 44px touch targets

---

### **Week 4: Tailwind CSS Mastery**
**Goals**: Master utility-first workflow, design systems with Tailwind

#### Module 4.1: Tailwind Fundamentals & Setup (8 hours)
- **Utility-First Philosophy**
  - Why utilities > custom CSS
  - JIT (Just-In-Time) compilation and tree-shaking
  - Tailwind config customization
  - @apply for component extraction
  - Content configuration for purging unused CSS
  
- **Key Resources**:
  - Tailwind Docs: https://tailwindcss.com/docs
  - Tailwind CSS 2025 Guide: https://codeformatting.com/blogs/tailwind-css/
  - Tailwind v4 Features: https://tailwindcss.com/blog/tailwindcss-v4
  
- **Practical Exercise 4.1.1**:
  - Set up Tailwind in React project
  - Create custom config with brand colors
  - Build first components using utility classes
  - Reduce bundle size by proper configuration

#### Module 4.2: Component Building with Tailwind (10 hours)
- **Reusable Component Patterns**
  - Button variants (primary, secondary, ghost, outline)
  - Card component system
  - Form inputs with consistent styling
  - Typography components
  - Layout components (container, grid wrapper)
  - Using variants with class composition
  
- **Key Resources**:
  - Tailwind Component Guide: https://tailwindcss.com/docs/extracting-components
  - Headless UI (pre-built accessible components): https://headlessui.com/
  - Radix UI: https://www.radix-ui.com/ (unstyled component library)
  
- **Practical Exercise 4.2.1**:
  - Build comprehensive component library:
    - 4 button variants
    - 3 card styles
    - Input + textarea with validation states
    - Badge, pill, tag components
    - Alert/notification component
  - Use @apply for DRY code where appropriate

#### Module 4.3: Dark Mode & Responsive Patterns (8 hours)
- **Tailwind Dark Mode**
  - Class-based vs system preference dark mode
  - Toggling dark mode with localStorage
  - Color palette for dark mode
  - Dark mode utilities: `dark:` prefix
  
- **Responsive Utilities**
  - Breakpoint prefixes: `sm:`, `md:`, `lg:`, `xl:`, `2xl:`
  - Hiding/showing at breakpoints
  - Responsive typography scaling
  - Grid column spanning at different breakpoints
  
- **Key Resources**:
  - Dark Mode Guide: https://tailwindcss.com/docs/dark-mode
  - Responsive Design: https://tailwindcss.com/docs/responsive-design
  
- **Practical Exercise 4.3.1**:
  - Implement dark mode toggle in a landing page
  - Build fully responsive layout: mobile-first then desktop
  - Test at all 6 breakpoints
  - Ensure contrast ratios meet WCAG AA

#### Module 4.4: Tailwind Design System (6 hours)
- **Scaling Tailwind**
  - Extending tailwind.config.js with design tokens
  - Creating consistent color palettes
  - Custom plugins for repeated patterns
  - Documentation for team consistency
  
- **Key Resources**:
  - Design Tokens with Tailwind: https://www.frontendtools.tech/blog/tailwind-css-best-practices-design-system-patterns
  
- **Practical Exercise 4.4.1**:
  - Create documented design system in Tailwind
  - Include: colors, spacing, typography, components
  - Build reusable component snippets

---

### **Week 5: CSS Animations & Transitions**
**Goals**: Master pure CSS animations, performance optimization

#### Module 5.1: CSS Transitions (8 hours)
- **Smooth State Changes**
  - `transition` property: duration, delay, timing-function
  - Easing functions: ease, ease-in, ease-out, ease-in-out, custom cubic-bezier
  - Multi-property transitions
  - Timing best practices: 200ms quick, 300-500ms standard
  - Avoiding janky animations
  
- **Key Resources**:
  - MDN Transitions: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Transitions
  - Easing Cheat Sheet: https://easings.net/
  - CSS Animation Performance: https://design.dev/guides/css-animations/
  
- **Practical Exercise 5.1.1**:
  - Create hover states for interactive elements
  - Button: color + scale change (use transform not width)
  - Card: subtle shadow shift on hover
  - Form input: border color + focus glow

#### Module 5.2: CSS Keyframe Animations (12 hours)
- **Complex Animations**
  - @keyframes syntax: percentage vs from/to
  - animation-duration, animation-delay, animation-iteration-count
  - animation-fill-mode: forwards, backwards, both
  - animation-timing-function variations
  - Performance: use transform + opacity only (GPU-accelerated)
  - Avoiding expensive properties: width, height, top, left, margin
  
- **Common Patterns**:
  - Loading spinners
  - Pulse animations (attention grabbers)
  - Fade in/out sequences
  - Slide in from edges
  - Bounce and spring effects
  - Shimmer loading effects
  
- **Key Resources**:
  - MDN Keyframes: https://developer.mozilla.org/en-US/docs/Web/CSS/@keyframes
  - CSS Animation Best Practices 2025: https://playground.halfaccessible.com/blog/css-animation-transitions-guide
  
- **Practical Exercise 5.2.1**:
  - Build 8 reusable animations:
    1. Fade in (0% opacity → 100%)
    2. Slide up from bottom (transform translateY)
    3. Scale bounce (spring-like effect)
    4. Rotate spinner (infinite)
    5. Pulse alert (opacity pulse)
    6. Shimmer skeleton (gradient animation)
    7. Blink cursor
    8. Flip card 3D effect

#### Module 5.3: Transform & Perspective (8 hours)
- **Advanced Transforms**
  - 2D transforms: translate, scale, rotate, skew
  - 3D transforms: translateZ, rotateX, rotateY, rotateZ
  - Transform origin and perspective
  - Transform stacking order matters!
  - GPU acceleration with will-change
  
- **Key Resources**:
  - MDN Transform: https://developer.mozilla.org/en-US/docs/Web/CSS/transform
  - Transform Generator: https://cssmatrix.io/
  
- **Practical Exercise 5.3.1**:
  - Create 3D flip card animation
  - Build rotating cube (4 faces)
  - Parallax scroll effect (perspective)

#### Module 5.4: Performance Optimization (6 hours)
- **Animation Performance**
  - Chrome DevTools Performance panel: recording and analyzing
  - Dropping frames detection (60 FPS target)
  - GPU acceleration best practices
  - Avoiding layout thrashing
  - Debouncing expensive animations
  - Testing on low-end devices
  
- **Key Resources**:
  - Web Animation Performance 2025: https://mmcommunications.vn/en/web-animation-motion-design-guide-n607
  - Chrome DevTools: https://developer.chrome.com/docs/devtools/performance/
  
- **Practical Exercise 5.4.1**:
  - Record and analyze animations in DevTools
  - Identify expensive properties
  - Optimize to maintain 60 FPS
  - Compare transform vs position animations

---

### **Week 6: Framer Motion (formerly Motion) in React**
**Goals**: Advanced gesture animations, scroll interactions, layout transitions

#### Module 6.1: Framer Motion Fundamentals (10 hours)
- **Setup & Core Concepts**
  - Installation (npm install motion)
  - Importing from `motion/react` (v12+ naming)
  - Motion components: motion.div, motion.button, etc.
  - animate, initial, whileHover, whileTap props
  - Variants for state management
  - Transition timing and spring physics
  
- **Key Resources**:
  - Motion (formerly Framer Motion) Docs: https://motion.dev/
  - Motion v12 Updates: https://refine.dev/blog/framer-motion/
  - LogRocket Guide (2025): https://blog.logrocket.com/creating-react-animations-with-motion/
  - Beginner's Guide: https://medium.com/@cirilptomass/a-beginners-guide-to-framer-motion-in-react-next-js-2378c7c1b20d
  
- **Practical Exercise 6.1.1**:
  - Build interactive button with hover + tap animations
  - Create card with entrance animation
  - Implement variant-based state transitions

#### Module 6.2: Gesture Animations & Interactions (10 hours)
- **User Interactions**
  - Hover animations (whileHover)
  - Tap/click animations (whileTap)
  - Drag animations (drag, dragConstraints, dragElastic)
  - Gesture detection
  - Momentum scrolling
  - Drag to dismiss patterns
  
- **Practical Exercise 6.2.1**:
  - Build draggable modal (drag to dismiss)
  - Create swipeable card stack
  - Implement drag-to-sort list
  - Add spring-back effect after drag

#### Module 6.3: Scroll-Based Animations (10 hours)
- **Scroll Interactions**
  - useScroll hook for scroll progress
  - whileInView for entrance animations
  - Parallax scrolling effects
  - Reveal-on-scroll patterns
  - Horizontal scroll animations
  - Hardware-accelerated scroll (v12+)
  
- **Key Patterns**:
  - Hero section parallax
  - Staggered entrance on scroll
  - Progress bars tracking scroll
  - Animated counters triggered by scroll
  - Sticky animated headers
  
- **Practical Exercise 6.3.1**:
  - Build landing page with scroll animations:
    - Parallax hero section
    - Staggered fade-in for features
    - Counter animations on view
    - Animated timeline
    - Scroll progress indicator

#### Module 6.4: Layout Animations & Advanced Techniques (8 hours)
- **Advanced Patterns**
  - layoutId for shared layout animations
  - AnimatePresence for exit animations
  - useAnimation for programmatic control
  - useMotionValue for custom tracking
  - SVG animations
  - Color animations (new in v12: oklch, oklab, lab, lch support)
  
- **Performance Best Practices**:
  - useReducedMotion for accessibility
  - Lazy loading animations with useInView
  - Reducing unnecessary animations
  - Memory management in motion animations
  
- **Practical Exercise 6.4.1**:
  - Build animated tab switcher with shared layout animation
  - Create morphing button (shape transition)
  - Implement respects-prefers-reduced-motion
  - Build page transition animations

---

### **Week 7: Design Trends & Accessibility**
**Goals**: Master glassmorphism, implement WCAG standards, reverse-engineer great design

#### Module 7.1: Modern Design Trends (10 hours)

##### 7.1.1: Glassmorphism (5 hours)
- **Frosted Glass Effect**
  - backdrop-filter: blur(X px)
  - Semi-transparent backgrounds: rgba/hsla
  - Border styling for glass effect
  - Layering and depth
  - Performance considerations
  - Accessibility with text contrast
  
- **Key Resources**:
  - Glassmorphism Guide 2025: https://playground.halfaccessible.com/blog/glassmorphism-design-trend-implementation-guide/
  - CSS Glassmorphism: https://natebal.com/glassmorphism-web-design/
  - Generator: https://glassmorphism.com/
  
- **Practical Exercise 7.1.1.1**:
  - Create glassmorphic card component
  - Build glassmorphic modal
  - Implement on portfolio site hero section

##### 7.1.2: Neumorphism (5 hours)
- **Soft UI Design**
  - Multiple box shadows: inner + outer
  - Monochromatic color schemes
  - Subtle depth vs flat design
  - Interactive states (pressed/released)
  - Accessibility challenges with low contrast
  
- **Key Resources**:
  - Neumorphism vs Glassmorphism 2025: https://syngrid.com/neumorphism-vs-glassmorphism-which-trend-works-in-2025/
  - Design Trends 2026: https://www.zignuts.com/blog/neumorphism-vs-glassmorphism
  - Neumorphism Generator: https://neumorphism.io/
  
- **Practical Exercise 7.1.2.1**:
  - Design neumorphic button set
  - Create neumorphic dashboard component
  - Ensure WCAG contrast compliance

#### Module 7.2: Reverse-Engineering Great Design (10 hours)
- **How to Study Award-Winning Sites**
  - Tools: DevTools, Figma, Inspect Element, ColorZilla
  - What to look for: spacing, typography, animations, microinteractions
  - Building a swipe file: collections of inspiration
  - Documenting patterns discovered
  
- **Inspiration Sources**:
  - Dribbble: https://dribbble.com/
  - Awwwards: https://www.awwwards.com/
  - Behance: https://www.behance.net/
  - Designer Hangout: https://www.designerhangout.co/
  
- **Practical Exercise 7.2.1**:
  - Pick 3 award-winning portfolio sites
  - Document: color palette, typography scale, spacing system, animation patterns
  - Recreate one hero section from scratch
  - Build your own variation with learned techniques

#### Module 7.3: Web Accessibility (WCAG 2.2) (8 hours)
- **Accessibility Standards**
  - WCAG 2.2 Level AA requirements
  - POUR principles: Perceivable, Operable, Understandable, Robust
  - Color contrast ratios: 4.5:1 for text, 3:1 for large text
  - Keyboard navigation: tabindex, focus visible, arrow keys
  - Screen reader friendly HTML: semantic markup, ARIA roles
  - Motion & animation: prefers-reduced-motion media query
  
- **Key Resources**:
  - WCAG 2.2 Guidelines: https://www.w3.org/WAI/WCAG22/quickref/
  - Web Accessibility Best Practices 2025: https://www.broworks.net/blog/web-accessibility-best-practices-2025-guide
  - WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
  - MDN Accessibility: https://developer.mozilla.org/en-US/docs/Web/Accessibility
  
- **Practical Exercise 7.3.1**:
  - Audit existing component library for a11y
  - Fix contrast issues
  - Add keyboard navigation
  - Implement focus indicators
  - Test with screen reader (NVDA, JAWS)
  - Add prefers-reduced-motion support

#### Module 7.4: Responsive Design Best Practices (6 hours)
- **Mobile-First Design Execution**
  - Touch-friendly sizing: 44×44px minimum
  - Thumb zones on mobile
  - Readable fonts without zooming: minimum 16px body
  - Line height for legibility: 1.5-1.6
  - Viewport scaling: 200% zoom must work
  - Landscape vs portrait orientations
  
- **Key Resources**:
  - Mobile Accessibility 2026: https://www.webability.io/blog/mobile-accessibility-best-practices-for-designing-inclusive-mobile-experiences/
  - Responsive Web Design Guide 2026: https://www.alfdesigngroup.com/post/best-practices-for-mobile-first-websites
  
- **Practical Exercise 7.4.1**:
  - Test portfolio on real devices: iPhone, iPad, Android phone, tablet
  - Check landscape orientation
  - Verify 200% zoom functionality
  - Ensure touch targets are 44px minimum

---

### **Week 8: Capstone Project & Polish**
**Goals**: Build stunning portfolio that showcases all skills

#### Module 8.1: Portfolio Site Design & Development (20 hours)

**Requirements**:
1. **Hero Section**
   - Glassmorphic card with animated text entrance
   - Parallax background
   - CTA button with microinteraction
   - Responsive: mobile stacked, desktop side-by-side

2. **About Section**
   - Neumorphic cards for skills
   - Animated counter when scrolling into view
   - Smooth image reveal
   - Timeline of experience with animations

3. **Projects Showcase**
   - Animated card grid (staggered entrance)
   - Hover effects with image overlay
   - Filter by category (animated transitions)
   - Modal with project details and tech stack

4. **Animations Throughout**
   - At least 5 different pure CSS animations
   - 3 Framer Motion gesture interactions
   - 2 scroll-based animations
   - Respects prefers-reduced-motion

5. **Design & Styling**
   - Custom color palette with dark mode
   - Complete typography system
   - Consistent spacing (8px base unit)
   - Glassmorphic components on hero
   - Neumorphic cards on skills/projects

6. **Code Quality**
   - Tailwind CSS for styling
   - Reusable React components
   - Semantic HTML
   - Optimized bundle size
   - No unused CSS

7. **Accessibility**
   - WCAG 2.2 Level AA compliance
   - Keyboard navigation throughout
   - All images have alt text
   - Color contrast ratios verified
   - Focus indicators visible

8. **Performance**
   - Animations maintain 60 FPS
   - Lighthouse score >90
   - Optimized images (WebP format)
   - Fast load time (<3s on 4G)

#### Module 8.2: Component Library Development (15 hours)
- **Reusable Components**
  - Button (4 variants)
  - Card (3 styles: flat, elevated, outline)
  - Input/Textarea with validation
  - Badge/Pill/Tag
  - Alert/Toast notification
  - Modal dialog
  - Dropdown menu
  - Accordion
  - Tabs
  - Slider/Progress bar

- **Each Component Should**:
  - Have multiple states: default, hover, active, disabled, loading
  - Support animation variants
  - Be fully accessible
  - Work in light AND dark mode
  - Be responsive
  - Have documented props

#### Module 8.3: Documentation & Deployment (5 hours)
- **Document Your Work**
  - Component storybook or documentation site
  - Design system documentation
  - Animation guidelines
  - Accessibility checklist
  - Performance metrics

- **Deploy**
  - Vercel: https://vercel.com/
  - Netlify: https://www.netlify.com/
  - GitHub Pages: https://pages.github.com/

---

## RECOMMENDED LEARNING RESOURCES

### Official Documentation
- **MDN Web Docs**: https://developer.mozilla.org/
- **Tailwind CSS Docs**: https://tailwindcss.com/docs
- **Motion (Framer Motion) Docs**: https://motion.dev/
- **WCAG Guidelines**: https://www.w3.org/WAI/WCAG22/quickref/

### Interactive Learning Platforms
- **Flexbox Froggy**: https://flexboxfroggy.com/
- **Grid Garden**: https://cssgridgarden.com/
- **Easing Cheat Sheet**: https://easings.net/
- **Color Picker**: https://coolors.co/

### Design Inspiration
- **Dribbble**: https://dribbble.com/
- **Awwwards**: https://www.awwwards.com/
- **Behance**: https://www.behance.net/
- **UI Kits on Awwwards**: https://www.awwwards.com/search?related=ui-kits

### Tools
- **Figma**: https://www.figma.com/ (design & prototyping)
- **DevTools**: Built into Chrome, Firefox, Safari
- **Lighthouse**: https://developers.google.com/web/tools/lighthouse (performance audit)
- **WebAIM Contrast Checker**: https://webaim.org/resources/contrastchecker/

---

## WEEKLY SCHEDULE (40 hours/week)

```
Monday-Wednesday: New Content (16 hours)
  - 4 hours theory + documentation reading
  - 4 hours guided exercises
  - 4 hours independent projects
  - 4 hours reverse-engineering + studying code

Thursday-Friday: Projects & Practice (16 hours)
  - 8 hours building mini-projects
  - 4 hours testing (responsive, accessibility, performance)
  - 4 hours polishing and documenting

Weekend: Review & Deep Dive (8 hours)
  - 2 hours reviewing week's learning
  - 4 hours extra practice on weak areas
  - 2 hours planning next week
```

---

## SUCCESS METRICS

By Week 8, you should be able to:

✅ Translate any Figma design to pixel-perfect code
✅ Build responsive layouts with Flexbox/Grid without thinking
✅ Create smooth animations that don't impact performance
✅ Design with color theory and typography principles
✅ Implement WCAG 2.2 Level AA accessibility
✅ Build production-quality components with Tailwind
✅ Create wow factor with Framer Motion
✅ Reverse-engineer and improve on award-winning designs
✅ Deploy stunning portfolio that gets noticed
✅ Have a component library ready for team use

---

## NOTES FOR SUCCESS

1. **Code Along Constantly**: Don't just read, actually type every example
2. **Inspect Everything**: Use DevTools to understand how sites are built
3. **Test on Real Devices**: Desktop testing is not enough
4. **Iterate**: Redesign your projects weekly as you learn new skills
5. **Document Your Learning**: Write blog posts on what you've learned
6. **Join Communities**: Frontend design communities for feedback
7. **Measure & Optimize**: Use Lighthouse, WebAIM, performance tools regularly
8. **Build in Public**: Share progress on Twitter/LinkedIn for accountability

---

**Ready to Start? Begin with Week 1, Module 1.1!**
