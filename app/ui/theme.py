"""统一设计令牌 — 全局颜色、尺寸、间距、阴影、版本常量。"""

__version__ = "2.3.0"

# ── 颜色 ──

ACCENT = "#1A73E8"
ACCENT_HOVER = "#1557B0"
ACCENT_LIGHT = "#4A9CF5"
ACCENT_BG = "#E8F0FE"

TEXT_PRIMARY = "#1D1D1F"
TEXT_SECONDARY = "#6E6E73"
TEXT_TERTIARY = "#AEAEB2"
TEXT_ON_DARK = "#FFFFFF"

BG_PRIMARY = "#FFFFFF"
BG_SECONDARY = "#F5F5F7"
BG_ELEVATED = "#FFFFFF"
BG_SUNKEN = "#EDEDF0"

BORDER = "#E5E5EA"
BORDER_LIGHT = "#C7C7CC"
BORDER_SUBTLE = "#F0F0F2"

SUCCESS = "#34C759"
SUCCESS_BG = "#F0FFF4"
WARNING = "#E67E22"
DANGER = "#D32F2F"

# ── 尺寸 ──

RADIUS = "10px"
RADIUS_LG = "12px"
RADIUS_SM = "6px"
RADIUS_XS = "4px"

# ── 间距 ──

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 20
SPACE_2XL = 24
SPACE_3XL = 32

# ── 字体 ──

FONT_FAMILY = "PingFang SC, SF Pro Text, Helvetica Neue, sans-serif"
FONT_SIZE_XS = 10
FONT_SIZE_SM = 11
FONT_SIZE_MD = 13
FONT_SIZE_LG = 14
FONT_SIZE_XL = 16
FONT_SIZE_2XL = 20
FONT_SIZE_TITLE = 22

# ── 动画 ──

ANIM_FAST = 150
ANIM_NORMAL = 250
ANIM_SLOW = 400

# ── 状态色补充 ──

INFO = "#007AFF"
INFO_BG = "#EBF5FF"

# ── 覆盖层 ──

OVERLAY_DIM = "rgba(0, 0, 0, 0.3)"

# ── 阴影（用于 QGraphicsDropShadowEffect 参数） ──
# 格式: (blur_radius, x_offset, y_offset, opacity)

SHADOW_SUBTLE = (8, 0, 1, 0.06)
SHADOW_MEDIUM = (16, 0, 4, 0.10)
SHADOW_PROMINENT = (24, 0, 8, 0.14)

# ── 导航图标 ──

NAV_ICONS = {
    "nav_convert": "\u21C4",   # ⇄
    "nav_preview": "\u25A3",   # ▣
    "nav_settings": "\u2699",  # ⚙
}

# ── 格式图标 ──

FORMAT_ICONS = {
    "TXT": "\u2263",    # ≣
    "PDF": "\u25A4",    # ▤
    "Word": "W",
    "HTML": "</>",
    "Excel": "\u2637",  # ☷
    "RTF": "\u00B6",    # ¶
}
