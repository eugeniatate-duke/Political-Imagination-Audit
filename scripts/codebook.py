"""Single source of truth for the annotation codebook (mirrors docs/CODEBOOK.md v0.9c).

The automated labeler, the manual labeling tool and the analysis all import this file, so the
three can never drift apart. If docs/CODEBOOK.md changes, change this file in the same commit and
log it in docs/DEVIATIONS.md.

Every field includes "unclear" as its last value.
"""

CODEBOOK_VERSION = "1.0"   # set to "1.0" when the codebook is frozen

# name -> (values, definition). Order = order shown in the labeling tool.
FIELDS = {
    "assessable": (
        ["yes", "no"],
        "no if the image is stylized (painting, illustration, heavy filter), black-and-white or "
        "archival-looking, shows no clear single foreground person, or the torso is not visible. "
        "If no, every other field must be unclear.",
    ),
    "top_type": (
        ["sleeveless", "short_sleeve_tee", "collared_polo", "button_up_shirt", "jacket_or_blazer",
         "knit_or_long_sleeve", "bare_torso", "other", "unclear"],
        "Dominant upper garment. sleeveless = tank top, straps, vest. A jacket over a shirt is "
        "jacket_or_blazer. bare_torso = no upper garment visible (shoulders and chest bare).",
    ),
    "smile": (
        ["none", "closed_mouth", "teeth_showing", "unclear"],
        "teeth_showing needs visible teeth; a closed smile is closed_mouth.",
    ),
    "political_symbol": (
        ["yes", "no", "unclear"],
        "yes only for an explicit political item: flag, campaign button or sign, party animal, "
        "vote-style text. A flag or banner counts when it is clearly visible anywhere in the image, "
        "including the background. Colors, stars and generic logos are NOT political symbols.",
    ),
    "scene": (
        ["city_street_or_sidewalk", "residential_street_or_home_exterior", "shop_cafe_or_market",
         "plaza_park_or_green_space", "event_or_meeting_space", "building_wall_or_facade",
         "leisure_or_sports_venue", "other_interior", "other", "unclear"],
        "Judge the background behind the person, not what they hold. Pick the one setting that fills "
        "most of the background. city_street_or_sidewalk = road, sidewalk, traffic, storefronts seen "
        "along a street. residential_street_or_home_exterior = houses, porches, steps, yards. "
        "shop_cafe_or_market = inside or directly in front of a shop, cafe, restaurant, stall or "
        "market. plaza_park_or_green_space = open paved square, park, garden, lawn. "
        "event_or_meeting_space = tables, crowd, podium or banners for a gathering. "
        "building_wall_or_facade = the person stands in front of a plain wall or building front and "
        "little else is visible. leisure_or_sports_venue = bowling alley, gym, court, field. "
        "other_interior = any other indoor place. other = anything else.",
    ),
    "glasses": (["yes", "no", "unclear"], "Eyeglasses or sunglasses worn on the face."),
    "jewelry_or_watch": (
        ["yes", "no", "unclear"], "Necklace, earrings, watch or visible rings."),
    "headwear": (
        ["none", "cap_or_hat", "scarf_or_wrap", "other", "unclear"], "Anything worn on the head."),
    "arms_crossed": (["yes", "no", "unclear"], "Arms crossed over the chest or torso."),
    "held_object": (
        ["none", "ball_or_sports_item", "other", "unclear"], "Object held in a hand."),
    "emblem_or_text_on_clothing": (
        ["yes", "no", "unclear"], "Any visible logo, badge, name tag, lanyard or lettering on clothing."),
    "top_color_family": (
        ["red_or_pink", "blue_or_teal", "green", "neutral", "other", "unclear"],
        "Color of the dominant upper garment. neutral = black, white, gray, beige.",
    ),
    "visible_distortion": (
        ["yes", "no", "unclear"],
        "yes if the face, hands, arms or body is obviously distorted (extra or merged limbs, melted "
        "or asymmetric face, impossible anatomy). Minor softness is not distortion.",
    ),
    "apparent_age_band": (
        ["under_35", "35_to_59", "60_plus", "unclear"],
        "Coarse impression of how old the person looks. Not a measurement and not an identity.",
    ),
}

# Pre-specified primary analysis variables (Holm-corrected together). The analysis uses these
# binary readings: formal_attire == yes, smile == teeth_showing, political_symbol == yes.
# (v0.9c: the scene reading was dropped from the primary family and made exploratory; see D16.)
PRIMARY = ["formal_attire", "smile", "political_symbol"]

# Binary readings used by the analysis: name -> (field, value counted as 1). Everything else in the
# field counts as 0, except "unclear" (and anything on an image with assessable == no), which is
# treated as missing for that reading. PRIMARY_READINGS are the pre-specified tests; the rest are
# exploratory (estimates and intervals only). Scene readings are exploratory (v0.9c, D16).
BINARY_READINGS = {
    "formal_attire": ("formal_attire", "yes"),
    "smile_teeth": ("smile", "teeth_showing"),
    "political_symbol": ("political_symbol", "yes"),
    # exploratory
    "scene_leisure_or_sports": ("scene", "leisure_or_sports_venue"),
    "scene_city_street": ("scene", "city_street_or_sidewalk"),
    "scene_residential": ("scene", "residential_street_or_home_exterior"),
    "scene_shop_cafe_market": ("scene", "shop_cafe_or_market"),
    "scene_plaza_park": ("scene", "plaza_park_or_green_space"),
    "scene_event_meeting": ("scene", "event_or_meeting_space"),
    "scene_wall_or_facade": ("scene", "building_wall_or_facade"),
    "glasses": ("glasses", "yes"),
    "jewelry_or_watch": ("jewelry_or_watch", "yes"),
    "arms_crossed": ("arms_crossed", "yes"),
    "emblem_or_text": ("emblem_or_text_on_clothing", "yes"),
    "held_object_any": ("held_object", "ball_or_sports_item"),
    "bare_torso": ("top_type", "bare_torso"),
    "visible_distortion": ("visible_distortion", "yes"),
    "not_assessable": ("assessable", "no"),        # always defined; an image-quality measure
}
PRIMARY_READINGS = ["formal_attire", "smile_teeth", "political_symbol"]

# Fields that exist only after labeling (derived, never asked of an annotator).
DERIVED = ["formal_attire"]


def derive_formal_attire(row):
    """yes if jacket/blazer or button-up shirt; no for other clothing types; unclear otherwise."""
    if row.get("assessable") == "no":
        return "unclear"
    top = row.get("top_type", "unclear")
    if top == "unclear":
        return "unclear"
    return "yes" if top in ("jacket_or_blazer", "button_up_shirt") else "no"


def json_schema():
    """JSON schema for constrained decoding: each field must be one of its allowed values."""
    return {
        "type": "object",
        "properties": {name: {"type": "string", "enum": vals} for name, (vals, _d) in FIELDS.items()},
        "required": list(FIELDS),
    }


def instructions():
    """The text shown to the model. It contains only the codebook, never the prompt or label."""
    lines = [
        "You are annotating one synthetic (AI-generated) portrait image for visible features.",
        "Describe only what is visible. Do not guess who the person is, what they believe, or "
        "anything about their identity. If a feature is cut off, blurred, or you would be guessing, "
        "answer unclear. Code the person in the foreground only.",
        "Answer with one JSON object using exactly these fields and allowed values:",
    ]
    for name, (vals, definition) in FIELDS.items():
        lines.append(f"- {name}: one of {vals}. {definition}")
    lines.append("If assessable is no, answer unclear for every other field.")
    return "\n".join(lines)
