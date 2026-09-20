# -*- coding: utf-8 -*-
"""SVG diagrams for the Phase 1 progress report."""

BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8981"
RULE = "#dcdbd4"
PANEL = "#f5f4ef"
RED = "#e34948"

DEFS = f'''
<defs>
  <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
          orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/>
  </marker>
  <marker id="ahb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
          orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/>
  </marker>
  <marker id="aho" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
          orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{ORANGE}"/>
  </marker>
  <marker id="ahm" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
          orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/>
  </marker>
  <pattern id="hatch" width="7" height="7" patternTransform="rotate(45)"
           patternUnits="userSpaceOnUse">
    <rect width="7" height="7" fill="{RED}" opacity="0.10"/>
    <line x1="0" y1="0" x2="0" y2="7" stroke="{RED}" stroke-width="2.2" opacity="0.35"/>
  </pattern>
</defs>
'''


def box(x, y, w, h, title, sub=None, fill="#ffffff", stroke=INK, dash=None,
        tsize=14, ssize=11.5, tcol=INK, scol=INK2, r=4, sw=1.6):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    out = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
           f'stroke="{stroke}" stroke-width="{sw}"{d}/>')
    if sub:
        out += (f'<text x="{x + w/2}" y="{y + h/2 - 5}" text-anchor="middle" '
                f'font-size="{tsize}" font-weight="600" fill="{tcol}">{title}</text>')
        for i, line in enumerate(sub.split("|")):
            out += (f'<text x="{x + w/2}" y="{y + h/2 + 13 + i*14}" text-anchor="middle" '
                    f'font-size="{ssize}" fill="{scol}">{line}</text>')
    else:
        out += (f'<text x="{x + w/2}" y="{y + h/2 + 5}" text-anchor="middle" '
                f'font-size="{tsize}" font-weight="600" fill="{tcol}">{title}</text>')
    return out


