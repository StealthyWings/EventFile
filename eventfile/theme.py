"""A dark slate + bright green look in the style of MongoDB's site.

Only fonts that ship with Windows are used (Bahnschrift, Segoe UI, Cascadia Mono / Consolas),
so the page never fetches anything from the internet.
"""

import inspect

import gradio as gr

SLATE = "#001E2B"
CARD = "#03222F"
CARD_BORDER = "#1C3A48"
INPUT = "#112733"
INPUT_BORDER = "#3D4F58"
TEXT = "#E8EDEB"
TEXT_SOFT = "#C1C7C6"
TEXT_MUTED = "#889397"
GREEN = "#00ED64"
GREEN_HOVER = "#71F6BA"
GREEN_DEEP = "#023430"

GREENS = gr.themes.Color(
    c50="#E3FCF7", c100="#C0FAE6", c200="#71F6BA", c300="#00ED64", c400="#00ED64",
    c500="#00ED64", c600="#00A35C", c700="#00684A", c800="#023430", c900="#012A26",
    c950="#001E2B", name="leaf_green",
)
SLATES = gr.themes.Color(
    c50="#F9FBFA", c100="#E8EDEB", c200="#C1C7C6", c300="#889397", c400="#5C6C75",
    c500="#3D4F58", c600="#1C2D38", c700="#112733", c800="#0A2632", c900="#001E2B",
    c950="#00141C", name="slate",
)

# Same values in light and dark mode, so the page looks the same whatever the OS setting.
COLORS = dict(
    body_background_fill=SLATE,
    body_text_color=TEXT,
    body_text_color_subdued=TEXT_MUTED,
    background_fill_primary=CARD,
    background_fill_secondary=SLATE,
    border_color_primary=CARD_BORDER,
    border_color_accent=GREEN,
    border_color_accent_subdued=GREEN_DEEP,
    color_accent=GREEN,
    color_accent_soft=GREEN_DEEP,
    link_text_color=GREEN,
    link_text_color_hover=GREEN_HOVER,
    link_text_color_active=GREEN,
    link_text_color_visited=GREEN,
    code_background_fill=INPUT,
    block_background_fill="transparent",
    block_border_color=CARD_BORDER,
    block_label_background_fill="transparent",
    block_label_border_color="transparent",
    block_label_text_color=TEXT_SOFT,
    block_title_background_fill="transparent",
    block_title_border_color="transparent",
    block_title_text_color=TEXT_SOFT,
    block_info_text_color=TEXT_MUTED,
    panel_background_fill=CARD,
    panel_border_color=CARD_BORDER,
    input_background_fill=INPUT,
    input_background_fill_focus=INPUT,
    input_background_fill_hover=INPUT,
    input_border_color=INPUT_BORDER,
    input_border_color_focus=GREEN,
    input_border_color_hover="#5C6C75",
    input_placeholder_color="#5C6C75",
    button_primary_background_fill=GREEN,
    button_primary_background_fill_hover=GREEN_HOVER,
    button_primary_border_color=GREEN,
    button_primary_border_color_hover=GREEN_HOVER,
    button_primary_text_color=SLATE,
    button_primary_text_color_hover=SLATE,
    button_secondary_background_fill="transparent",
    button_secondary_background_fill_hover=INPUT,
    button_secondary_border_color=INPUT_BORDER,
    button_secondary_border_color_hover="#5C6C75",
    button_secondary_text_color="#FFFFFF",
    button_secondary_text_color_hover="#FFFFFF",
    checkbox_background_color=INPUT,
    checkbox_background_color_focus=INPUT,
    checkbox_background_color_hover=INPUT,
    checkbox_background_color_selected=GREEN,
    checkbox_border_color="#5C6C75",
    checkbox_border_color_focus=GREEN,
    checkbox_border_color_hover=GREEN,
    checkbox_border_color_selected=GREEN,
    checkbox_label_background_fill="transparent",
    checkbox_label_background_fill_hover="transparent",
    checkbox_label_background_fill_selected="transparent",
    checkbox_label_border_color="transparent",
    checkbox_label_border_color_hover="transparent",
    checkbox_label_border_color_selected="transparent",
    checkbox_label_text_color=TEXT,
    checkbox_label_text_color_selected=TEXT,
    table_text_color=TEXT,
    table_border_color=CARD_BORDER,
    table_even_background_fill="#0A2632",
    table_odd_background_fill="#06212D",
    table_row_focus=GREEN_DEEP,
    loader_color=GREEN,
    slider_color=GREEN,
    stat_background_fill=GREEN_DEEP,
    error_background_fill="#2B0B0E",
    error_border_color="#DB3030",
    error_text_color="#FFCDC7",
    error_icon_color="#FF6960",
    accordion_text_color=TEXT,
)

SHAPES = dict(
    block_radius="8px",
    container_radius="12px",
    input_radius="6px",
    input_border_width="1px",
    block_border_width="0px",
    block_label_border_width="0px",
    block_title_border_width="0px",
    block_label_text_weight="600",
    block_title_text_weight="600",
    block_label_text_size="14px",
    block_title_text_size="14px",
    block_shadow="none",
    shadow_drop="none",
    shadow_drop_lg="none",
    input_shadow="none",
    input_shadow_focus="0 0 0 3px rgba(0, 237, 100, 0.22)",
    button_primary_shadow="none",
    button_primary_shadow_hover="none",
    button_secondary_shadow="none",
    button_large_radius="4px",
    button_medium_radius="4px",
    button_small_radius="4px",
    button_large_text_weight="600",
    button_medium_text_weight="600",
    button_large_text_size="16px",
)


