from rapidfuzz import fuzz

from app.config import get_settings
from app.models import Vendor
from app.pipeline.context import RunContext
from app.rules.checks import check_c05, check_c06, check_c07, mask_account
from app.rules.gstin import is_valid_gstin
from app.schemas import CheckResult, StageOutcome


async def run(ctx: RunContext) -> StageOutcome:
    settings = get_settings()
    ext = ctx.extraction
    norm = ctx.normalized
    session = ctx.session

    if not ext or not norm:
        return StageOutcome(
            status="FAILED",
            summary="Skipped: needs output from Normalize stage",
            output={"error": "Normalize missing"},
            checks=[],
        )

    matched_vendor: Vendor | None = None
    method_str = "none"

    all_vendors = session.query(Vendor).all()

    # 1. Exact GSTIN lookup
    if norm.vendor_gstin and is_valid_gstin(norm.vendor_gstin):
        for v in all_vendors:
            if v.gstin and v.gstin.upper() == norm.vendor_gstin:
                matched_vendor = v
                method_str = "GSTIN"
                break

    # 2. Fuzzy name matching if not matched by GSTIN
    if not matched_vendor and norm.vendor_name:
        clean_inv_name = norm.vendor_name.strip()
        best_score = 0.0
        best_vendor = None

        for v in all_vendors:
            # Check legal name
            s1 = fuzz.token_set_ratio(clean_inv_name, v.legal_name)
            if s1 > best_score:
                best_score = s1
                best_vendor = v

            # Check aliases
            for alias in v.aliases or []:
                s2 = fuzz.token_set_ratio(clean_inv_name, alias)
                if s2 > best_score:
                    best_score = s2
                    best_vendor = v

        if best_vendor and best_score >= settings.VENDOR_NAME_MATCH_MIN:
            matched_vendor = best_vendor
            method_str = f"name (score {best_score:.0f})"

    ctx.vendor = matched_vendor
    ctx.vendor_match_method = method_str

    # Run checks in fixed order: C06, C05, C07
    checks: list[CheckResult] = []
    checks.append(check_c06(ext, matched_vendor, method_str))
    checks.append(check_c05(matched_vendor))
    checks.append(check_c07(ext, matched_vendor))

    ctx.all_checks.extend(checks)

    flag_count = sum(1 for c in checks if c.outcome == "FLAG")
    status = "FLAGGED" if flag_count > 0 else "PASSED"

    if matched_vendor:
        summary = f"{matched_vendor.legal_name} · {matched_vendor.status}"
        output = {
            "vendor_id": matched_vendor.vendor_id,
            "vendor_name": matched_vendor.legal_name,
            "method": method_str,
            "master_bank_masked": mask_account(matched_vendor.bank_account_number),
        }
    else:
        summary = "Unknown vendor"
        output = {
            "vendor_id": None,
            "vendor_name": None,
            "method": "none",
            "master_bank_masked": None,
        }

    ctx.stage_outputs["vendor"] = output

    return StageOutcome(
        status=status,
        summary=summary,
        output=output,
        checks=checks,
    )
