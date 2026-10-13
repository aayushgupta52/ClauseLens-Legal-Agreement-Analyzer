"""Hand-written clause templates for the 15 clause types with no public labeled data.

Syntax: {slot} draws a value (see generator.SLOTS), {a|b|c} picks one alternative, and the
role slots {owner} {tenant} {employer} {employee} come from the document's role set.

Every part has TWO phrasings: index 0 is used for train/val, index 1 ONLY for the held-out
test pool. So the synthetic test set measures generalisation to unseen phrasing, not just to
unseen slot values. Risk labels follow docs/risk_rubric.md and are working hypotheses that an
advocate must validate before they are treated as ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass

Pair = tuple[str, str]


@dataclass(frozen=True)
class ClauseSpec:
    clause_id: str
    doc_type: str
    heading: str
    core: Pair
    mods: tuple[Pair, Pair, Pair]  # green, amber, red
    flags: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]


SPECS: dict[str, ClauseSpec] = {}


def _c(clause_id, doc_type, heading, core, green, amber, red, amber_flags=(), red_flags=()):
    SPECS[clause_id] = ClauseSpec(
        clause_id, doc_type, heading, core, (green, amber, red), ((), amber_flags, red_flags)
    )


# fmt: off
# ------------------------------------------------------------------ rent_agreement
_c(
    "security_deposit", "rent_agreement", "SECURITY DEPOSIT",
    ("The {tenant} has paid to the {owner} an interest-free refundable security deposit of "
     "{deposit_amount} {at the time of|on} signing this Agreement.",
     "By way of security, the {tenant} shall keep {deposit_amount} with the {owner}, which "
     "carries no interest."),
    ("The deposit shall be {refunded|returned} within {refund_days} of the {tenant} vacating "
     "the premises, after deducting only unpaid rent and the cost of proven damage.",
     "On handing back possession, the {owner} shall return the deposit within {refund_days}, "
     "less only outstanding dues and documented repair costs."),
    ("The deposit shall be refunded within {long_refund_days} of vacation, after the {owner} "
     "inspects the premises and adjusts all dues, damages and other charges.",
     "Refund of the deposit will be made within {long_refund_days} once the {owner} has "
     "verified the condition of the premises and settled all charges."),
    ("The {owner} may deduct any amount from the deposit as it deems fit, and the balance, if "
     "any, shall be refunded at the {owner}'s discretion.",
     "The deposit is liable to be forfeited in part or in full for any reason the {owner} "
     "considers appropriate, and no time limit applies to its return."),
    ("long_refund_window", "broad_deductions"),
    ("discretionary_deductions", "no_refund_timeline"),
)
_c(
    "lock_in_period", "rent_agreement", "LOCK-IN PERIOD",
    ("A lock-in period of {lock_in_months} applies from the date of commencement of this "
     "Agreement.",
     "The first {lock_in_months} of the tenancy shall be treated as the lock-in period."),
    ("The lock-in applies equally to both parties, and either may exit after it on "
     "{notice_days} written notice without any penalty.",
     "Both parties are bound by this lock-in, and thereafter either may leave on "
     "{notice_days} written notice without paying anything."),
    ("If the {tenant} leaves earlier, the {tenant} shall pay {penalty_months} rent as "
     "compensation to the {owner}.",
     "Early exit by the {tenant} within the lock-in will attract a payment equal to "
     "{penalty_months} rent."),
    ("Only the {tenant} is bound by the lock-in, and on early exit the {tenant} shall forfeit "
     "the entire security deposit and pay rent for the whole remaining period.",
     "The {owner} may terminate at any time, but if the {tenant} leaves during the lock-in, "
     "the deposit is forfeited and rent for the unexpired period becomes immediately payable."),
    ("exit_penalty",),
    ("one_sided", "forfeiture", "uncapped_exit_cost"),
)
_c(
    "rent_escalation", "rent_agreement", "RENT REVISION",
    ("The rent payable under this Agreement is {rent} per month and is subject to revision as "
     "follows.",
     "Rent for the tenancy begins at {rent} per month and may be revised during the term."),
    ("The rent shall increase by a fixed {escalation_pct} after every {escalation_months}.",
     "A fixed increase of {escalation_pct} will apply on completion of each "
     "{escalation_months}, and no other increase is permitted."),
    ("The rent shall increase by {escalation_pct} every {escalation_months}, and the {owner} "
     "may also revise it on renewal at current market rates.",
     "A {escalation_pct} increase applies every {escalation_months}; on renewal the rent will "
     "be re-fixed at the prevailing market rate."),
    ("The {owner} may increase the rent at any time and by any amount, and the {tenant} must "
     "pay the revised rent from the next month.",
     "The rent is liable to enhancement as decided by the {owner} from time to time, without "
     "prior consent or a stated limit."),
    ("market_rate_reset",),
    ("unilateral_change", "no_cap"),
)
_c(
    "maintenance_repairs", "rent_agreement", "REPAIRS AND MAINTENANCE",
    ("Repairs and maintenance of the premises during the tenancy shall be dealt with as set "
     "out below.",
     "The parties shall bear the cost of upkeep and repairs of the premises in the following "
     "manner."),
    ("The {owner} shall bear structural repairs and major breakdowns, and the {tenant} shall "
     "bear minor day-to-day repairs up to {repair_limit} per occasion.",
     "Structural and major repairs are the {owner}'s responsibility; the {tenant} pays only "
     "for minor repairs costing up to {repair_limit} each."),
    ("The {tenant} shall bear all repairs and replacements of fittings and fixtures, while the "
     "{owner} shall bear structural repairs.",
     "All wear and tear to fittings, fixtures and appliances shall be repaired at the "
     "{tenant}'s cost, except structural defects."),
    ("The {tenant} shall bear the cost of all repairs and maintenance of every kind, including "
     "structural repairs and major breakdowns.",
     "No repair of any nature shall be the {owner}'s liability, and the {tenant} shall meet "
     "all repair and replacement costs, including structural defects."),
    ("tenant_bears_fittings",),
    ("tenant_bears_structural",),
)
_c(
    "utilities_and_charges", "rent_agreement", "UTILITIES AND CHARGES",
    ("Charges for electricity, water, piped gas and internet during the tenancy shall be "
     "settled as follows.",
     "Recurring charges for utilities and services at the premises shall be borne as stated "
     "below."),
    ("The {tenant} shall pay utility bills as per actual consumption, and the society "
     "maintenance of {maintenance_charge} per month shall be borne by the {owner}.",
     "Utilities are payable by the {tenant} on actual meter readings, while the {owner} pays "
     "property tax and the society maintenance of {maintenance_charge} per month."),
    ("The {tenant} shall pay all utility bills and the society maintenance of "
     "{maintenance_charge} per month, along with any future increase.",
     "Utility bills as well as society charges of {maintenance_charge} per month, including "
     "later revisions, shall be paid by the {tenant}."),
    ("The {tenant} shall pay all utility, society and other charges of whatever nature as "
     "demanded by the {owner}, without any right to see the bills.",
     "Charges of every kind shall be paid by the {tenant} in the amount the {owner} specifies "
     "from time to time, and the {owner}'s demand shall be final."),
    ("future_increases_on_tenant",),
    ("unitemised_charges", "unilateral_amount"),
)
_c(
    "owner_entry_inspection", "rent_agreement", "ENTRY AND INSPECTION",
    ("The {owner} may enter the premises for inspection or repairs in the manner stated "
     "below.",
     "Access to the premises by the {owner} during the tenancy shall be subject to the "
     "following."),
    ("Entry shall be permitted only at reasonable hours after giving the {tenant} at least "
     "{entry_notice_hours} prior notice, except in an emergency.",
     "The {owner} must give not less than {entry_notice_hours} notice and may visit only "
     "during reasonable hours, save in a genuine emergency."),
    ("The {owner} may enter the premises for inspection with prior intimation, which may be "
     "given orally or by message.",
     "The {owner} or an agent may visit the premises periodically after informing the "
     "{tenant} in any manner."),
    ("The {owner} and its agents may enter the premises at any time, with or without notice, "
     "and the {tenant} shall not object.",
     "The {tenant} shall allow the {owner} to enter and inspect the premises at all hours "
     "without prior intimation."),
    ("informal_notice",),
    ("entry_without_notice",),
)
_c(
    "subletting_guests", "rent_agreement", "SUBLETTING AND GUESTS",
    ("The use of the premises by persons other than the {tenant} is regulated as follows.",
     "Subletting, sharing and the stay of guests at the premises shall be governed by the "
     "following terms."),
    ("The {tenant} shall not sublet the premises without written consent, and guests may stay "
     "up to {guest_days} without any approval.",
     "Subletting requires the {owner}'s written consent; visitors may stay for up to "
     "{guest_days} without permission."),
    ("The {tenant} shall not sublet or share the premises, and any guest staying beyond "
     "{guest_days} requires the prior consent of the {owner}.",
     "No sharing of the premises is permitted, and guests may not stay for more than "
     "{guest_days} unless the {owner} approves."),
    ("No person other than the {tenant} may stay at the premises, including family members, "
     "without the {owner}'s written permission, failing which the {owner} may terminate this "
     "Agreement immediately and forfeit the deposit.",
     "Any overnight guest or occupant not named in this Agreement shall be treated as a breach "
     "entitling the {owner} to evict the {tenant} forthwith and retain the deposit."),
    ("strict_guest_limit",),
    ("overbroad_restriction", "eviction_threat"),
)
_c(
    "eviction_default", "rent_agreement", "DEFAULT AND EVICTION",
    ("If the {tenant} defaults in the payment of rent or breaches this Agreement, the "
     "following shall apply.",
     "The consequences of non-payment of rent or any other breach by the {tenant} are as set "
     "out below."),
    ("The {owner} shall first give a written notice and a cure period of {cure_days}, and may "
     "terminate only if the default continues after that period.",
     "Termination for default is permitted only after the {tenant} has been given written "
     "notice and {cure_days} to remedy it."),
    ("If rent remains unpaid for {default_days}, the {owner} may terminate this Agreement by "
     "giving notice, and the {tenant} shall vacate promptly.",
     "Non-payment of rent beyond {default_days} entitles the {owner} to end the tenancy on "
     "notice, and the {tenant} must then hand over possession."),
    ("On any default, however small, the {owner} may evict the {tenant} immediately without "
     "notice, forfeit the deposit and lock the premises.",
     "The {owner} may take back possession at once and without any notice if the {tenant} "
     "delays a payment or breaches any term, and the deposit shall stand forfeited."),
    ("short_default_window",),
    ("no_notice", "self_help_eviction", "forfeiture"),
)
_c(
    "tenant_verification", "rent_agreement", "POLICE VERIFICATION",
    ("The {tenant} shall complete the verification formalities required for the tenancy.",
     "Verification of the {tenant} and of the documents supplied by the {tenant} shall be "
     "handled as follows."),
    ("The {tenant} shall submit identity proof and assist with police verification within "
     "{verification_days} of taking possession, and the {owner} shall bear any filing fees.",
     "Within {verification_days} of moving in, the {tenant} shall provide identity documents "
     "for police verification, and the {owner} shall complete the filing at its own cost."),
    ("The {tenant} shall submit identity proof and complete police verification within "
     "{verification_days}, at the {tenant}'s own cost.",
     "Police verification and all related formalities shall be completed by the {tenant} within "
     "{verification_days} at the {tenant}'s expense."),
    ("The {owner} may retain the original identity documents of the {tenant} until the end of "
     "the tenancy, and the {tenant} shall bear all verification costs and penalties.",
     "Original identity documents of the {tenant} shall be kept by the {owner} for the entire "
     "tenancy, and any penalty arising from verification shall be paid by the {tenant}."),
    ("costs_on_tenant",),
    ("originals_retained", "penalties_on_tenant"),
)
_c(
    "handover_inventory", "rent_agreement", "INVENTORY AND HANDOVER",
    ("The condition of the premises and the inventory of fittings shall be recorded for "
     "handover.",
     "Possession of the premises and the list of furniture and fittings provided shall be "
     "documented as described below."),
    ("An inventory list signed by both parties is annexed to this Agreement, and the premises "
     "shall be returned in the same condition, normal wear and tear excepted.",
     "Both parties have signed the attached inventory, and the {tenant} shall return the "
     "premises in their original condition apart from ordinary wear and tear."),
    ("The {tenant} shall return the premises in good condition and shall bear the cost of "
     "repainting at the time of vacating.",
     "At the end of the tenancy the {tenant} shall hand back the premises in good condition "
     "and bear the cost of repainting and cleaning."),
    ("No inventory is recorded, and the {owner}'s assessment of the condition of the premises "
     "and of any damage shall be final and binding on the {tenant}.",
     "The {owner} alone shall decide whether the premises are damaged and what is to be "
     "recovered, and the {tenant} shall not dispute that decision."),
    ("mandatory_repainting",),
    ("no_inventory", "unilateral_assessment"),
)

# ------------------------------------------------------------------ offer_and_bond
_c(
    "service_bond", "offer_and_bond", "SERVICE BOND",
    ("The {employee} agrees to serve the {employer} for a minimum period as stated below.",
     "This offer is subject to the {employee} completing a minimum period of service with the "
     "{employer}, as follows."),
    ("If the {employee} leaves before completing {bond_months} of service, the {employee} "
     "shall pay a pro-rata share of {bond_amount} for the period not served.",
     "Should the {employee} resign within {bond_months}, only a proportionate part of "
     "{bond_amount}, based on the unserved period, shall be recoverable."),
    ("If the {employee} leaves before completing {bond_months} of service, the {employee} "
     "shall pay a proportionate amount as determined by the {employer}.",
     "On leaving within {bond_months}, the {employee} shall reimburse a reasonable amount for "
     "the period not served, as the {employer} calculates it."),
    ("If the {employee} leaves for any reason before completing {bond_months} of service, the "
     "full bond amount of {bond_amount} shall become payable, irrespective of the period "
     "already served.",
     "The {employee} shall pay {bond_amount} in full if service ends before {bond_months}, "
     "regardless of how much of the period has been completed."),
    ("undefined_amount",),
    ("full_amount_regardless",),
)
_c(
    "training_cost_recovery", "offer_and_bond", "TRAINING COSTS",
    ("The {employer} may recover the cost of training given to the {employee} in the "
     "circumstances described below.",
     "Costs incurred by the {employer} on onboarding and training of the {employee} are "
     "recoverable as set out below."),
    ("Recovery is limited to actual, itemised training expenses up to {training_cost}, reduced "
     "in proportion to the service completed.",
     "Only documented training costs not exceeding {training_cost} may be recovered, and the "
     "amount reduces for each month of service completed."),
    ("If the {employee} leaves within {recovery_months}, the {employee} shall refund the "
     "training cost of {training_cost}.",
     "A refund of {training_cost} towards training shall be payable if the {employee} resigns "
     "within {recovery_months} of joining."),
    ("The {employee} shall reimburse the entire cost of training, as computed by the "
     "{employer}, whenever the employment ends for any reason, with no limit on the amount.",
     "All training and onboarding expenses, in the amount the {employer} determines, shall be "
     "repaid by the {employee} on exit, without any ceiling or itemisation."),
    ("flat_refund",),
    ("uncapped", "no_itemisation"),
)
_c(
    "notice_period", "offer_and_bond", "NOTICE PERIOD",
    ("The notice required to end the employment is as follows.",
     "Termination of this employment requires notice in the following manner."),
    ("Either party may end the employment by giving {notice_days} written notice, or salary in "
     "lieu of notice.",
     "The {employee} and the {employer} are each required to give {notice_days} notice of "
     "termination, or pay in lieu."),
    ("The {employee} shall give {emp_notice_days} notice, while the {employer} may end the "
     "employment by giving {er_notice_days} notice.",
     "A notice of {emp_notice_days} is required from the {employee}, whereas the {employer} "
     "need only give {er_notice_days}."),
    ("The {employee} must give {emp_notice_days} notice, but the {employer} may terminate the "
     "employment at any time without notice or reason.",
     "While the {employee} is bound to serve {emp_notice_days} notice, the {employer} may end "
     "the employment forthwith without notice or compensation."),
    ("asymmetric_notice",),
    ("one_sided", "no_employer_notice"),
)
_c(
    "document_retention", "offer_and_bond", "ORIGINAL DOCUMENTS",
    ("Documents submitted by the {employee} at the time of joining shall be handled as "
     "follows.",
     "The {employer} shall deal with the educational and identity documents of the {employee} "
     "in the following manner."),
    ("The {employer} shall take only photocopies, and originals shall be verified and returned "
     "to the {employee} on the date of joining.",
     "Originals are to be shown for verification and returned the same day, and the "
     "{employer} will keep only copies."),
    ("The {employer} may retain the original certificates for up to {retention_months} for "
     "verification and shall return them thereafter.",
     "Original documents will be held by the {employer} for background verification for up to "
     "{retention_months} from the date of joining."),
    ("The {employer} shall retain the original educational certificates of the {employee} "
     "until the {employee} completes the entire service bond period.",
     "Original marksheets and certificates shall remain with the {employer} for the duration "
     "of the bond and will be returned only after its completion and clearance of all dues."),
    ("temporary_retention",),
    ("originals_withheld",),
)
_c(
    "salary_deductions", "offer_and_bond", "SALARY DEDUCTIONS",
    ("Deductions from the salary or stipend of the {employee} shall be made as stated below.",
     "The {employer} may make the following deductions from the pay of the {employee}."),
    ("Deductions shall be limited to statutory taxes and contributions and shall be itemised "
     "in the monthly payslip.",
     "Only deductions required by law will be made, and each of them will be shown separately "
     "in the payslip."),
    ("The {employer} may deduct up to {deduction_pct} of the monthly salary towards recovery "
     "of advances, losses or damages caused by the {employee}.",
     "A deduction not exceeding {deduction_pct} of the monthly pay may be made to recover any "
     "dues or losses attributed to the {employee}."),
    ("The {employer} may deduct any amount from the salary or stipend towards dues, losses or "
     "penalties as determined by the {employer}, and may withhold the final settlement until "
     "all recoveries are made.",
     "Any sum the {employer} considers recoverable from the {employee} may be deducted from "
     "the pay at any time, and the final dues shall be withheld until recovery is complete."),
    ("loss_recovery",),
    ("uncapped", "withholding_final_dues"),
)

# Clause order inside a generated document.
ORDER: dict[str, list[str]] = {
    "rent_agreement": [
        "security_deposit", "lock_in_period", "rent_escalation", "maintenance_repairs",
        "utilities_and_charges", "owner_entry_inspection", "subletting_guests",
        "eviction_default", "tenant_verification", "handover_inventory",
    ],
    "offer_and_bond": [
        "service_bond", "training_cost_recovery", "notice_period", "document_retention",
        "salary_deductions",
    ],
}

# Neutral clauses used only to make generated documents look complete (not sampled as data).
COMMON: dict[str, tuple[str, str, Pair]] = {
    "governing_law": (
        "GOVERNING LAW",
        "common",
        ("This Agreement shall be governed by and construed in accordance with the laws of India.",
         "The laws of India shall apply to this Agreement and to its interpretation."),
    ),
    "dispute_resolution": (
        "JURISDICTION",
        "common",
        ("Any dispute arising out of this Agreement shall be subject to the exclusive "
         "jurisdiction of the courts at {city}.",
         "The courts at {city} shall alone have jurisdiction over any dispute relating to this "
         "Agreement."),
    ),
    "entire_agreement": (
        "ENTIRE AGREEMENT",
        "common",
        ("This Agreement contains the entire understanding between the parties and supersedes "
         "all prior discussions.",
         "No prior arrangement shall bind the parties, as this Agreement records the whole of "
         "their understanding."),
    ),
}

# Non-clause text (label "other"): preambles and closing / signature lines.
FILLERS: dict[str, Pair] = {
    "preamble_rent_agreement": (
        "This Agreement is made at {city} on this {day} day of {month}, {year}, between "
        "{owner_name}, hereinafter called the {owner}, and {tenant_name}, hereinafter called "
        "the {tenant}, in respect of flat no. {flat_no} at {locality}, {city}.",
        "WHEREAS {owner_name}, the {owner}, is the lawful owner of flat no. {flat_no}, "
        "{locality}, {city}, and has agreed to let it to {tenant_name}, the {tenant}, from "
        "{day} {month} {year}.",
    ),
    "preamble_offer_and_bond": (
        "Dear {employee_name}, we are pleased to offer you the position of {designation} at "
        "{employer_name}, with effect from {day} {month} {year}, on the terms set out below.",
        "This letter confirms the appointment of {employee_name} as {designation} with "
        "{employer_name} from {day} {month} {year}, subject to the following terms.",
    ),
    "trailer_rent_agreement": (
        "IN WITNESS WHEREOF the parties have signed this Agreement on the day and year first "
        "written above.",
        "Signed and delivered by the parties in the presence of the witnesses named below.",
    ),
    "trailer_offer_and_bond": (
        "Accepted and agreed by the {employee} on the date written below.",
        "ACCEPTED: I have read and understood the above terms and agree to them.",
    ),
}
# fmt: on