def _theme() -> gr.themes.Base:
    theme = gr.themes.Base(
        primary_hue=GREENS,
        secondary_hue=GREENS,
        neutral_hue=SLATES,
        font=[gr.themes.Font("Segoe UI"), gr.themes.Font("system-ui"), "sans-serif"],
        font_mono=[gr.themes.Font("Cascadia Mono"), gr.themes.Font("Consolas"), "monospace"],
    )
    accepted = inspect.signature(theme.set).parameters
    both = {}
    for key, value in COLORS.items():
        both[key] = value
        if f"{key}_dark" in accepted:  # not every variable has a dark-mode twin
            both[f"{key}_dark"] = value
    return theme.set(**both, **SHAPES)


THEME = _theme()

# Chromium honours font-stretch / the "Condensed" family for Bahnschrift, but not font-variation-settings.
DISPLAY_FONT = '"Bahnschrift Condensed", "Bahnschrift", Impact, "Arial Narrow", sans-serif'
MONO_FONT = '"Cascadia Mono", Consolas, "Courier New", monospace'

CSS = f"""
.gradio-container {{ max-width: 1240px !important; margin: 0 auto !important; }}
footer {{ opacity: 0.55; }}

/* top bar */
.ef-nav {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
          padding: 6px 2px 18px; border-bottom: 1px solid {CARD_BORDER}; }}
.ef-brand {{ display: flex; align-items: center; gap: 10px; color: #FFFFFF;
            font-family: Georgia, "Times New Roman", serif; font-size: 26px; letter-spacing: -0.01em; }}
.ef-brand svg {{ width: 22px; height: 26px; }}
.ef-nav-meta {{ display: flex; align-items: center; gap: 18px; color: {TEXT}; font-size: 15px; flex-wrap: wrap; }}
.ef-pill {{ border: 1px solid {INPUT_BORDER}; border-radius: 999px; padding: 6px 14px;
           font-family: {MONO_FONT}; font-size: 12px; letter-spacing: 0.08em; color: #FFFFFF; }}

/* hero */
.ef-hero {{ text-align: center; padding: 44px 8px 30px; }}
.ef-hero h1 {{ font-family: {DISPLAY_FONT}; font-stretch: 75%; font-weight: 700; text-transform: uppercase;
              font-size: clamp(40px, 7vw, 92px); line-height: 0.92; letter-spacing: -0.005em;
              color: #F9F7EF; margin: 18px 0 18px; }}
.ef-hero p {{ max-width: 760px; margin: 0 auto; color: {TEXT_SOFT}; font-size: 18px; line-height: 1.55; }}
.ef-hero .ef-eyebrow {{ justify-content: center; }}

/* mono eyebrow labels with a dot, as in "● AVAILABLE NOW" */
.ef-eyebrow {{ display: flex; align-items: center; gap: 10px; font-family: {MONO_FONT}; font-weight: 700;
              font-size: 13px; letter-spacing: 0.14em; text-transform: uppercase; color: #FFFFFF; }}
.ef-dot {{ width: 8px; height: 8px; border-radius: 50%; background: {GREEN}; display: inline-block; }}
.ef-dot.purple {{ background: #7B61FF; }}
.ef-dot.blue {{ background: #0498EC; }}

/* cards */
.ef-card {{ background: {CARD} !important; border: 1px solid {CARD_BORDER} !important;
           border-radius: 14px !important; padding: 26px !important; gap: 14px !important; }}
.ef-step h2 {{ font-family: {DISPLAY_FONT}; font-stretch: 75%; font-weight: 700; text-transform: uppercase; font-size: 40px; line-height: 0.95;
              color: #FFFFFF; margin: 12px 0 6px; }}
.ef-step p {{ color: {TEXT_SOFT}; margin: 0; font-size: 15px; }}

/* Gradio paints form groups with the border colour to draw dividers; keep fields flat on the card */
.ef-card .form {{ background: transparent !important; border: none !important; gap: 14px !important; }}
.ef-card .block.padded {{ padding: 0 !important; }}

/* "Load a sample event ›" as a text link */
.ef-link {{ background: transparent !important; border: none !important; color: #FFFFFF !important;
           font-weight: 700 !important; justify-content: flex-start !important; padding-left: 0 !important;
           width: fit-content !important; min-width: 0 !important; }}
.ef-link:hover {{ color: {GREEN} !important; }}

/* upload areas */
.ef-upload {{ border: 1px dashed {INPUT_BORDER} !important; border-radius: 10px !important;
             background: #0A2632 !important; }}

/* evidence check */
.ef-evidence h3 {{ font-family: {MONO_FONT}; font-size: 13px !important; font-weight: 700;
                  letter-spacing: 0.14em; text-transform: uppercase; color: #FFFFFF; margin: 0 0 10px; }}
.ef-evidence ul {{ padding: 0; margin: 0; }}
.ef-evidence li {{ list-style: none; border-left: 3px solid #FFC010; background: rgba(255, 192, 16, 0.07);
                  padding: 9px 12px; margin: 6px 0; border-radius: 4px; color: {TEXT}; }}
.ef-evidence p {{ border-left: 3px solid {GREEN}; background: rgba(0, 237, 100, 0.07);
                 padding: 9px 12px; border-radius: 4px; margin: 6px 0; color: {TEXT}; }}

.ef-banner {{ border: 1px solid #FFC010; border-radius: 10px; padding: 12px 16px; color: {TEXT};
             background: rgba(255, 192, 16, 0.08); }}
.ef-timing {{ font-family: {MONO_FONT}; font-size: 12px; color: {TEXT_MUTED}; }}
"""
