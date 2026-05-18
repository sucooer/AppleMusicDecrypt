# AppleMusicDecrypt Web Frontend Apple Media Redesign

## Summary

Redesign the existing Web UI from a utility-first operations panel into a media-driven download workbench. The approved direction is Apple media inspired: cover-led hero, a floating action card placed directly on the hero, calmer secondary status surfaces, and a responsive layout that stays usable on both desktop and mobile.

This redesign preserves the current FastAPI backend, endpoints, and single-page architecture. The work should focus on frontend structure, presentation, interaction states, and client-side rendering quality rather than backend feature expansion.

## Goals

- Make the first screen feel like a premium music product instead of a server console.
- Keep download actions immediately available above the fold.
- Improve visual hierarchy so input and task state are easier to parse than logs.
- Preserve the tool nature of the product: download, quality lookup, task progress, failed tracks, and logs remain available.
- Deliver a fully responsive experience for desktop and mobile.
- Improve state clarity for empty, loading, success, failure, and wrapper-unavailable states.

## Non-Goals

- Replacing the current backend stack or API contract.
- Adding multi-page navigation.
- Adding user accounts, history, queue management, or persistent storage.
- Introducing a frontend framework.
- Building a full album artwork ingestion pipeline from Apple metadata for V1 of the redesign.

## Approved Product Direction

### Approved choices

- Visual style: Apple media inspired.
- Hero style: cover-driven.
- First-screen priority: dynamic cover visual with controls in the same view.
- Device priority: fully responsive across desktop and mobile.

### Resulting product intent

The page should feel like a local music workstation with premium editorial styling. It should create emotional context through cover-inspired composition, typography, and motion, but it must still let a user paste a URL and start a task immediately without hunting for controls.

## Approaches Considered

Three approaches were considered:

1. Dark player-style interface with immersive full-screen artwork.
2. Light media hero with a floating action card and quieter secondary workbench sections.
3. Mixed-theme workbench with a media hero on top and a heavy dark operations console below.

Approach 2 was approved because it best balances brand-like media presentation and task efficiency. It also scales more safely to mobile than an immersive dark player layout and avoids the visual fragmentation risk of a mixed-theme console.

## Information Architecture

The page should be organized into three vertical sections in order of importance.

### 1. Hero and primary action

This is the dominant section of the page.

Content:

- Cover-inspired background composition made from multiple blurred or cropped artwork tiles.
- Short product statement.
- Primary floating action card.

The action card must contain:

- Apple Music URL input.
- Codec selector.
- Language selector.
- Force overwrite toggle.
- Primary `Download` button.
- Secondary `Quality Lookup` button.
- Inline notice area for validation, loading, success, or failure feedback.

The hero should not become a marketing landing page. It should remain operational and concise.

### 2. Task and system status

This section follows the hero and should summarize the current operational state without overwhelming the user.

Content:

- Current task state.
- Task detail.
- Album progress.
- Saved path.
- Download speed.
- Decrypt speed.
- Active task count.
- Wrapper availability and regions.
- Failed-track summary when relevant.

This area should visually elevate active work but remain quieter than the hero.

### 3. Result and console surfaces

This section contains lower-priority but still important operational output.

Content:

- Quality lookup result.
- Real-time log stream.

On desktop, these can sit side by side or in balanced stacked cards depending on viewport width. On mobile, they must stack vertically with sensible height limits.

## Visual System

### Overall tone

The interface should feel like a premium media utility, not a generic admin dashboard.

### Background and surfaces

- Use a warm light background with soft rose and blush gradients.
- Add subtle atmospheric color fields rather than flat fills.
- Use translucent white cards with light blur for primary and secondary surfaces.
- Reserve deep near-black only for the log content region, not for the whole page shell.

### Color palette

Recommended palette:

- Background base: `#fff7f8` to `#fff1f2`
- Primary text: near-deep plum such as `#2f1722`
- Secondary text: muted berry such as `#6b4a57`
- Primary action: `#e11d48`
- Secondary accent: `#fb7185`
- Utility blue for secondary interactive emphasis: `#2563eb`
- Success: soft green with strong text contrast
- Error: red aligned with the berry/rose system, not generic system red

The download action should own the strongest CTA color. Other controls must not compete with it.

### Typography

- Display and hero headings: `Playfair Display`
- Body copy, controls, labels, and status text: `Inter`

Typography rules:

- Large display title in the hero.
- Functional copy must stay crisp and modern.
- Serif usage should be limited to headlines and selective highlights.
- Body copy and controls should remain sans-serif for speed and clarity.

## Layout Rules

### Desktop

