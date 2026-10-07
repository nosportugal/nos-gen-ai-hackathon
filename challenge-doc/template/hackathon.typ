// =============================================================================
// NOS — JunctionX Lisbon 2026 handbook template
//
// Branding follows the NOS guidelines: white background, #121212 text,
// Segoe UI (Carlito as the metric-compatible open fallback), accent bars and
// content in bordered cards. JunctionX appears as a logo only.
//
// Usage (see main.typ):
//
//   #import "template/hackathon.typ": *
//   #show: hackathon-doc.with(title: "...", subtitle: "...")
// =============================================================================

// -----------------------------------------------------------------------------
// Brand tokens — NOS guidelines
// -----------------------------------------------------------------------------

#let nos-green = rgb("#00C853") // accent 1 — primary
#let nos-blue = rgb("#003B8E") // accent 2 — secondary
#let nos-cyan = rgb("#00ACC1") // accent 3 — support

#let ink = rgb("#121212") // body text
#let muted = rgb("#5F6B72") // secondary text
#let surface = rgb("#F6F7F8") // light grey card background
#let border = rgb("#E2E5E8") // card and table borders

// Segoe UI when available (Windows/Office), Carlito otherwise — Carlito is
// metric-compatible with Calibri, the sanctioned alternative.
// Add "Segoe UI" in front of this list when building on a machine that has it
// installed (it is not redistributable, so the repo ships Carlito instead).
#let brand-font = ("Carlito",)
#let mono-font = ("JetBrains Mono",)

#let event-name = "JunctionX Lisbon 2026"
#let event-dates = "10–11 October 2026"

#let logo-nos = "../assets/logos/nos-ink.png"
#let logo-junctionx = "../assets/logos/junctionx-ink.png"

// -----------------------------------------------------------------------------
// Header: small NOS logo, running section title, hairline
// -----------------------------------------------------------------------------

#let header-bar = context {
  let p = here().page()
  let seen = query(heading.where(level: 1)).filter(h => h.location().page() <= p)
  let running = if seen.len() > 0 { seen.last().body } else { [] }

  grid(
    columns: (auto, 1fr),
    align: (left + horizon, right + horizon),
    image(logo-nos, height: 11pt),
    text(size: 8pt, fill: muted)[#running],
  )
  v(3pt)
  line(length: 100%, stroke: 0.6pt + border)
}

// -----------------------------------------------------------------------------
// Footer: the two event logos, the hackathon dates, the page number
// -----------------------------------------------------------------------------

#let footer-bar(dates: event-dates) = {
  set text(size: 8pt, fill: muted)
  line(length: 100%, stroke: 0.6pt + border)
  v(4pt)
  grid(
    columns: (1fr, auto, 1fr),
    align: (left + horizon, center + horizon, right + horizon),
    // Left: NOS and JunctionX logos.
    stack(
      dir: ltr,
      spacing: 10pt,
      image(logo-nos, height: 10pt),
      image(logo-junctionx, height: 13pt),
    ),
    // Centre: the hackathon dates.
    text(weight: "bold", tracking: 0.3pt, upper(dates)),
    // Right: page number.
    context text(
      weight: "bold",
      [#counter(page).display() / #counter(page).final().first()],
    ),
  )
}

// -----------------------------------------------------------------------------
// Building blocks
// -----------------------------------------------------------------------------

// A solid accent bar used to open chapters and headline blocks.
#let section-bar(body, fill-color: nos-green, size: 17pt) = block(
  width: 100%,
  fill: fill-color,
  inset: (x: 14pt, y: 11pt),
  radius: 2pt,
)[
  #text(font: brand-font, size: size, weight: "bold", fill: white)[#body]
]

// Generic card: light grey surface, light border.
#let card(body, fill-color: surface, accent-color: none) = block(
  width: 100%,
  fill: fill-color,
  stroke: if accent-color == none {
    0.6pt + border
  } else {
    (left: 3pt + accent-color, rest: 0.6pt + border)
  },
  radius: 2pt,
  inset: (x: 14pt, y: 12pt),
  above: 14pt,
  below: 14pt,
  body,
)

// Highlighted note. `tone` picks the accent: "primary", "secondary", "support".
#let callout(title: none, tone: "primary", body) = {
  let colour = if tone == "secondary" { nos-blue } else if tone == "support" { nos-cyan } else { nos-green }
  card(accent-color: colour)[
    #if title != none {
      text(font: brand-font, weight: "bold", size: 10.5pt, fill: colour)[#title]
      v(6pt)
    }
    #body
  ]
}

// A small labelled stat card, e.g. #fact("Prize pool", "€25 000+")
#let fact(label, value, tone: nos-green) = block(
  width: 100%,
  fill: white,
  stroke: 0.6pt + border,
  radius: 2pt,
  inset: 0pt,
  height: 66pt,
)[
  #block(width: 100%, fill: tone, height: 3pt)
  #block(inset: (x: 12pt, y: 10pt))[
    #text(size: 8pt, weight: "bold", tracking: 1pt, fill: muted, upper(label))
    #v(4pt)
    #text(font: brand-font, size: 13pt, weight: "bold")[#value]
  ]
]

// Row of stat cards: #facts(("Teams", "40"), ("Hours", "24"))
#let facts(..items) = {
  let tones = (nos-green, nos-blue, nos-cyan)
  grid(
    columns: items.pos().len() * (1fr,),
    column-gutter: 10pt,
    ..items.pos().enumerate().map(((i, it)) => fact(it.at(0), it.at(1), tone: tones.at(calc.rem(i, 3))))
  )
}

