"""Plain-language explanations (Phase 7), English and Hinglish.

Deterministic templates, NOT a generative model: every sentence is written in advance, and the
only text that comes from the document is the key-facts line, which is copied verbatim from the
clause. Nothing can be invented, and `check_grounded` proves it for every report.
"""

from __future__ import annotations

import re

from clauselens.facts import Fact

LANGS = ("en", "hinglish")
RISK_LABEL = {
    "en": {"green": "Looks fine", "amber": "Needs attention", "red": "High risk"},
    "hinglish": {"green": "Theek lag raha hai", "amber": "Dhyan dene wala", "red": "Zyada risky"},
}
ROLE_NAME = {
    "deposit_amount": "Deposit", "monthly_rent": "Monthly rent", "refund_window": "Refund window",
    "lock_in_period": "Lock-in", "exit_penalty": "Exit penalty", "notice_period": "Notice",
    "rent_increase": "Rent increase", "escalation_interval": "Increase every",
    "repair_limit": "Repair limit", "maintenance_charge": "Society charges",
    "entry_notice": "Entry notice", "guest_limit": "Guest limit", "cure_period": "Cure period",
    "default_grace": "Default after", "verification_window": "Verification within",
    "bond_amount": "Bond amount", "bond_period": "Bond period", "training_cost": "Training cost",
    "recovery_period": "Recovery window", "retention_period": "Documents held for",
    "deduction_cap": "Deduction cap", "pay": "Pay", "date": "Date",
    "purchase_price": "Purchase price", "booking_amount": "Booking amount",
    "registration_charge": "Registration charge",
}  # fmt: skip

CLAUSE_INFO: dict[str, tuple[str, str]] = {
    "security_deposit": ("Sets the deposit, what can be deducted and when it comes back.",
                         "Deposit kitna hai, kya kaata ja sakta hai aur wapas kab milega, ye batata hai."),
    "lock_in_period": ("Fixes a minimum stay and what leaving early costs.",
                       "Minimum rehne ka time aur jaldi nikalne ka cost tay karta hai."),
    "rent_escalation": ("Explains how and when the rent goes up.", "Rent kaise aur kab badhega, ye batata hai."),
    "maintenance_repairs": ("Splits repair and maintenance costs between the parties.",
                            "Repair aur maintenance ka kharcha kaun uthayega, ye batata hai."),
    "utilities_and_charges": ("Says who pays electricity, water and society charges.",
                              "Bijli, paani aur society charges kaun dega, ye batata hai."),
    "owner_entry_inspection": ("Controls when the owner may enter the home.",
                               "Owner kab ghar mein aa sakta hai, ye control karta hai."),
    "subletting_guests": ("Limits subletting and guest stays.", "Sublet aur guests ke rukne par limit lagata hai."),
    "eviction_default": ("Describes what happens on non-payment or breach.",
                         "Rent na dene ya breach par kya hoga, ye batata hai."),
    "tenant_verification": ("Covers police and document verification.",
                            "Police aur document verification ke baare mein hai."),
    "handover_inventory": ("Records the condition and inventory at handover.",
                           "Handover par ghar ki condition aur inventory record karta hai."),
    "service_bond": ("Sets a minimum service period and what you owe if you leave early.",
                     "Minimum service period aur jaldi chhodne par kitna dena hoga, ye tay karta hai."),
    "training_cost_recovery": ("Lets the employer recover training costs.",
                               "Employer ko training ka kharcha wapas lene deta hai."),
    "notice_period": ("Sets the notice needed to resign or be terminated.",
                      "Resign karne ya nikale jaane ke liye kitna notice chahiye, ye batata hai."),
    "document_retention": ("Says whether the employer holds your original documents.",
                           "Batata hai ki employer tere original documents rakhega ya nahi."),
    "salary_deductions": ("Lists what can be deducted from salary or stipend.",
                          "Salary ya stipend se kya kaata ja sakta hai, ye batata hai."),
    "property_specifications": ("Covers the stated property area, layout, fixtures, amenities and changes the seller or builder may make.",
                                "Property ka area, layout, fixtures, amenities aur seller/builder ke changes ke baare mein hai."),
    "title_and_encumbrances": ("Covers title, ownership and disclosed liens or encumbrances. Verify title documents independently.",
                               "Title, ownership aur liens/encumbrances ke baare mein hai. Title documents independently verify karo."),
    "possession_handover": ("Covers possession timing, handover conditions and possible delay consequences.",
                            "Possession ki timing, handover conditions aur delay ke consequences ke baare mein hai."),
    "booking_payment": ("Covers booking money, purchase consideration and payment milestones.",
                       "Booking amount, purchase price aur payment milestones ke baare mein hai."),
    "cancellation_refund": ("Covers cancellation rights, refund conditions and possible forfeiture of paid amounts.",
                            "Cancellation, refund conditions aur paid amount forfeit hone ke baare mein hai."),
    "registration_charges": ("Covers stamp duty, registration fees and transaction charges.",
                             "Stamp duty, registration fees aur transaction charges ke baare mein hai."),
}  # fmt: skip