- Hero dominates the first viewport.
- Floating action card sits directly within the hero composition.
- Status section follows immediately below and can use a structured card grid.
- Quality and log sections appear after status and should not visually outrank the hero.

### Mobile

- Single-column flow.
- URL input and download action must remain visible in the first screen without scrolling past decorative artwork.
- Status cards must collapse into either a two-column compact grid or a restrained stacked layout.
- Logs and verbose outputs must be deprioritized below the primary action flow.

### Spacing and density

- Prefer clear breathing room between major sections.
- Avoid excessively dense utility-panel packing in the hero.
- Keep form controls large enough for touch use on mobile.

## Interaction Design

### URL input

- Validation should appear inline near the field, not only in the log panel.
- The input must visually support long pasted Apple Music URLs.

### Primary download flow

- Clicking `Download` should immediately show a loading state on the button.
- The hero card should show a concise submission status.
- Once a task starts, the task section should become visually active.

### Quality lookup

- Quality results should not be shown as raw developer-oriented JSON in the final experience.
- The frontend should reformat the response into a readable structured display or readable preformatted summary.

### Failed tracks

- Failed tracks should live in a dedicated card or sub-panel.
- The panel should stay hidden when there are no failures.
- Retry actions should be clearly separated from the main download CTA.

### Logs

- Logs should preserve a console feel.
- Logs should not dominate the initial scan of the page.
- On mobile, log height should be constrained and expandable through normal page flow rather than occupying the whole screen.

## Motion Design

Motion should be restrained and purposeful.

Allowed motion:

- Very slow ambient movement in hero light fields or artwork composition.
- Gentle enter animation for the primary hero card.
- Brief state highlight when task metrics update.
- Smooth hover and focus transitions.

Avoid:

- Continuous decorative spinning or bouncing.
- Large-scale transforms on hover that cause layout instability.
- Multiple simultaneous decorative animations competing for attention.

Timing guidance:

- Hover and focus transitions: roughly 160ms to 220ms.
- Entry motion: roughly 280ms to 420ms using ease-out curves.
- Ambient movement: very slow and nearly imperceptible.

Accessibility requirement:

- Respect `prefers-reduced-motion` and disable non-essential animation in that mode.

## State Design

### Empty state

- The hero should include a clear prompt to paste a song, album, playlist, artist, or MV URL.
- Task state should read as intentionally empty rather than showing raw placeholders wherever possible.

### Wrapper unavailable

- Wrapper connectivity should be translated into user-facing language.
- The UI should indicate that the page is reachable but download capability is unavailable.

### In-progress state

- Use human-readable task labels such as queued, downloading, decrypting, retrying, completed, and failed.
- Do not expose raw internal status strings if they are not user-friendly.

### Success state

- Surface completion with a visible success notice and emphasize the saved path briefly.

### Failure state

- Provide a concise user-facing summary near the hero or task panel.
- Keep detailed diagnostics in the log area.

## Component and File Boundaries

The redesign should stay within the existing web frontend boundary unless a small backend change is required to improve presentation semantics.

Primary files expected to change:

- `src/web/static/index.html`
- `src/web/static/styles.css`
- `src/web/static/app.js`

Backend changes should be avoided unless needed for one of these reasons:

- Exposing clearer task-state labels.
- Providing more structured quality data for readable rendering.
- Improving wrapper status wording without frontend guesswork.

## Accessibility and Usability Requirements

- Maintain strong text contrast on all light translucent surfaces.
- Ensure all controls have visible focus styles.
- Keep touch targets large enough for mobile.
- Do not use color as the sole indicator of task state.
- Preserve labels for all fields.
- Avoid layout shifts during hover or status updates.

## Performance Guardrails

- Keep visual effects CSS-first and lightweight.
- Avoid heavy continuous blur or animation stacks that degrade low-power devices.
- Limit animated elements to one or two focal surfaces.
- Preserve good first render behavior for a static asset page.

## Testing and Verification

The implementation plan should verify:

- Desktop hero and floating action card layout render as intended.
- Mobile first screen still exposes the main input and CTA.
- No horizontal scroll appears at narrow widths.
- `prefers-reduced-motion` is respected.
- Existing task, quality, retry, and SSE behaviors remain functional.
- Quality output is more readable than raw JSON.
- Wrapper unavailable, empty, active, success, and failure states are visually distinct.

## Open Implementation Notes

- The current page already has the required backend capability for task status, quality lookup, failed-track retry, and logs.
- The redesign should preserve current element IDs or update `app.js` in lockstep to avoid breaking behavior.
- The hero may use static artwork placeholders or abstract cover tiles first; real fetched cover art can remain a future enhancement if it would materially expand scope.
