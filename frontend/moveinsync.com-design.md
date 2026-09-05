---
version: alpha
name: Move in Sync
description: A clean, enterprise SaaS system with high-trust simplicity, bright whitespace, and a single energetic green accent.
colors:
  primary: "#43B02A"
  secondary: "#1E4A9B"
  tertiary: "#FF7A3D"
  neutral: "#333333"
  surface: "#FFFFFF"
  surface-alt: "#F7F8FA"
  on-surface: "#1F1F1F"
  on-primary: "#FFFFFF"
  border: "#E5E7EB"
  muted: "#6B7280"
  success: "#43B02A"
  error: "#D92D20"
typography:
  headline-display:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: 700
    lineHeight: 57.6px
    letterSpacing: 0px
  headline-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: 600
    lineHeight: 43.2px
    letterSpacing: 0px
  headline-md:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: 600
    lineHeight: 33.6px
    letterSpacing: 0px
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 600
    lineHeight: 22px
    letterSpacing: 0px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 400
    lineHeight: 28px
    letterSpacing: 0px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
    letterSpacing: 0px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
    letterSpacing: 0px
  label-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 600
    lineHeight: 24px
    letterSpacing: 0px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 600
    lineHeight: 20px
    letterSpacing: 0px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 600
    lineHeight: 16px
    letterSpacing: 0.02em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
    letterSpacing: 0px
rounded:
  none: 0px
  sm: 4px
  md: 8px
  lg: 16px
  xl: 30px
  full: 9999px
spacing:
  xs: 6px
  sm: 14px
  md: 20px
  lg: 24px
  xl: 50px
  gutter: 32px
  section: 80px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.xl}"
    padding: 15px 20px
    height: 46px
  button-primary-hover:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.xl}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.neutral}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.xl}"
    padding: 15px 20px
    height: 46px
  button-link:
    backgroundColor: "transparent"
    textColor: "{colors.neutral}"
    typography: "{typography.body-md}"
    rounded: "{rounded.none}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.md}"
    padding: 16px
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: 12px 14px
# Move in Sync

## Overview
Move in Sync feels polished, practical, and enterprise-friendly, with a strong emphasis on clarity over decoration. The visual tone is bright and reassuring: lots of white space, dark neutral text, and a vivid green call to action that signals momentum and reliability. The layout is spacious and conversion-oriented, suited to decision-makers evaluating a business platform rather than a consumer brand.

