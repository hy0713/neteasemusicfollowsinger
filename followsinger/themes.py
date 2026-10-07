"""Five complete desktop palettes, including readable dark controls."""

THEMES = {
    "时尚绿": ("#fbfbf8", "#f0f1e9", "#35433e", "#456c5d", "#e6eddf", "#78877c", "#dce2d7"),
    "护眼黄": ("#faf3df", "#eee3c7", "#514735", "#92713d", "#eee0b9", "#84745b", "#d9cbae"),
    "海浪蓝": ("#f3f8fc", "#e4eef7", "#28445b", "#337ba8", "#dcecf8", "#64839c", "#c8d9e7"),
    "经典白": ("#ffffff", "#f2f3f5", "#30343b", "#56647a", "#e9edf3", "#727985", "#dce0e6"),
    "夜间黑": ("#191c22", "#22262e", "#e2e6ed", "#647fac", "#2d3c52", "#a0aaba", "#39414e"),
}


def recolor(css, name):
    background, rail, text, accent, selected, muted, border = THEMES[name]
    groups = {
        background: ("#fbfbf8", "#f9faf6"),
        rail: ("#f0f1e9", "#f3f5ee", "#e6e9df"),
        text: ("#35433e", "#455348", "#556b5c", "#365e52"),
        accent: ("#456c5d", "#36584d", "#6a8d75", "#6c8b6a", "#789673", "#6b8868"),
        selected: ("#dce7dc", "#e6eddf", "#e9eee5", "#bcd3bf"),
        muted: ("#8b958e", "#6e8c7b", "#78877c", "#789078", "#99a095", "#939c90", "#8d998c", "#b1b8b0"),
        border: ("#e3e6dc", "#edf0e8", "#dce2d7", "#c9d5c5", "#e0e5db", "#b9c8b9", "#e2e7dc", "#dce5d6", "#dce3d6"),
    }
    import re
    colors = {old: new for new, originals in groups.items() for old in originals}
    return re.sub(r"#[0-9a-fA-F]{6}", lambda match: colors.get(match[0], match[0]), css)