// Agenda / schedule line: #slot("09:00", "Doors open", note: "Main hall")
#let slot(time, what, note: none) = grid(
  columns: (2.6cm, 1fr),
  row-gutter: 0pt,
  text(weight: "bold", fill: nos-blue)[#time],
  [
    #text(weight: "bold")[#what]
    #if note != none { linebreak(); text(size: 9.5pt, fill: muted)[#note] }
  ],
)

// Thin horizontal separator.
#let divider = block(above: 18pt, below: 18pt, line(length: 100%, stroke: 0.6pt + border))

// -----------------------------------------------------------------------------
// Cover page
// -----------------------------------------------------------------------------

#let cover-page(title, subtitle, tagline, location, dates) = {
  set page(margin: (x: 2.6cm, top: 3.2cm, bottom: 2.4cm), footer: none, header: none)
  set text(fill: ink)

  image(logo-nos, height: 30pt)

  v(2.4cm)

  // Accent bars, primary to support.
  stack(
    dir: ltr,
    spacing: 4pt,
    rect(width: 54pt, height: 6pt, fill: nos-green, radius: 1pt),
    rect(width: 18pt, height: 6pt, fill: nos-blue, radius: 1pt),
    rect(width: 10pt, height: 6pt, fill: nos-cyan, radius: 1pt),
  )
  v(16pt)

  text(font: brand-font, size: 36pt, weight: "bold", hyphenate: false)[#title]
  if subtitle != none {
    v(10pt)
    text(size: 14pt, fill: muted)[#subtitle]
  }

  if tagline != none {
    v(24pt)
    block(width: 80%, par(leading: 0.75em, text(size: 11.5pt, fill: muted)[#tagline]))
  }

  v(1fr)

  card[
    #grid(
      columns: (auto, 1fr),
      column-gutter: 2.2cm,
      row-gutter: 10pt,
      text(size: 8pt, weight: "bold", tracking: 1pt, fill: muted)[EVENT],
      text(size: 11pt, weight: "bold")[#event-name],
      text(size: 8pt, weight: "bold", tracking: 1pt, fill: muted)[WHEN],
      text(size: 11pt, weight: "bold")[#dates],
      text(size: 8pt, weight: "bold", tracking: 1pt, fill: muted)[WHERE],
      text(size: 11pt, weight: "bold")[#location],
    )
  ]

  pagebreak(weak: true)
}

// -----------------------------------------------------------------------------
// Main template
// -----------------------------------------------------------------------------

#let hackathon-doc(
  title: "Hackathon Handbook",
  subtitle: none,
  tagline: none,
  location: "Lisbon, Portugal",
  dates: event-dates,
  cover: true,
  toc: true,
  body,
) = {
  set document(title: title, author: "NOS")

  set page(
    paper: "a4",
    fill: white,
    margin: (x: 2.6cm, top: 2.6cm, bottom: 2.2cm),
    header: header-bar,
    header-ascent: 18pt,
    footer: footer-bar(dates: dates),
  )

  set text(font: brand-font, size: 10.5pt, fill: ink, lang: "en", hyphenate: false)
  set par(justify: true, leading: 0.68em, spacing: 1.05em)
  set list(indent: 6pt, marker: text(fill: nos-green)[•])
  set enum(indent: 6pt)

  // Headings -----------------------------------------------------------------
  show heading: set text(font: brand-font, weight: "bold")

  // Level 1 — chapter opener with a primary accent bar.
  show heading.where(level: 1): it => {
    pagebreak(weak: true)
    block(above: 0pt, below: 18pt, section-bar(it.body))
  }

  // Level 2 — secondary accent bar on the left.
  show heading.where(level: 2): it => block(above: 20pt, below: 9pt)[
    #grid(
      columns: (4pt, 1fr),
      column-gutter: 9pt,
      rect(width: 4pt, height: 15pt, fill: nos-blue, radius: 1pt),
      text(size: 13pt)[#it.body],
    )
  ]

  // Level 3 — support accent, text only.
  show heading.where(level: 3): it => block(above: 15pt, below: 7pt)[
    #text(size: 11pt, fill: nos-cyan)[#it.body]
  ]

  // Inline elements ----------------------------------------------------------
  show link: it => text(fill: nos-blue, weight: "bold")[#underline(offset: 2pt, stroke: 0.4pt + nos-blue.lighten(50%))[#it]]

  show raw: set text(font: mono-font, size: 9pt)
  // Inline code: grey rounded chip so it stands out from body text.
  show raw.where(block: false): it => box(
    fill: rgb("#E9ECEF"),
    stroke: 0.5pt + rgb("#D3D8DD"),
    radius: 3pt,
    inset: (x: 3.5pt),
    outset: (y: 3pt),
    text(weight: "bold", fill: nos-blue, it),
  )
  show raw.where(block: true): it => card(fill-color: surface, accent-color: nos-cyan, it)

  // Tables as light-bordered blocks with a grey header row.
  set table(
    stroke: 0.6pt + border,
    inset: (x: 9pt, y: 7pt),
    fill: (x, y) => if y == 0 { surface },
  )
  show table.cell.where(y: 0): set text(weight: "bold", size: 9.5pt)

  show figure.caption: set text(size: 9pt, fill: muted)

  // Front matter -------------------------------------------------------------
  if cover {
    cover-page(title, subtitle, tagline, location, dates)
  }

  if toc {
    section-bar("Contents", size: 15pt)
    v(14pt)
    show outline.entry.where(level: 1): it => {
      v(7pt, weak: true)
      text(weight: "bold", it)
    }
    outline(title: none, depth: 2, indent: 1.2em)
    pagebreak(weak: true)
  }

  body
}