## Colors
- **Primary (#43B02A):** The signature green used for primary actions, trust cues, and brand highlights. It is energetic without feeling loud, and it provides the strongest visual anchor on the page.
- **Secondary (#1E4A9B):** A deep blue used as a supporting enterprise tone, especially suitable for informational banners, links, and credibility layers. It adds a more formal, corporate counterbalance to the green.
- **Tertiary (#FF7A3D):** A warm accent for emphasis moments and supportive illustration details. Use sparingly so it does not compete with the primary CTA color.
- **Neutral (#333333):** The main text color for headlines, navigation, and body copy. It reads as softer than pure black, keeping the interface approachable.
- **Surface (#FFFFFF):** The dominant background color across the site. This bright white surface creates the open, airy feel seen in the screenshot.
- **Surface-alt (#F7F8FA):** A subtle off-white for grouped regions, cards, or low-contrast panels when a slight tonal separation is needed.
- **On-surface (#1F1F1F):** A near-black utility tone for high-contrast text or icons when stronger readability is required.
- **Border (#E5E7EB):** A light gray divider and outline color used for cards, pills, and framed UI elements.
- **Muted (#6B7280):** A secondary text tone for helper copy, navigation alternatives, and less important metadata.
- **Success (#43B02A):** Reuses the primary green for positive states and confirmation messaging.
- **Error (#D92D20):** Reserved for destructive actions and validation states; it should appear only in exceptional cases.

## Typography
Inter is the system typeface and should remain the default across all interface content. Headlines are bold and compact, with the largest level at 48px/57.6px for hero statements and progressively smaller display levels for section headers. Body text stays highly readable at 16px with a 24px line height, while labels and buttons use semi-bold weights to create a crisp, product-focused feel.

There is no visible uppercase-heavy branding treatment; the style is straightforward and sentence-case friendly. Letter spacing remains mostly neutral, with only the smallest label style using a slight positive spacing for utility text and compact interface cues. Overall, typography should feel modern, highly legible, and assertive without becoming editorial or theatrical.

## Layout & Spacing
The page uses a wide, centered, fluid container with generous side padding and substantial vertical breathing room. Hero content is split into a left text column and a right visual cluster, creating a balanced two-column composition that remains simple to scan. Section spacing is expansive, using a rhythm built around 6px, 14px, 20px, 24px, 50px, and larger section breaks to keep the interface calm and enterprise-grade.

Cards and framed UI elements should use modest internal padding rather than heavy nesting. Navigation elements are spaced loosely enough to feel premium, but not so far apart that the interface feels sparse or detached. Use the `spacing.section` rhythm for page blocks and `spacing.gutter` for interior grid separation.

## Elevation & Depth
Depth is intentionally minimal. The site relies on tonal contrast, clean borders, and large whitespace rather than pronounced shadows or layered surfaces. Where depth is needed, a very soft shadow may be used, but most UI should remain flat and crisp to preserve the trustworthy, businesslike feel.

Borders are subtle and light gray, especially around cards and small utility containers. The strongest hierarchy comes from size, weight, and color contrast rather than elevation. Avoid glossy effects, dramatic blur, or heavy drop shadows.

## Shapes
The shape language is smooth and friendly, with pill-shaped buttons and gently rounded cards. Primary calls to action use a large `30px` radius, producing a soft capsule that feels welcoming and modern. Supporting containers use smaller `8px` radii for a restrained, professional look.

Overall, the geometry should feel approachable but disciplined. Avoid sharp corners on important actions, but do not over-round every surface; the mix of `rounded.xl` for buttons and `rounded.md` for cards is part of the system’s balance.

## Components
Buttons are the most distinctive component in the system. Primary buttons use `button-primary`: solid green background, white text, semi-bold label styling, `15px 20px` padding, and a `46px` height minimum. Secondary buttons use `button-secondary`: white background, green border, dark text, and the same pill shape and sizing as the primary. Link-style actions use `button-link` and should remain text-only, without borders or background fills.

Buttons should feel stable and accessible: keep the label weight at 600, avoid overly tight padding, and preserve the wide pill radius. Hover states may deepen toward the secondary blue or slightly darken the green, but should not introduce shadows or motion-heavy treatments.

Cards use `card`: white background, `1px` light border, `8px` radius, and `16px` padding. They should read as lightweight containers rather than elevated panels. Inputs should mirror the same restrained card language: white fill, light border, `rounded.md`, and comfortable internal padding with clear focus visibility.

Navigation links should remain understated, with dark neutral text and small separators or spacing rather than decorative chrome. The informational banner at the top can use the secondary blue background with white text to create a high-contrast, utility-driven announcement style. Chips, badges, and trust markers should stay compact and simple, using color only when they reinforce meaning.

## Do's and Don'ts
- Do use the green primary color for the main conversion action and the strongest brand moments.
- Do keep layouts airy, with generous whitespace and clearly separated content groups.
- Do use Inter consistently for navigation, headings, body copy, and button labels.
- Do favor flat surfaces, light borders, and subtle tonal shifts over dramatic elevation.
- Do preserve pill-shaped CTAs and lightly rounded cards to match the observed UI language.
- Don't introduce heavy shadows, glass effects, or complex gradients.
- Don't use more than one or two competing accent colors at full strength in the same component cluster.
- Don't make buttons sharp-cornered or overly compact; the interface should feel calm and approachable.