# flag -> (reason en, tip en, reason hinglish, tip hinglish)
FLAG_TEXT: dict[str, tuple[str, str, str, str]] = {
    "discretionary_deductions": (
        "Deductions are left to one side's discretion.", "Ask for a closed list of allowed deductions.",
        "Deductions ek hi side ki marzi par chhodi gayi hain.", "Allowed deductions ki fixed list maango."),
    "no_limit": (
        "There is no upper limit on the amount or time.", "Ask for a clear cap and a time limit.",
        "Amount ya time par koi upper limit nahi hai.", "Clear cap aur time limit likhwao."),
    "no_notice": (
        "One side can act without any notice.", "Ask for a written notice and a cure period.",
        "Ek side bina notice ke action le sakti hai.", "Written notice aur cure period maango."),
    "forfeiture": (
        "The deposit or money can be forfeited.", "Limit forfeiture to proven loss, with a notice first.",
        "Deposit ya paisa zabt (forfeit) ho sakta hai.", "Forfeiture sirf proven loss tak rakho, notice ke baad."),
    "originals_withheld": (
        "Original documents are held back.", "Offer photocopies instead and ask for originals to be returned.",
        "Original documents rok ke rakhe jayenge.", "Photocopy do aur originals wapas maango."),
    "one_sided_exit": (
        "Only one side is bound or can exit freely.", "Ask for the same rights and duties for both sides.",
        "Sirf ek side bound hai ya free exit kar sakti hai.", "Dono side ke liye same rights aur duties maango."),
    "full_amount_regardless": (
        "The full amount is payable however much service you completed.",
        "Ask for a pro-rata amount based on the period not served.",
        "Kitni bhi service karo, poori amount deni padegi.", "Bacha hua period ke hisaab se pro-rata amount maango."),
    "seller_specification_change": (
        "The seller or builder may change important property specifications without prior written consent.",
        "Ask for written buyer consent for material changes and a clear remedy if area or facilities are reduced.",
        "Seller ya builder important property specifications bina written consent badal sakta hai.",
        "Material changes ke liye buyer ki written consent aur area/facilities kam hone par remedy likhwao."),
    "unclear_title": (
        "The agreement does not clearly protect the buyer against title defects or undisclosed claims.",
        "Have a property advocate independently verify title records and encumbrances before signing or paying.",
        "Agreement title defects ya undisclosed claims se buyer ko clearly protect nahi karta.",
        "Sign/payment se pehle property advocate se title records aur encumbrances verify karao."),
    "possession_delay": (
        "The wording may allow possession delays without a clear date or effective remedy.",
        "Ask for a fixed possession date, defined extension reasons and written delay remedies.",
        "Wording possession delay ko allow kar sakti hai bina clear date ya remedy ke.",
        "Fixed possession date, extension ke reasons aur delay remedies likhwao."),
    "booking_forfeiture": (
        "The wording may allow booking money or payments to be forfeited broadly.",
        "Clarify cancellation rights, permitted deductions, seller breach scenarios and refund deadlines.",
        "Booking amount ya payments broadly forfeit ho sakte hain.",
        "Cancellation rights, allowed deductions, seller breach aur refund deadline clear karao."),
    "unilateral_change": (
        "One side can change the terms or amount alone.", "Ask that changes need written consent of both sides.",
        "Ek side akele terms ya amount badal sakti hai.", "Changes ke liye dono ki written consent maango."),
    "entry_without_notice": (
        "Entry is allowed without prior notice.", "Agree on at least 24 hours' notice and fixed hours.",
        "Bina notice ke entry allowed hai.", "Kam se kam 24 ghante ka notice aur fixed timing tay karo."),
    "no_inventory": (
        "No inventory is recorded and one side decides about damage.",
        "Get a signed inventory with photos at handover.",
        "Inventory record nahi hai aur damage ka faisla ek hi side karti hai.",
        "Handover par photos ke saath signed inventory banwao."),
    "self_help_eviction": (
        "Possession can be taken back without a process.", "Ask for notice and a proper process before eviction.",
        "Bina process ke possession wapas liya ja sakta hai.", "Eviction se pehle notice aur proper process maango."),
    "tenant_bears_structural": (
        "You would pay even for structural repairs.", "Structural repairs normally stay with the owner; ask to change this.",
        "Structural repairs ka kharcha bhi tujhe dena hoga.", "Structural repairs owner ke paas rehne chahiye; ye badalwao."),
    "unitemised_charges": (
        "Charges are not itemised and the demand is final.", "Ask to see bills and pay actuals only.",
        "Charges itemised nahi hain aur demand final hai.", "Bills dekhne ka haq maango aur actual hi do."),
    "withholding_final_dues": (
        "Final dues can be withheld until recoveries are made.", "Ask that final dues are paid within a fixed time.",
        "Final dues recovery tak rok liye ja sakte hain.", "Final dues ek fixed time mein dene ko kaho."),
    "undefined_amount": (
        "The amount is left for one side to determine.", "Ask for a fixed, written formula or amount.",
        "Amount ek side ke calculate karne par chhodi gayi hai.", "Fixed, written formula ya amount maango."),
    "exit_penalty": (
        "Leaving early carries a payment.", "Check the amount and try to reduce or cap it.",
        "Jaldi nikalne par payment lagti hai.", "Amount check karo aur cap ya kam karwane ki koshish karo."),
    "informal_notice": (
        "Notice can be informal (oral or message).", "Ask for written notice with a minimum period.",
        "Notice informal (oral ya message) ho sakta hai.", "Minimum period ke saath written notice maango."),
    "market_rate_reset": (
        "Rent can reset to the market rate on renewal.", "Ask for a fixed percentage increase on renewal.",
        "Renewal par rent market rate pe reset ho sakta hai.", "Renewal par fixed percentage increase maango."),
    "future_increases_on_tenant": (
        "Future increases in charges fall on you.", "Ask for a cap on future increases.",
        "Charges ke future increases tujh par aayenge.", "Future increases par cap maango."),
    "tenant_bears_fittings": (
        "You bear all repairs of fittings and wear and tear.", "Ask to split cost for normal wear and tear.",
        "Fittings ke saare repairs aur wear and tear tujhe uthane honge.", "Normal wear and tear ka kharcha baantne ko kaho."),
    "strict_guest_limit": (
        "Guests need the owner's approval beyond a short stay.", "Ask for a reasonable guest allowance.",
        "Thode din se zyada guests ke liye owner ki approval chahiye.", "Guests ke liye reasonable allowance maango."),
    "short_default_window": (
        "Short grace period before default action.", "Ask for a longer grace period and a written notice.",
        "Default action se pehle grace period chhota hai.", "Lamba grace period aur written notice maango."),
    "costs_on_tenant": (
        "The cost falls on you.", "Ask to share the cost.", "Kharcha tujh par hai.", "Kharcha share karne ko kaho."),
    "mandatory_repainting": (
        "Repainting at exit is your cost.", "Ask to limit this to damage beyond normal wear.",
        "Nikalte waqt repainting ka kharcha tera hai.", "Ise normal wear se zyada damage tak seemit karwao."),
    "loss_recovery": (
        "Losses or dues can be recovered from pay.", "Ask for itemised, proven recoveries only.",
        "Losses ya dues pay se recover ho sakte hain.", "Sirf itemised aur proven recovery maango."),
    "temporary_retention": (
        "Original documents are held for some time.", "Ask for a short fixed period and a written receipt.",
        "Original documents kuch time ke liye rakhe jayenge.", "Chhota fixed period aur written receipt maango."),
    "flat_refund": (
        "A flat training cost is refundable on early exit.", "Ask for pro-rata recovery of actual costs.",
        "Jaldi nikalne par flat training cost wapas karni hogi.", "Actual cost ka pro-rata recovery maango."),
    "broad_deductions": (
        "Broad deductions may be adjusted.", "Ask which deductions are allowed.",
        "Broad deductions adjust ho sakti hain.", "Poochho kaun si deductions allowed hain."),
    "long_refund_window": (
        "The refund takes longer than 30 days.", "Ask for a refund within 30 days.",
        "Refund mein 30 din se zyada lagenge.", "30 din ke andar refund maango."),
    "long_lock_in": (
        "The lock-in is longer than 12 months.", "Ask for a shorter lock-in.",
        "Lock-in 12 mahine se lamba hai.", "Chhota lock-in maango."),
    "high_escalation": (
        "The yearly rent increase is above 10%.", "Ask for a lower fixed increase.",
        "Saalana rent increase 10% se zyada hai.", "Kam fixed increase maango."),
    "high_deduction_cap": (
        "Pay deductions can exceed 10%.", "Ask for a lower cap.",
        "Pay deductions 10% se upar ja sakti hain.", "Kam cap maango."),
    "long_bond": (
        "The bond period is longer than 24 months.", "Ask for a shorter bond.",
        "Bond period 24 mahine se lamba hai.", "Chhota bond maango."),
    "long_notice": (
        "The notice period is longer than 90 days.", "Ask for a shorter notice period.",
        "Notice period 90 din se lamba hai.", "Chhota notice period maango."),
}  # fmt: skip

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers(text: str) -> set[str]:
    return {m.group(0).replace(",", "").rstrip(".") for m in _NUM.finditer(text)}


