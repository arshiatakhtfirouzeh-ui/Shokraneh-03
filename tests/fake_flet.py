"""A strict stand-in for the part of Flet 1.x that the UI uses (tests only).

* Unknown keyword arguments raise TypeError exactly like the real controls and are recorded in DROPPED, so a typo in
  a keyword is caught even though ui.compat.mk() would silently drop it.
* Icons / enums that do not exist raise AttributeError (the UI must only use real Material icon names).
* This checks the app's own logic and its consistency with the Flet API *as remembered*; it is not a substitute for
  running the real thing.
"""
import enum
import sys
import types

DROPPED: list[tuple[str, str]] = []

COMMON = {"expand", "width", "height", "visible", "opacity", "tooltip", "key", "data", "left", "top", "right", "bottom", "disabled"}

SPEC = {
    "Container": {"content", "padding", "margin", "alignment", "bgcolor", "gradient", "border", "border_radius", "shadow", "on_click",
                  "ink", "clip_behavior", "animate", "animate_opacity", "blur"},
    "Row": {"controls", "spacing", "alignment", "vertical_alignment", "wrap", "run_spacing", "scroll", "tight"},
    "Column": {"controls", "spacing", "alignment", "horizontal_alignment", "scroll", "tight"},
    "Stack": {"controls", "clip_behavior"},
    "ProgressRing": {"value", "stroke_width", "color", "bgcolor"},
    "Text": {"value", "size", "color", "font_family", "weight", "text_align", "max_lines", "overflow", "selectable", "italic", "no_wrap"},
    "Icon": {"icon", "size", "color"},
    "IconButton": {"icon", "icon_color", "icon_size", "on_click", "style"},
    "TextField": {"value", "label", "hint_text", "multiline", "min_lines", "max_lines", "on_change", "on_blur", "on_submit",
                  "border_radius", "filled", "fill_color", "border_color", "focused_border_color", "border_width", "content_padding",
                  "text_size", "text_align", "keyboard_type", "password", "autofocus", "max_length", "cursor_color", "text_style",
                  "can_reveal_password", "read_only"},
    "Switch": {"value", "on_change", "active_color"},
    "SafeArea": {"content"},
    "View": {"route", "controls", "padding", "spacing", "bgcolor", "scroll", "horizontal_alignment", "vertical_alignment"},
    "AlertDialog": {"modal", "title", "content", "actions", "actions_alignment", "bgcolor", "scrollable", "on_dismiss", "content_padding",
                    "inset_padding", "elevation", "shadow_color", "surface_tint_color"},
    "SnackBar": {"content", "bgcolor", "duration", "behavior"},
    "Theme": {"font_family", "color_scheme_seed", "use_material3"},
    "TextStyle": {"font_family", "color", "size", "weight"},
    "BoxShadow": {"spread_radius", "blur_radius", "color", "offset"},
    "LinearGradient": {"begin", "end", "colors"},
    "RadialGradient": {"center", "radius", "colors", "stops"},
    "FilePicker": {"on_result"},
    "Clipboard": set(),
}


class Control:
    _name = "Control"

    def __init__(self, *args, **kw):
        allowed = SPEC[self._name] | COMMON
        for k in kw:
            if k not in allowed:
                DROPPED.append((self._name, k))
                raise TypeError(f"{self._name}.__init__() got an unexpected keyword argument '{k}'")
        self.args = args
        self.__dict__.update(kw)
        if self._name == "Icon" and args:
            self.icon = args[0]
        if self._name == "Text" and args:
            self.value = args[0]

    def update(self):
        pass

    def kids(self):
        out = []
        for attr in ("content", "controls", "actions", "title"):
            v = getattr(self, attr, None)
            if isinstance(v, Control):
                out.append(v)
            elif isinstance(v, (list, tuple)):
                out += [x for x in v if isinstance(x, Control)]
        return out


def _make(name):
    return type(name, (Control,), {"_name": name})


for _n in SPEC:
    globals()[_n] = _make(_n)


def _enum(name, members):
    return enum.Enum(name, {m: m for m in members})


MainAxisAlignment = _enum("MainAxisAlignment", ["START", "END", "CENTER", "SPACE_BETWEEN", "SPACE_AROUND", "SPACE_EVENLY"])
CrossAxisAlignment = _enum("CrossAxisAlignment", ["START", "END", "CENTER", "STRETCH", "BASELINE"])
ScrollMode = _enum("ScrollMode", ["AUTO", "ALWAYS", "HIDDEN", "ADAPTIVE"])
TextAlign = _enum("TextAlign", ["LEFT", "RIGHT", "CENTER", "JUSTIFY", "START", "END"])
TextOverflow = _enum("TextOverflow", ["ELLIPSIS", "CLIP", "FADE", "VISIBLE"])
FontWeight = _enum("FontWeight", ["W_400", "W_500", "W_600", "W_700", "BOLD", "NORMAL"])
ThemeMode = _enum("ThemeMode", ["LIGHT", "DARK", "SYSTEM"])
KeyboardType = _enum("KeyboardType", ["TEXT", "NUMBER", "MULTILINE", "PHONE"])
ClipBehavior = _enum("ClipBehavior", ["NONE", "HARD_EDGE", "ANTI_ALIAS"])
SnackBarBehavior = _enum("SnackBarBehavior", ["FIXED", "FLOATING"])
Brightness = _enum("Brightness", ["LIGHT", "DARK"])
AnimationCurve = _enum("AnimationCurve", ["LINEAR", "EASE_OUT", "EASE_IN_OUT", "EASE_OUT_CUBIC"])


