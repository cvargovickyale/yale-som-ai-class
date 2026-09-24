"""Pydantic/PydanticAI structured types shared across the HW3 agent and scripts.

A "Pydantic/PydanticAI structured type" here means: a `pydantic.BaseModel`
subclass that declares exact field names, types, and allowed values (an
`Enum` for a closed set like `MerchType`, a `Literal` for a fixed set of
strings like a confidence level) so invalid data is rejected rather than
silently accepted. PydanticAI then uses the same class as an `Agent`'s
`output_type=`, which turns the schema into a tool call the model is
constrained to use -- calling code gets back a real Python object
(`result.match.filename` as an actual string, `result.match.confidence` as
one of exactly "high"/"medium"/"low"), never raw text it has to hope parses
into the right shape.

Every structured type used anywhere in this homework (catalogue entries, the
identify/ad-effectiveness/profile/audit types) lives here rather than being
scattered across the individual scripts, so there is exactly one definition
of what each piece of data is allowed to look like.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class MerchType(str, Enum):
    """Garment categories observed in the Campus Customs product catalogue."""

    T_SHIRT = "t_shirt"
    CREWNECK = "crewneck"
    HOODIE = "hoodie"
    QUARTER_ZIP = "quarter_zip"
    FLEECE_JACKET = "fleece_jacket"
    BOMBER_JACKET = "bomber_jacket"
    LONG_SLEEVE = "long_sleeve"
    MOCKNECK = "mockneck"
    OTHER = "other"


class BrandingStyle(str, Enum):
    """How the school/program identity is rendered on the garment.

    Distinguishing wordmark vs. logo vs. crest (and combinations) is the
    detail that most helps later matching against a photo, since a real photo
    often shows only one of these clearly.
    """

    WORDMARK_ONLY = "wordmark_only"
    LOGO_ONLY = "logo_only"
    CREST_ONLY = "crest_only"
    WORDMARK_AND_LOGO = "wordmark_and_logo"
    WORDMARK_AND_CREST = "wordmark_and_crest"
    LOGO_AND_CREST = "logo_and_crest"
    NONE = "none"


class CatalogueEntry(BaseModel):
    """One Campus Customs product, as identified from its catalogue photo."""

    filename: str
    source: str = Field(
        default="vision_model",
        description=(
            "'vision_model' for an automated catalogue call, 'manual' when a "
            "human filled the fields in by hand (e.g. the vision call was "
            "blocked by content-safety filtering on the photo)."
        ),
    )
    merch_type: MerchType
    description: str = Field(
        description=(
            "1-2 sentence visual description: garment color/cut and where the "
            "branding sits on it."
        )
    )
    school_or_program: str = Field(
        description=(
            "The specific Yale entity the branding names, e.g. 'Yale Baseball', "
            "'Benjamin Franklin College', 'Yale School of Music', 'Yale' if only "
            "the university name/bulldog appears generically."
        )
    )
    branding_style: BrandingStyle
    primary_colors: list[str] = Field(
        default_factory=list,
        description="Dominant garment colors, e.g. ['navy'] or ['heather gray'].",
    )


class ProductMatch(BaseModel):
    """The specific catalogue product judged to be shown in a query photo."""

    filename: str = Field(
        description="The matching catalogue entry's filename, e.g. 'baseball-left-chest-crewneck.jpg'."
    )
    school_or_program: str
    merch_type: MerchType
    confidence: Literal["high", "medium", "low"] = Field(
        description=(
            "How sure the agent is this is the specific product, not just that "
            "the general category/school is right."
        )
    )


class IdentifyResult(BaseModel):
    """Structured return type for the product-identify agent.

    Written to output/identify_product.json for a single `--image` run.
    """

    query_image: str = Field(description="Path to the photo that was checked, as passed to --image.")
    product_present: bool = Field(
        description="Whether a Campus Customs product is visible in the photo at all."
    )
    match: ProductMatch | None = Field(
        default=None,
        description=(
            "The specific catalogue product identified, when product_present is "
            "True and the agent could pin it down to one catalogue entry. None if "
            "no product is present, or if a product looks plausible but can't be "
            "confidently matched to a specific catalogue entry."
        ),
    )
    reasoning: str = Field(
        description="Brief, concrete grounds for the decision: what was seen, and why it does or doesn't match."
    )
    candidates_considered: list[str] = Field(
        default_factory=list,
        description=(
            "Catalogue filenames actually compared against the photo (bounded to "
            "10 or fewer). Empty if the photo was ruled out before any candidate "
            "images were loaded."
        ),
    )


class ProductCatalogue(BaseModel):
    """Container written to output/catalogue.json."""

    model: str
    generated_at: str
    entries: list[CatalogueEntry]
    skipped: list[str] = Field(
        default_factory=list,
        description="Product filenames the model call failed on and that never got an entry.",
    )


class AppealCategory(str, Enum):
    """What an ad (or a customer) responds to. The same vocabulary is used on
    both sides -- a customer's `interests` and an ad's derived `ad_themes' --
    because the overlap between the two is literally the matching mechanism
    for judging ad effectiveness, not just a label."""

    SCHOOL_PRIDE = "school_pride"
    HUMOR_COMEDY = "humor_comedy"
    SOCIAL_BELONGING = "social_belonging"
    STYLE_FASHION = "style_fashion"
    CONFIDENCE_SWAGGER = "confidence_swagger"
    ATHLETIC_ENERGY = "athletic_energy"
    TRADITION_HERITAGE = "tradition_heritage"
    # Resonance with a mission-driven, "business for society" framing --
    # social impact, ethical leadership, purpose beyond profit -- rather than
    # generic school spirit. Added for Problem 6's Yale School of Management
    # personas; an ad has to actually show something purpose/impact-oriented
    # to earn this as an ad_theme, the same rule as every other category.
    PURPOSE_IMPACT = "purpose_impact"


class CustomerProfile(BaseModel):
    """One Campus Customs customer persona, used to judge ad fit."""

    name: str
    role: str = Field(
        description="e.g. 'Yale undergraduate', 'parent of a Yale student', 'alum'."
    )
    relationship_to_yale: Literal["student", "parent", "alum", "other"]
    program: str = Field(
        description="e.g. 'Yale School of Management, MBA (Class of 2026)', or "
        "'Parent of a Yale School of Management MBA student'."
    )
    age_range: str
    interests: list[AppealCategory] = Field(
        description="Which appeal categories this customer actually responds to -- "
        "the matching signal against an ad's derived themes."
    )
    wear_occasions: list[str] = Field(
        default_factory=list,
        description=(
            "Where/when this customer would actually wear Campus Customs merch, "
            "e.g. 'networking events', 'casual weekends', 'gifting'. Deliberately "
            "separate from `interests`: what appeals to someone and where they'd "
            "wear it are different questions -- a customer can love an ad's theme "
            "and still have no occasion that calls for the merch it's selling."
        ),
    )
    style_preferences: str = Field(
        description="Free text: e.g. 'casual streetwear, hoodies and graphic tees'."
    )
    budget_sensitivity: Literal["low", "medium", "high"] = Field(
        description="How much price matters to this customer; 'high' = very price-sensitive."
    )
    notes: str = Field(default="", description="Any other context useful for judging ad fit.")


class AdEffectivenessResult(BaseModel):
    """Structured return type for judging one ad video against one customer
    profile. Entries accumulate in output/ad_effectiveness.json the same way
    IdentifyResult entries accumulate in identify_product.json.
    """

    video_path: str = Field(description="Path to the ad video that was watched, as passed to --video.")
    customer_name: str = Field(description="The CustomerProfile.name this run was judged against.")
    ad_themes: list[AppealCategory] = Field(
        description="Appeal categories the agent judged the ad actually emphasizes, "
        "derived from watching sampled frames -- not copied from the customer profile."
    )
    matched_categories: list[AppealCategory] = Field(
        default_factory=list,
        description="Overlap between ad_themes and this customer's own interests -- "
        "the core signal behind the effectiveness rating.",
    )
    effectiveness: Literal["high", "medium", "low"] = Field(
        description="How likely this ad is to persuade this specific customer to shop with Campus Customs."
    )
    reasoning: str = Field(
        description="Grounded account of what the ad shows, what the customer cares "
        "about, and why they do or don't line up."
    )


class AuditStep(BaseModel):
    """One turn of the agent's reasoning loop during a single run.

    `thought` only ever holds text the model actually produced visibly in
    that turn -- never a reconstruction of hidden chain-of-thought. Most
    tool-calling turns have no separate visible text at all, in which case
    this is empty; that is logged honestly rather than backfilled with a
    guess at what the model "must have been thinking."
    """

    timestamp: str
    thought: str = Field(default="", description="Visible text the model produced in this turn, if any.")
    tool_name: str | None = Field(
        default=None, description="None for a turn that produced no tool call."
    )
    tool_args: dict = Field(default_factory=dict)
    result_summary: str = Field(
        default="", description="Short, truncated summary of the tool's return value."
    )


class AuditEntry(BaseModel):
    """One full agent invocation (one --image or one --video/--profile run).
    Appended to output/audit_trail.json every run -- entries are never
    overwritten or dropped, including on a failed/aborted run.
    """

    timestamp: str
    mode: Literal["identify", "ad_effectiveness"]
    inputs: dict[str, str] = Field(
        description="e.g. {'image': '...'} or {'video': '...', 'profile': '...'}."
    )
    steps: list[AuditStep]
    stop_reason: str = Field(
        description="Why the run ended: produced a final result, aborted on a "
        "content-safety rejection, or an unhandled error."
    )
    outcome_summary: str = Field(
        default="", description="One-line summary of the final structured result, if any."
    )