def check_grounded(facts_line: str, clause_text: str) -> bool:
    """True if every number in the facts line also appears in the clause text."""
    return _numbers(facts_line) <= _numbers(clause_text)


def facts_line(facts: list[Fact]) -> str:
    seen: set[tuple[str, str]] = set()
    parts = []
    for f in facts:
        if f.type == "date" or (f.role, f.text) in seen:
            continue
        seen.add((f.role, f.text))
        parts.append(f"{ROLE_NAME.get(f.role, f.type.title())}: {f.text}")
    return " · ".join(parts)


def explain_clause(
    clause_id: str,
    risk: str | None,
    flags: list[tuple[str, str]],
    facts: list[Fact],
    lang: str = "en",
) -> dict:
    """Summary, reasons, tips and facts line for one clause (never invents numbers)."""
    if lang not in LANGS:
        raise ValueError(f"lang must be one of {LANGS}")
    col = 0 if lang == "en" else 1
    info = CLAUSE_INFO.get(clause_id)
    summary = info[col] if info else ""
    reasons, tips = [], []
    for flag, _ in flags:
        texts = FLAG_TEXT.get(flag)
        if texts:
            reason, tip = (texts[0], texts[1]) if col == 0 else (texts[2], texts[3])
            if reason not in reasons:
                reasons.append(reason)
            if tip not in tips:
                tips.append(tip)
    return {
        "risk_label": RISK_LABEL[lang][risk] if risk else None,
        "summary": summary,
        "reasons": reasons,
        "tips": tips,
        "facts_line": facts_line(facts),
    }
