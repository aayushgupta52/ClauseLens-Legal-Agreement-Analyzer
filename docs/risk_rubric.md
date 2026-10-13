# ClauseLens risk rubric v1

Purpose: one consistent definition of **green / amber / red** for labeling the gold set
(Phase 2) and for the rule layer of the risk engine (Phase 6).

> Status: working hypotheses. Every threshold marked **[VALIDATE]** must be reviewed by a
> law student or advocate before it is treated as fact. ClauseLens is an awareness tool,
> not legal advice, and never claims a clause is "illegal" or "unenforceable".

## 1. Scoring (per clause)

Score each dimension 0 / 1 / 2:

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| **Balance** | Applies equally to both sides | Mildly favours the drafter | Clearly one-sided against the user |
| **Financial exposure** | None or small, clearly stated | Meaningful, but capped and stated | Large, uncapped, or not stated |
| **Clarity** | Specific and unambiguous | Some vague wording | Vague, undefined or open-ended |
| **Exit / reversibility** | User can leave or cure easily | Exit has a clear cost | Exit blocked, or cost disproportionate |

Total 0-8 → **Green** 0-2, **Amber** 3-5, **Red** 6-8.
Calibrate these cut-offs on the gold set (Phase 2) before freezing them.

## 2. Hard red flags (always Red, regardless of total)

- Employer keeps **original academic or identity documents** during employment or bond.
- Penalty or recovery amount that is **undefined**, or not tied to remaining service. **[VALIDATE]**
- Notice or termination right given to **only one side**.
- Deposit with **no refund timeline** or open-ended deductions. **[VALIDATE]**
- Owner may **enter without notice**, or evict without any stated process. **[VALIDATE]**
- Clause lets one side **change terms unilaterally**.

## 3. Per-clause guidance (rent_agreement)

| Clause | Green looks like | Red looks like |
|---|---|---|
| security_deposit | Amount, deduction reasons and refund timeline all stated | No timeline, or deductions "at owner's discretion" |
| lock_in_period | Short, equal for both sides | Long, or only the tenant is locked in, or heavy exit penalty **[VALIDATE]** |
| rent_escalation | Fixed, stated percentage and date | "As decided by owner" |
| owner_entry_inspection | Prior notice, reasonable hours | Entry at any time |
| maintenance_repairs | Responsibility split clearly | Tenant pays for everything incl. structural repairs |
| eviction_default | Cure period, stated process | Immediate eviction, forfeiture of deposit |

## 4. Per-clause guidance (offer_and_bond)

| Clause | Green looks like | Red looks like |
|---|---|---|
| service_bond | Pro-rata recovery, stated period | Full amount regardless of service completed |
| training_cost_recovery | Itemised, pro-rata, reasonable | Unitemised or unlimited |
| notice_period | Same for both sides | Long for employee, short or none for employer |
| non_compete | Narrow scope and duration, or absent | Wide scope, long duration, after exit **[VALIDATE]** |
| document_retention | Copies only | Originals withheld |
| salary_deductions | Itemised and tied to law or policy | Open-ended recoveries |

## 5. Labeling rules for the gold set

1. Label the **clause as written**, not what you think a court would do.
2. If the amount, period or party is missing, score Clarity = 2 and note "missing value".
3. Two annotators label independently; disagreements are resolved by discussion and logged.
4. Record Cohen's kappa between annotators; report it in the evaluation.
5. Never include real names, phone numbers or ID numbers in the gold set (anonymise first).
