# # Design System Document: GIRO MOBILITY  
  
## 1. Overview & Creative North Star  
  
**Creative North Star: "The Pulse Curator"**  
GIRO rejects the static, boxy layouts of traditional utility apps. Drawing inspiration from high-performance motorsport engineering and technical urban fashion, we create an experience as rapid as a heartbeat and as sharp as a late-night city sprint.  
  
**The GIRO Aesthetic:**  
* **Intentional Asymmetry:** Breaking the grid to create forward momentum.  
* **Tonal Layering:** Using depth through color shifts rather than heavy shadows.  
* **High-Velocity Contrast:** Bold, solid color blocks that signal action and precision. We move away from "standard" grids by using overlapping elements—where high-contrast modules break the boundary of a container.  
  
---  
  
## 2. Colors & Surface Philosophy  
  
The palette signifies passion and premium engineering through high-intensity solids. We strictly avoid gradients in favor of "Hard-Edge" transitions.  
  
### The Color Palette  
* **Primary (Deep Crimson):** `#A22522` — Critical actions, headers, and brand anchors.  
* **Secondary (Electric Orange):** `#FA7921` — High-priority alerts and secondary CTAs.  
* **Tertiary (Forest Tech):** `#3F6634` — Success states and specialized technical data.  
* **Surface (Parchment):** `#F8F6EC` — The base canvas (The "Track").  
  
### The "No-Line" Rule  
**Explicit Instruction:** Designers are prohibited from using 1px solid borders to define sections or cards. Hierarchy must be established through background color shifts.   
* Use `surface` (#F8F6EC) as your base canvas.  
* A section is "divided" by the sharp edge of its color block, not a stroke.  
  
---  
  
## 3. Typography: The Industrial Edge  
  
We utilize a tri-font system to balance brand character with technical precision.  
  
* **Display & Headlines (SORA):** Used for all titles and brand moments. Sora’s geometric structure should be set with tight letter-spacing (-0.02em) to feel bold and authoritative.  
* **Body & Editorial (MONTSERRAT):** The workhorse for narrative and descriptive text. Set `body-lg` with a generous line-height (1.6) to ensure a sophisticated, breathable feel.  
* **Functional UI (PUBLIC SANS):** Reserved for high-density data, labels, and technical inputs. This ensures maximum clarity at small sizes during high-velocity use.  
  
---  
  
## 4. Elevation & Depth  
  
We avoid traditional "material" shadows in favor of **Tonal Layering**.  
  
* **The Layering Principle:** Depth is achieved by placing a `surface_container_lowest` element on top of a `surface_container` background. The subtle shift in the light neutral spectrum signals "interactability."  
* **Ambient Shadows:** If an element must float (like a "Start" FAB), use an extra-diffused shadow: `Y: 20px, Blur: 40px, Color: #000000 @ 6%`.  
* **The Ghost Border:** For accessibility, use an `outline_variant` at **15% opacity**. It should be felt, not seen.  
  
---  
  
## 5. Components  
  
### Buttons  
* **Primary:** Background: Solid `primary` (#A22522) | Text: `on_primary`. Corner Radius: **8px**.   
* **Secondary:** Background: Solid `secondary` (#FA7921) | Text: `on_secondary`.  
* **Tertiary:** No background. Bold `tertiary` (#3F6634) text with a matching 2px underline.  
  
### Input Fields  
* **Style:** Minimalist. No bounding box. Only a bottom stroke using `outline_variant` at 20% opacity.   
* **Focus State:** The bottom stroke becomes `primary` (#A22522) at 2px thickness. The label (Sora Bold) shifts to the primary crimson.  
  
### Live Map Module  
* **Style:** Use a `surface` container with `20%` transparency and `backdrop-blur: 12px` to sit over the map. No borders or gradients.  
  
---  
  
## 6. Do's and Don'ts  
  
### Do:  
* **Do** use Sora for large, impactful headers that anchor the screen.  
* **Do** use asymmetrical margins (e.g., 24px left, 16px right) to create a sense of "lean" and movement.  
* **Do** use **Solid Deep Crimson** (#A22522) as a highlighter for the most critical information.  
  
### Don't:  
* **Don't use gradients.** All color applications must be solid and deliberate.  
* **Don't use 100% black (#000000).** Use deep variants of the surface colors for contrast.  
* **Don't use standard 1px dividers.** If you can't separate it with space, use a tonal background shift.  
* **Don't** use "Drop Shadows" on cards unless they are transient (e.g., menus or modals).  
  
---  
*Document Ends*  