class Animation:
    def __init__(self, duration=300, curve=None):
        self.duration, self.curve = duration, curve

KNOWN_ICONS = set("""
ADD ARROW_BACK ARROW_FORWARD AUTO_AWESOME BACKUP BEDTIME CALENDAR_MONTH CALENDAR_VIEW_WEEK CARD_GIFTCARD CELEBRATION CHAT_BUBBLE_OUTLINE
CHECK CHECK_CIRCLE CHECK_CIRCLE_OUTLINE CHEVRON_LEFT CHEVRON_RIGHT CIRCLE CLOSE CLOUD DELETE_OUTLINE EDIT EMOJI_EVENTS FAVORITE
FAVORITE_BORDER FILE_DOWNLOAD FILE_UPLOAD FLAG FORMAT_QUOTE GRID_VIEW HISTORY HOME_OUTLINED INFO_OUTLINE INSIGHTS KEYBOARD_ARROW_DOWN
KEYBOARD_ARROW_UP GAVEL COPYRIGHT ERROR_OUTLINE LANGUAGE LIGHTBULB LOCK LOCK_OPEN LOCAL_FIRE_DEPARTMENT MAIL MAIL_OUTLINE MARK_EMAIL_UNREAD NIGHTLIGHT_ROUND
NOTIFICATIONS_NONE NOTIFICATIONS_ACTIVE PALETTE PERSON PERSON_ADD PSYCHOLOGY SELF_IMPROVEMENT SENTIMENT_SATISFIED_ALT SETTINGS_OUTLINED
SHIELD_OUTLINED STAR STAR_BORDER TRENDING_UP VOLUNTEER_ACTIVISM WB_SUNNY WB_TWILIGHT BACKSPACE REFRESH LOGOUT SWAP_HORIZ SCHEDULE
EVENT TODAY AUTO_STORIES FORUM SPA TUNE KEY VISIBILITY VISIBILITY_OFF CONTENT_COPY SEND DONE_ALL TIMELINE DATE_RANGE EDIT_NOTE
""".split())


MISSING_ICONS: set[str] = set()


class _Icons:
    def __getattr__(self, name):
        if name in KNOWN_ICONS:
            return name
        if name.isupper():  # compat.ic() retries with the lower-case name; only the real request counts
            MISSING_ICONS.add(name)
        raise AttributeError(name)


Icons = _Icons()


class Alignment:
    def __init__(self, x=0, y=0):
        self.x, self.y = x, y


class Padding:
    def __init__(self, left=0, top=0, right=0, bottom=0):
        self.left, self.top, self.right, self.bottom = left, top, right, bottom


class BorderSide:
    def __init__(self, width=1, color=None):
        self.width, self.color = width, color


class Border:
    def __init__(self, top=None, right=None, bottom=None, left=None):
        self.top, self.right, self.bottom, self.left = top, right, bottom, left

    @classmethod
    def all(cls, width=1, color=None):
        s = BorderSide(width, color)
        return cls(s, s, s, s)


class Offset:
    def __init__(self, x=0, y=0):
        self.x, self.y = x, y


class Locale:
    def __init__(self, language_code="en", country_code=None):
        self.language_code, self.country_code = language_code, country_code


class LocaleConfiguration:
    def __init__(self, supported_locales=None, current_locale=None):
        self.supported_locales, self.current_locale = supported_locales, current_locale


class Page:
    def __init__(self):
        self.views = [View(route="/")]
        self.dialogs = []
        self.services = []
        self.width, self.height = 420, 860
        self.platform_brightness = Brightness.LIGHT
        self.updates = 0
        self.title = self.bgcolor = self.theme = self.dark_theme = self.theme_mode = None
        self.padding = self.spacing = 0
        self.fonts = {}

    def update(self, *a):
        self.updates += 1

    def show_dialog(self, d):
        self.dialogs.append(d)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None

    def run_task(self, fn, *a, **k):
        import asyncio

        return asyncio.run(fn(*a, **k))


class Event:
    def __init__(self, control=None, data=""):
        self.control, self.data = control, data


def run(*a, **k):  # pragma: no cover
    raise RuntimeError("fake flet cannot run an app")


def install():
    mod = types.ModuleType("flet")
    mod.__dict__.update({k: v for k, v in globals().items() if not k.startswith("_")})
    sys.modules["flet"] = mod
    return mod