def arrow(x1, y1, x2, y2, marker="ah", color=INK2, dash=None, sw=1.8):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" marker-end="url(#{marker})"{d}/>')


def label(x, y, text, size=11.5, col=INK2, anchor="middle", weight="400", style=""):
    st = f' font-style="{style}"' if style else ""
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" fill="{col}"{st}>{text}</text>')


def wrap(vb, body):
    return f'<div class="svgfig"><svg viewBox="{vb}" xmlns="http://www.w3.org/2000/svg" role="img">{DEFS}{body}</svg></div>'


# ============================================================ D1
def d_reactive_proactive():
    def X(t):
        return 110 + (t + 330) * 1.5556

    s = []
    s.append(label(0, 24, "Why a 60&#8211;90 second provisioning delay decides the whole argument",
                   15, INK, "start", "600"))
    s.append(f'<text x="0" y="44" font-size="11.5" fill="{INK2}">The spike arrives at t = 0. '
             f'A reactive scaler cannot start provisioning until then; a forecast starts the clock five minutes earlier.</text>')

    # spike marker
    s.append(f'<line x1="{X(0)}" y1="62" x2="{X(0)}" y2="272" stroke="{RED}" stroke-width="2" stroke-dasharray="5 4"/>')
    s.append(label(X(0), 76, "TRAFFIC SPIKE HITS", 11, RED, "middle", "700"))

    # --- reactive lane
    ly = 100
    s.append(label(0, ly + 20, "REACTIVE", 12, INK, "start", "700"))
    s.append(label(0, ly + 36, "acts on measured CPU", 10.5, MUTED, "start"))
    s.append(f'<line x1="110" y1="{ly+26}" x2="950" y2="{ly+26}" stroke="{RULE}" stroke-width="1.5"/>')
    # provisioning bar
    s.append(f'<rect x="{X(0)}" y="{ly+8}" width="{X(90)-X(0)}" height="36" rx="3" fill="{ORANGE}" opacity="0.9"/>')
    s.append(label((X(0)+X(90))/2, ly + 31, "request &#183; boot &#183; join pool", 11, "#ffffff", "middle", "600"))
    # degraded region
    s.append(f'<rect x="{X(0)}" y="{ly+48}" width="{X(90)-X(0)}" height="16" fill="url(#hatch)" stroke="{RED}" stroke-width="0.8"/>')
    s.append(label((X(0)+X(90))/2, ly + 78, "90 s of degraded service &#8212; users feel this", 11, RED, "middle", "600"))
    s.append(f'<circle cx="{X(90)}" cy="{ly+26}" r="6" fill="{AQUA}" stroke="#fff" stroke-width="2"/>')
    s.append(label(X(90) + 12, ly + 15, "capacity ready &#8212; too late", 11, INK2, "start"))

    # --- proactive lane
    py = 196
    s.append(label(0, py + 20, "PROACTIVE", 12, BLUE, "start", "700"))
    s.append(label(0, py + 36, "acts on LSTM forecast", 10.5, MUTED, "start"))
    s.append(f'<line x1="110" y1="{py+26}" x2="950" y2="{py+26}" stroke="{RULE}" stroke-width="1.5"/>')
    s.append(f'<rect x="{X(-300)}" y="{py+8}" width="{X(-210)-X(-300)}" height="36" rx="3" fill="{BLUE}" opacity="0.9"/>')
    s.append(label((X(-300)+X(-210))/2, py + 31, "request &#183; boot &#183; join", 11, "#ffffff", "middle", "600"))
    s.append(f'<circle cx="{X(-300)}" cy="{py+26}" r="6" fill="{BLUE}" stroke="#fff" stroke-width="2"/>')
    s.append(label(X(-300), py - 4, "LSTM predicts the spike", 11, BLUE, "middle", "600"))
    s.append(f'<circle cx="{X(-210)}" cy="{py+26}" r="6" fill="{AQUA}" stroke="#fff" stroke-width="2"/>')
    s.append(f'<rect x="{X(-210)}" y="{py+48}" width="{X(180)-X(-210)}" height="16" rx="2" fill="{AQUA}" opacity="0.22"/>')
    s.append(label((X(-210)+X(180))/2, py + 78, "capacity already in place before the spike lands &#8212; users feel nothing",
                   11, "#0d6b48", "middle", "600"))

    # axis
    s.append(f'<line x1="110" y1="292" x2="950" y2="292" stroke="{INK2}" stroke-width="1.2"/>')
    for t, lab in [(-300, "&#8722;5 min"), (-210, "&#8722;3.5 min"), (0, "0"), (90, "+90 s"), (180, "+3 min")]:
        s.append(f'<line x1="{X(t)}" y1="292" x2="{X(t)}" y2="298" stroke="{INK2}" stroke-width="1.2"/>')
        s.append(label(X(t), 312, lab, 10.5, INK2))
    s.append(label(950, 332, "time", 11, MUTED, "end", "400", "italic"))
    return wrap("0 0 1000 340", "".join(s))


# ============================================================ D2
def d_phase_seam():
    s = []
    s.append(label(0, 22, "The Phase 2 insertion point, fixed before any model code is written",
                   15, INK, "start", "600"))
    y = 62
    s.append(box(0, y, 150, 62, "Input window", "60 timesteps &#215; 3", fill=PANEL))
    s.append(arrow(152, y + 31, 196, y + 31))
    s.append(box(198, y, 170, 62, "LSTM layers", "sequence &#8594; hidden state", fill="#fff", stroke=BLUE))
    s.append(arrow(370, y + 31, 470, y + 31, "ahb", BLUE))
    # seam
    s.append(f'<line x1="470" y1="{y-16}" x2="470" y2="{y+150}" stroke="{ORANGE}" stroke-width="2.4" stroke-dasharray="7 5"/>')
    s.append(label(470, y - 24, "THE SEAM", 11.5, ORANGE, "middle", "700"))
    s.append(arrow(472, y + 31, 560, y + 31, "ahb", BLUE))
    s.append(box(562, y, 150, 62, "Dense layer", "hidden &#8594; 3 values", fill="#fff", stroke=BLUE))
    s.append(arrow(714, y + 31, 758, y + 31))
    s.append(box(760, y, 170, 62, "Prediction", "cpu, mem, net at t+1", fill=PANEL))

    s.append(label(240, y + 88, "PHASE 1 (this semester) &#8212; hidden state passes straight through",
                   11.5, BLUE, "middle", "600"))

    # phase 2 branch
    y2 = y + 118
    s.append(f'<path d="M 470 {y+62} L 470 {y2+20} " stroke="{MUTED}" stroke-width="0" />')
    s.append(box(360, y2, 220, 56, "4-qubit PennyLane circuit",
                 "angle encode &#183; entangle &#183; measure",
                 fill="#fff", stroke=MUTED, dash="6 4", tsize=13, ssize=11))
    s.append(f'<path d="M 420 {y+93} C 420 {y2-6}, 420 {y2-6}, 420 {y2-2}" fill="none" stroke="{MUTED}" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#ahm)"/>')
    s.append(f'<path d="M 520 {y2+56} C 520 {y2+70}, 620 {y2+70}, 620 {y+126}" fill="none" stroke="{MUTED}" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#ahm)"/>')
    s.append(label(636, y2 + 24, "PHASE 2 (next semester, BTP) &#8212; the circuit is spliced in here.",
                   11.5, INK2, "start", "600"))
    s.append(label(636, y2 + 42, "Everything upstream and downstream is untouched, which is", 11, MUTED, "start"))
    s.append(label(636, y2 + 58, "what makes the Phase 1 result a valid controlled baseline.", 11, MUTED, "start"))
    return wrap("0 0 1000 265", "".join(s))


# ============================================================ D3
def d_pipeline():
    s = []
    s.append(label(0, 22, "End-to-end data flow &#8212; solid outline is built and verified, dashed is scheduled work",
                   15, INK, "start", "600"))

    # row 1
    y1 = 54
    s.append(box(0, y1, 150, 56, "data/raw/*.csv", "1,250 VM traces", fill=PANEL, tsize=12.5, ssize=10.5))
    s.append(arrow(152, y1 + 28, 194, y1 + 28))
    s.append(box(196, y1, 150, 56, "explore.py", "survey all 1,250", fill="#fff", stroke=BLUE, tsize=12.5, ssize=10.5))
    s.append(arrow(348, y1 + 28, 390, y1 + 28))
    s.append(box(392, y1, 160, 56, "vm_survey.csv", "ranked by volatility", fill=PANEL, tsize=12.5, ssize=10.5))
    s.append(arrow(554, y1 + 28, 596, y1 + 28))
    s.append(box(598, y1, 170, 56, "Human decision", "&#8220;use VM 270&#8221;", fill="#fff", stroke=ORANGE, tsize=12.5, ssize=10.5))
    s.append(label(786, y1 + 24, "Run once, by hand.", 10.5, MUTED, "start", "400", "italic"))
    s.append(label(786, y1 + 40, "The chosen ID is then fixed.", 10.5, MUTED, "start", "400", "italic"))

    # row 2
    y2 = 146
    s.append(f'<path d="M 683 {y1+56} C 683 {y2-18}, 240 {y2-24}, 240 {y2-2}" fill="none" stroke="{ORANGE}" stroke-width="1.6" marker-end="url(#aho)"/>')
    s.append(box(160, y2, 160, 56, "load_data.py", "clean one VM", fill="#fff", stroke=BLUE, tsize=12.5, ssize=10.5))
    s.append(box(160, y2 + 74, 160, 56, "generate_data.py", "synthetic spikes", fill="#fff", stroke=MUTED,
                 dash="6 4", tsize=12.5, ssize=10.5, tcol=MUTED))
    s.append(arrow(322, y2 + 28, 372, y2 + 28))
    s.append(arrow(322, y2 + 102, 372, y2 + 102, "ahm", MUTED, "5 4"))
    s.append(box(374, y2, 190, 56, "270_clean.csv", "8,640 rows &#183; 30 days", fill=PANEL, tsize=12.5, ssize=10.5))
    s.append(box(374, y2 + 74, 190, 56, "synthetic.csv", "not yet built", fill="#fff", stroke=MUTED,
                 dash="6 4", tsize=12.5, ssize=10.5, tcol=MUTED, scol=MUTED))

    # the shared format brace
    s.append(f'<path d="M 574 {y2+8} L 586 {y2+8} L 586 {y2+122} L 574 {y2+122}" fill="none" stroke="{AQUA}" stroke-width="2"/>')
    s.append(f'<line x1="586" y1="{y2+65}" x2="606" y2="{y2+65}" stroke="{AQUA}" stroke-width="2"/>')
    s.append(label(612, y2 + 55, "Identical four-column format:", 11, "#0d6b48", "start", "700"))
    s.append(label(612, y2 + 71, "datetime | cpu | mem | net", 11, "#0d6b48", "start"))
    s.append(label(612, y2 + 87, "&#8212; so everything below is source-agnostic.", 10.5, MUTED, "start", "400", "italic"))

    # row 3
    y3 = 306
    s.append(f'<path d="M 469 {y2+130} C 469 {y3-22}, 300 {y3-22}, 300 {y3-2}" fill="none" stroke="{INK2}" stroke-width="1.8" marker-end="url(#ah)"/>')
    s.append(box(180, y3, 240, 60, "preprocessing.py",
                 "split &#8594; scale &#8594; window &#8594; batch", fill="#fff", stroke=BLUE, tsize=13, ssize=11))
    s.append(arrow(422, y3 + 30, 466, y3 + 30))
    s.append(box(468, y3, 175, 60, "3 DataLoaders", "94 / 20 / 20 batches", fill=PANEL, tsize=12.5, ssize=10.5))
    s.append(box(660, y3, 175, 60, "scaler.joblib", "for inverse transform", fill=PANEL, tsize=12.5, ssize=10.5))
    s.append(f'<path d="M 555 {y3+60} C 555 {y3+78}, 747 {y3+78}, 747 {y3+62}" fill="none" stroke="{RULE}" stroke-width="0"/>')
    s.append(arrow(645, y3 + 30, 657, y3 + 30))

    # row 4 future
    y4 = 402
    s.append(f'<line x1="0" y1="{y4-16}" x2="1000" y2="{y4-16}" stroke="{RULE}" stroke-width="1.4" stroke-dasharray="4 4"/>')
    s.append(label(0, y4 + 4, "NOT YET BUILT", 10.5, MUTED, "start", "700"))
    fut = [("1.4  LSTM", 120), ("1.5  Evaluation", 320), ("1.6  Scaling engine", 520), ("1.7  Dashboard", 740)]
    for name, x in fut:
        s.append(box(x, y4 - 8, 170, 44, name, None, fill="#fff", stroke=MUTED, dash="6 4",
                     tsize=12, tcol=MUTED))
        if x != 740:
            s.append(arrow(x + 172, y4 + 14, x + 198, y4 + 14, "ahm", MUTED, "5 4"))
    s.append(f'<path d="M 555 {y3+60} C 555 {y4-30}, 205 {y4-30}, 205 {y4-10}" fill="none" stroke="{MUTED}" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#ahm)"/>')
    return wrap("0 0 1000 460", "".join(s))


# ============================================================ D4
def d_columns():
    s = []
    s.append(label(0, 22, "From eleven raw columns to the four-column canonical format",
                   15, INK, "start", "600"))
    raw = [
        ("Timestamp [ms]", "used", "actually Unix seconds"),
        ("CPU cores", "drop", ""),
        ("CPU capacity provisioned [MHZ]", "drop", ""),
        ("CPU usage [MHZ]", "drop", ""),
        ("CPU usage [%]", "used", ""),
        ("Memory capacity provisioned [KB]", "used", "denominator"),
        ("Memory usage [KB]", "used", "numerator"),
        ("Disk read throughput [KB/s]", "drop", ""),
        ("Disk write throughput [KB/s]", "drop", ""),
        ("Network received throughput [KB/s]", "used", ""),
        ("Network transmitted throughput [KB/s]", "used", ""),
    ]
    y0 = 54
    rh = 27
    s.append(label(0, y0 - 8, "RAW BITBRAINS CSV  (semicolon-delimited)", 10.5, MUTED, "start", "700"))
    ypos = {}
    for i, (name, kind, note) in enumerate(raw):
        y = y0 + i * rh
        used = kind == "used"
        fill = "#ffffff" if used else "#f2f1ec"
        stroke = BLUE if used else RULE
        col = INK if used else MUTED
        s.append(f'<rect x="0" y="{y}" width="330" height="{rh-5}" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="{1.4 if used else 1}"/>')
        s.append(label(9, y + 15, name, 11, col, "start", "600" if used else "400"))
        if note:
            s.append(label(324, y + 15, note, 9.5, MUTED, "end", "400", "italic"))
        if not used:
            s.append(f'<line x1="9" y1="{y+11}" x2="{9 + len(name)*5.6}" y2="{y+11}" stroke="{MUTED}" stroke-width="1"/>')
        ypos[name] = y + (rh - 5) / 2

    # outputs
    outs = [
        ("datetime", "index &#8212; strict 5-minute steps", ["Timestamp [ms]"], INK2, y0 + 8),
        ("cpu", "CPU usage [%], clipped to 0&#8211;100", ["CPU usage [%]"], BLUE, y0 + 78),
        ("mem", "used / capacity &#215; 100, clipped", ["Memory capacity provisioned [KB]", "Memory usage [KB]"], ORANGE, y0 + 148),
        ("net", "received + transmitted", ["Network received throughput [KB/s]", "Network transmitted throughput [KB/s]"], AQUA, y0 + 218),
    ]
    s.append(label(660, y0 - 8, "CANONICAL OUTPUT", 10.5, MUTED, "start", "700"))
    for name, desc, sources, col, y in outs:
        s.append(f'<rect x="660" y="{y}" width="340" height="52" rx="4" fill="#fff" stroke="{col}" stroke-width="1.8"/>')
        s.append(label(674, y + 22, name, 13.5, col, "start", "700"))
        s.append(label(674, y + 40, desc, 10.8, INK2, "start"))
        for src in sources:
            s.append(f'<path d="M 332 {ypos[src]} C 480 {ypos[src]}, 500 {y+26}, 656 {y+26}" fill="none" stroke="{col}" stroke-width="1.5" opacity="0.75" marker-end="url(#ah)"/>')

    s.append(label(0, y0 + 11 * rh + 22, "Six columns discarded: CPU core count and MHz capacity are static allocation figures, not load;",
                   10.8, MUTED, "start"))
    s.append(label(0, y0 + 11 * rh + 38, "the disk columns are left out because the project forecasts and scales only CPU, memory and network.",
                   10.8, MUTED, "start"))
    return wrap("0 0 1000 400", "".join(s))


# ============================================================ D5
def d_funnel():
    s = []
    s.append(label(0, 22, "VM selection funnel &#8212; 1,250 candidates down to one training workload",
                   15, INK, "start", "600"))
    stages = [
        ("1,250", "VM files in", "data/raw/", MUTED, 220),
        ("1,177", "have &#8805; 2,000 rows", "73 too short to judge", MUTED, 195),
        ("158", "mean CPU in 20&#8211;60%", "1,019 idle or saturated", BLUE, 150),
        ("138", "all parts move,", "memory + network alive", BLUE, 115),
        ("1", "highest volatility", "VM 270, std 48.36", ORANGE, 80),
    ]
    x = 0
    y_mid = 150
    for i, (big, l1, l2, col, h) in enumerate(stages):
        w = 172
        s.append(f'<rect x="{x}" y="{y_mid - h/2}" width="{w}" height="{h}" rx="5" fill="{col}" opacity="0.13"/>')
        s.append(f'<rect x="{x}" y="{y_mid - h/2}" width="{w}" height="{h}" rx="5" fill="none" stroke="{col}" stroke-width="1.8"/>')
        s.append(label(x + w/2, y_mid - 4, big, 25, col, "middle", "700"))
        s.append(label(x + w/2, y_mid + 18, l1, 10.5, INK, "middle", "600"))
        s.append(label(x + w/2, y_mid + 34, l2, 9.5, MUTED, "middle"))
        if i < len(stages) - 1:
            s.append(arrow(x + w + 6, y_mid, x + w + 32, y_mid, "ahm", MUTED))
        x += w + 35
    s.append(label(0, 288, "The 20&#8211;60% band is not arbitrary: below it the model learns to output a constant near zero, above it a constant near 100.",
                   11, INK2, "start"))
    s.append(label(0, 306, "Ranking by standard deviation asks &#8220;does its load actually move?&#8221;, and the last check makes sure it keeps moving in the test period too.",
                   11, INK2, "start"))
    return wrap("0 0 1000 320", "".join(s))


# ============================================================ D6
def d_loader():
    s = []
    s.append(label(0, 22, "load_vm() &#8212; six operations, and why the order matters",
                   15, INK, "start", "600"))
    steps = [
        ("1", "Read the semicolon-delimited CSV", "sep=';' &#8212; not a comma file"),
        ("2", "Strip and rename the column headers", "raw headers carry stray whitespace"),
        ("3", "Parse the timestamp, set it as the index", "detects seconds vs milliseconds by magnitude"),
        ("4", "Build cpu, mem, net; clip to valid ranges", "mem = used / capacity &#215; 100"),
        ("5", "Resample onto a strict 5-minute grid", "raw spacing drifts; .resample('5min').mean()"),
        ("6", "Handle the gaps that resampling exposed", "see the decision below"),
    ]
    y = 50
    for num, title, sub in steps:
        s.append(f'<rect x="0" y="{y}" width="470" height="42" rx="4" fill="#fff" stroke="{BLUE}" stroke-width="1.5"/>')
        s.append(f'<rect x="0" y="{y}" width="30" height="42" rx="4" fill="{BLUE}"/>')
        s.append(f'<rect x="22" y="{y}" width="8" height="42" fill="{BLUE}"/>')
        s.append(label(15, y + 26, num, 14, "#ffffff", "middle", "700"))
        s.append(label(42, y + 18, title, 11.8, INK, "start", "600"))
        s.append(label(42, y + 33, sub, 10.3, MUTED, "start"))
        if num != "6":
            s.append(arrow(235, y + 43, 235, y + 51, "ahb", BLUE, sw=1.5))
        y += 51

    # Step 6 feeds the decision. The connector leaves step 6's right edge, runs up a
    # clear channel at x=520 (left of every box on this side) and enters the diamond's
    # left vertex; the two outcomes then leave from the bottom and right vertices, so
    # no branch shares a vertex with the inbound arrow.
    cx, cy = 720, 100
    hw, hh = 120, 44
    s.append(f'<path d="M 472 326 L 520 326 L 520 {cy} L {cx-hw-4} {cy}" fill="none" '
             f'stroke="{BLUE}" stroke-width="1.6" marker-end="url(#ahb)"/>')

    s.append(f'<path d="M {cx} {cy-hh} L {cx+hw} {cy} L {cx} {cy+hh} L {cx-hw} {cy} Z" fill="#fff" stroke="{ORANGE}" stroke-width="1.8"/>')
    s.append(label(cx, cy - 6, "How long is", 11.8, INK, "middle", "600"))
    s.append(label(cx, cy + 10, "the gap?", 11.8, INK, "middle", "600"))

    # short gap -> forward-fill (leaves the bottom vertex)
    s.append(f'<path d="M {cx} {cy+hh} L {cx} 176 L 665 176 L 665 194" fill="none" stroke="{AQUA}" stroke-width="1.8" marker-end="url(#ah)"/>')
    s.append(label(cx + 10, 162, "&#8804; 3 steps (15 min)", 10.8, "#0d6b48", "start", "600"))
    s.append(f'<rect x="560" y="196" width="210" height="58" rx="4" fill="#fff" stroke="{AQUA}" stroke-width="1.6"/>')
    s.append(label(665, 218, "Forward-fill", 12, "#0d6b48", "middle", "700"))
    s.append(label(665, 235, "carrying the last value 15 min", 10.3, INK2, "middle"))
    s.append(label(665, 249, "is a small, safe assumption", 10.3, INK2, "middle"))

    # long gap -> drop (leaves the right vertex)
    s.append(f'<path d="M {cx+hw} {cy} L 895 {cy} L 895 194" fill="none" stroke="{RED}" stroke-width="1.8" marker-end="url(#ah)"/>')
    s.append(label(899, cy - 8, "&gt; 3 steps", 10.8, RED, "start", "600"))
    s.append(f'<rect x="790" y="196" width="210" height="58" rx="4" fill="#fff" stroke="{RED}" stroke-width="1.6"/>')
    s.append(label(895, 218, "Warn and drop the rows", 12, RED, "middle", "700"))
    s.append(label(895, 235, "interpolating hours would", 10.3, INK2, "middle"))
    s.append(label(895, 249, "fabricate load that never happened", 10.3, INK2, "middle"))

    # starts at x=560 so the step-6 connector's channel at x=520 stays clear
    s.append(f'<rect x="560" y="300" width="440" height="48" rx="4" fill="{PANEL}" stroke="{RULE}" stroke-width="1.2"/>')
    s.append(label(780, 320, "On VM 270: 21 short gaps filled, 0 rows dropped", 11.5, INK, "middle", "600"))
    s.append(label(780, 337, "&#8212; the VM ran for the whole month, so nothing had to be deleted", 10.5, MUTED, "middle"))
    return wrap("0 0 1000 372", "".join(s))


# ============================================================ D7
def d_preprocess():
    s = []
    s.append(label(0, 22, "The preprocessing pipeline &#8212; five stages whose order is the entire point",
                   15, INK, "start", "600"))

    stages = [
        ("A", "SPLIT", "by time position", "70% / 15% / 15%|never shuffle the raw series", BLUE),
        ("B", "SCALE", "fit on train only", "MinMaxScaler|val and test are transformed, never fitted", ORANGE),
        ("C", "WINDOW", "inside each split", "X: (N, 60, 3)|y: (N, 3)", AQUA),
        ("D", "BATCH", "into DataLoaders", "batch 64|shuffle train only", BLUE),
        ("E", "VERIFY", "before training", "shapes, round-trip,|leakage evidence", ORANGE),
    ]
    x = 0
    y = 58
    w = 178
    for i, (letter, name, tag, sub, col) in enumerate(stages):
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="118" rx="5" fill="#fff" stroke="{col}" stroke-width="1.8"/>')
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="5" fill="{col}"/>')
        s.append(f'<rect x="{x}" y="{y+20}" width="{w}" height="10" fill="{col}"/>')
        s.append(label(x + 14, y + 21, letter, 14, "#ffffff", "start", "700"))
        s.append(label(x + w/2 + 8, y + 21, name, 13, "#ffffff", "middle", "700"))
        s.append(label(x + w/2, y + 50, tag, 11.2, INK, "middle", "600"))
        for j, line in enumerate(sub.split("|")):
            s.append(label(x + w/2, y + 70 + j * 15, line, 10.4, INK2, "middle"))
        if i < 4:
            s.append(arrow(x + w + 4, y + 59, x + w + 22, y + 59))
        x += w + 27

    # the warning strip
    wy = 200
    s.append(f'<rect x="0" y="{wy}" width="1000" height="70" rx="5" fill="#fdf0ea" stroke="{ORANGE}" stroke-width="1.6"/>')
    s.append(label(16, wy + 24, "IF A AND B ARE SWAPPED, NOTHING CRASHES &#8212; AND EVERY METRIC AFTERWARDS IS A LIE",
                   11.5, "#9c3d13", "start", "700"))
    s.append(label(16, wy + 44, "Scaling before splitting lets the test set's minimum and maximum set the transform parameters. The model has then indirectly",
                   10.8, INK2, "start"))
    s.append(label(16, wy + 60, "seen test-set information during training. The original project roadmap has this order wrong; this implementation does not.",
                   10.8, INK2, "start"))

    # outputs
    oy = 292
    s.append(label(0, oy - 6, "WHAT COMES OUT", 10.5, MUTED, "start", "700"))
    outs = [
        ("train_loader", "5,988 windows &#183; 94 batches &#183; shuffled", BLUE),
        ("val_loader", "1,236 windows &#183; 20 batches &#183; ordered", ORANGE),
        ("test_loader", "1,236 windows &#183; 20 batches &#183; ordered", AQUA),
        ("scaler.joblib", "saved to models/ for the dashboard", INK2),
    ]
    ox = 0
    for name, desc, col in outs:
        s.append(f'<rect x="{ox}" y="{oy}" width="238" height="48" rx="4" fill="{PANEL}" stroke="{col}" stroke-width="1.4"/>')
        s.append(label(ox + 12, oy + 20, name, 12, col, "start", "700"))
        s.append(label(ox + 12, oy + 37, desc, 10.3, INK2, "start"))
        ox += 254
    return wrap("0 0 1000 350", "".join(s))


# ============================================================ D8
def d_leakage():
    s = []
    s.append(label(0, 22, "Why the scaler is fitted on the training split alone",
                   15, INK, "start", "600"))

    def series(x0, y0, col_tr, col_te, tr_w, te_w):
        out = f'<rect x="{x0}" y="{y0}" width="{tr_w}" height="26" rx="3" fill="{col_tr}" opacity="0.85"/>'
        out += f'<rect x="{x0+tr_w}" y="{y0}" width="{te_w}" height="26" rx="3" fill="{col_te}" opacity="0.85"/>'
        return out

    # WRONG panel
    s.append(f'<rect x="0" y="42" width="480" height="238" rx="5" fill="#fdf0f0" stroke="{RED}" stroke-width="1.8"/>')
    s.append(label(18, 68, "&#10007;  WRONG &#8212; scale, then split", 13, RED, "start", "700"))
    s.append(label(18, 90, "scaler.fit_transform(whole_series)", 10.8, INK2, "start"))
    s.append(series(18, 102, MUTED, MUTED, 300, 144))
    s.append(label(168, 119, "one scaler fitted over everything", 10.5, "#fff", "middle", "600"))
    s.append(f'<path d="M 430 116 C 452 116, 452 150, 300 150" fill="none" stroke="{RED}" stroke-width="1.6" marker-end="url(#ah)"/>')
    s.append(label(18, 172, "The maximum inside the test set helped decide the", 10.8, INK, "start"))
    s.append(label(18, 188, "transform. The model has now indirectly seen the", 10.8, INK, "start"))
    s.append(label(18, 204, "test data before it was ever evaluated on it.", 10.8, INK, "start"))
    s.append(f'<rect x="18" y="218" width="444" height="46" rx="4" fill="#fff" stroke="{RED}" stroke-width="1.2"/>')
    s.append(label(30, 238, "Symptom: test data also scales to a tidy 0.00&#8211;1.00.", 10.8, RED, "start", "600"))
    s.append(label(30, 254, "The tidiness is the tell.", 10.8, INK2, "start"))

    # RIGHT panel
    s.append(f'<rect x="520" y="42" width="480" height="238" rx="5" fill="#eef8f3" stroke="{AQUA}" stroke-width="1.8"/>')
    s.append(label(538, 68, "&#10003;  RIGHT &#8212; split, then scale", 13, "#0d6b48", "start", "700"))
    s.append(label(538, 90, "fit_transform(train)  &#183;  transform(val)  &#183;  transform(test)", 10.5, INK2, "start"))
    s.append(series(538, 102, BLUE, AQUA, 300, 144))
    s.append(label(688, 119, "scaler fitted here only", 10.5, "#fff", "middle", "600"))
    s.append(label(910, 119, "unseen", 10.5, "#fff", "middle", "600"))
    s.append(f'<line x1="838" y1="96" x2="838" y2="134" stroke="{INK}" stroke-width="2" stroke-dasharray="4 3"/>')
    s.append(label(538, 172, "The scaler's parameters come from the past only.", 10.8, INK, "start"))
    s.append(label(538, 188, "Test values are free to fall outside the 0&#8211;1 range,", 10.8, INK, "start"))
    s.append(label(538, 204, "and on this dataset they do.", 10.8, INK, "start"))
    s.append(f'<rect x="538" y="218" width="444" height="46" rx="4" fill="#fff" stroke="{AQUA}" stroke-width="1.2"/>')
    s.append(label(550, 238, "Measured: train 0.00&#8211;1.00, test 0.00&#8211;1.91.", 10.8, "#0d6b48", "start", "600"))
    s.append(label(550, 254, "The overshoot is the proof of no leakage.", 10.8, INK2, "start"))
    return wrap("0 0 1000 292", "".join(s))


# ============================================================ D9
def d_windows():
    s = []
    s.append(label(0, 22, "Sliding windows: 60 steps of history predict the 61st",
                   15, INK, "start", "600"))
    s.append(label(0, 42, "Drawn with a window of 5 for legibility; the real window is 60 steps (5 hours) and the real target is 1 step (5 minutes) ahead.",
                   10.8, MUTED, "start"))

    cw = 46
    x0 = 96
    n = 12
    ty = 66
    # timeline of cells
    s.append(label(88, ty + 20, "series", 10.8, INK2, "end", "600"))
    for i in range(n):
        s.append(f'<rect x="{x0 + i*cw}" y="{ty}" width="{cw-4}" height="30" rx="3" fill="{PANEL}" stroke="{RULE}" stroke-width="1.2"/>')
        s.append(label(x0 + i*cw + (cw-4)/2, ty + 20, f"t{i}", 10.8, INK2))

    rows = [(0, BLUE), (1, ORANGE), (2, AQUA)]
    ry = 120
    for k, (off, col) in enumerate(rows):
        y = ry + k * 52
        s.append(label(88, y + 21, f"sample {k}", 10.8, INK2, "end", "600"))
        for i in range(5):
            xx = x0 + (i + off) * cw
            s.append(f'<rect x="{xx}" y="{y}" width="{cw-4}" height="32" rx="3" fill="{col}" opacity="0.85"/>')
            s.append(label(xx + (cw-4)/2, y + 21, f"t{i+off}", 10.8, "#ffffff", "middle", "600"))
        # target
        xt = x0 + (5 + off) * cw
        s.append(f'<rect x="{xt}" y="{y}" width="{cw-4}" height="32" rx="3" fill="#fff" stroke="{col}" stroke-width="2.2" stroke-dasharray="4 3"/>')
        s.append(label(xt + (cw-4)/2, y + 21, f"t{5+off}", 10.8, col, "middle", "700"))
        if k == 0:
            s.append(label(x0 + 2*cw + 20, y - 6, "X  &#8212;  the 60&#215;3 input window", 10.8, BLUE, "middle", "600"))
            s.append(label(xt + 96, y - 6, "y  &#8212;  the target, all 3 metrics", 10.8, BLUE, "middle", "600"))
        s.append(label(x0 + 12*cw + 14, y + 21, f"X[{k}] &#8594; y[{k}]", 11, INK2, "start"))

    fy = 288
    s.append(f'<rect x="0" y="{fy}" width="1000" height="66" rx="5" fill="{PANEL}" stroke="{RULE}" stroke-width="1.2"/>')
    s.append(label(18, fy + 22, "The window slides one step at a time, so consecutive samples overlap by 59 of their 60 steps.", 11, INK, "start", "600"))
    s.append(label(18, fy + 40, "Two consequences: a split of R rows yields exactly R &#8722; 60 windows (the first 60 rows can only ever be history, never a target),", 10.6, INK2, "start"))
    s.append(label(18, fy + 56, "and windowing must run separately per split &#8212; one window straddling the train/test boundary would leak the future into training.", 10.6, INK2, "start"))
    return wrap("0 0 1000 366", "".join(s))


DIAGRAMS = {
    "reactive_proactive": d_reactive_proactive,
    "phase_seam": d_phase_seam,
    "pipeline": d_pipeline,
    "columns": d_columns,
    "funnel": d_funnel,
    "loader": d_loader,
    "preprocess": d_preprocess,
    "leakage": d_leakage,
    "windows": d_windows,
}
