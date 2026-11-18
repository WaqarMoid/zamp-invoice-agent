from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import POLine, PurchaseOrder
from app.rules.consumption import get_po_remaining_net
from app.rules.dates import extract_date_from_text
from app.rules.text import desc_similarity
from app.schemas import NormalizedInvoice, NormalizedLine


def match_invoice_lines_to_po(
    inv_lines: list[NormalizedLine],
    po_lines: list[POLine],
) -> tuple[list[dict[str, Any]], list[NormalizedLine]]:
    """
    Greedy line pairing per doc 07 §7.4.4.
    score = 0.5*desc + 0.3*hsn + 0.2*price
    Returns (matched_pairs, unmatched_inv_lines).
    """
    candidate_pairs: list[dict[str, Any]] = []

    for inv in inv_lines:
        for po in po_lines:
            # 1. desc similarity (0..1)
            desc_sim = desc_similarity(inv.description, po.description)

            # 2. HSN exact match
            hsn_match = 1.0 if inv.hsn_sac and po.hsn_sac and inv.hsn_sac == po.hsn_sac else 0.0

            # 3. Price variance score: 1 - min(1, abs(inv_unit - po_unit) / po_unit * 10)
            po_unit = Decimal(str(po.unit_price_paise)) / Decimal("100")
            inv_unit = inv.unit_price_net
            if po_unit > 0:
                price_diff_ratio = abs(inv_unit - po_unit) / po_unit
                price_score = max(0.0, 1.0 - min(1.0, float(price_diff_ratio * 10)))
            else:
                price_score = 1.0 if inv_unit == 0 else 0.0

            total_score = round(0.5 * desc_sim + 0.3 * hsn_match + 0.2 * price_score, 4)

            candidate_pairs.append(
                {
                    "inv_index": inv.index,
                    "inv_line": inv,
                    "po_line_no": po.line_no,
                    "po_line": po,
                    "score": total_score,
                    "desc_sim": round(desc_sim, 4),
                    "hsn_match": hsn_match,
                    "price_score": round(price_score, 4),
                }
            )

    # Sort descending by score
    candidate_pairs.sort(key=lambda x: x["score"], reverse=True)

    matched: list[dict[str, Any]] = []
    used_inv_indices: set[int] = set()
    used_po_line_nos: set[int] = set()

    for pair in candidate_pairs:
        if pair["score"] < 0.60:
            continue
        if pair["inv_index"] in used_inv_indices or pair["po_line_no"] in used_po_line_nos:
            continue
        matched.append(pair)
        used_inv_indices.add(pair["inv_index"])
        used_po_line_nos.add(pair["po_line_no"])

    unmatched = [inv for inv in inv_lines if inv.index not in used_inv_indices]
    return matched, unmatched


def infer_po_for_invoice(
    session: Session,
    normalized: NormalizedInvoice,
    vendor_id: str,
) -> tuple[PurchaseOrder | None, str, list[dict[str, Any]]]:
    """
    PO resolution and inference per doc 07 §7.4.3.
    Returns:
      (matched_po, method, candidates_info)
      where method in {"explicit", "inferred", "printed_not_found", "none"}
    """
    # 1. Explicit PO number check
    if normalized.po_number_norm:
        po = (
            session.query(PurchaseOrder)
            .filter(PurchaseOrder.po_number_norm == normalized.po_number_norm)
            .first()
        )
        if po:
            return po, "explicit", []

    # 2. Candidate collection for inference
    # Candidates: POs of matched vendor with status == OPEN and remaining net value > 0
    vendor_pos = (
        session.query(PurchaseOrder)
        .filter(
            PurchaseOrder.vendor_id == vendor_id,
            PurchaseOrder.status == "OPEN",
        )
        .all()
    )

    open_pos_with_balance: list[tuple[PurchaseOrder, Decimal]] = []
    for p in vendor_pos:
        rem_net = get_po_remaining_net(session, p.po_number)
        if rem_net > 0:
            open_pos_with_balance.append((p, rem_net))

    if not open_pos_with_balance:
        method = "printed_not_found" if normalized.po_number else "none"
        return None, method, []

    # Parse date from po_reference_text if present
    ref_date = normalized.po_reference_date
    if not ref_date and normalized.po_reference_text:
        ref_date = extract_date_from_text(normalized.po_reference_text)

    inv_lines = normalized.lines
    inv_net = normalized.net_total
    candidates_info: list[dict[str, Any]] = []

    for po, po_rem_net in open_pos_with_balance:
        # Compute coverage: fraction of inv lines whose best line-match score against this PO's lines >= 0.60
        covered_count = 0
        for inv in inv_lines:
            best_score = 0.0
            for pol in po.lines:
                desc_sim = desc_similarity(inv.description, pol.description)
                hsn_m = 1.0 if inv.hsn_sac and pol.hsn_sac and inv.hsn_sac == pol.hsn_sac else 0.0
                po_u = Decimal(str(pol.unit_price_paise)) / Decimal("100")
                if po_u > 0:
                    diff_ratio = abs(inv.unit_price_net - po_u) / po_u
                    pr_sc = max(0.0, 1.0 - min(1.0, float(diff_ratio * 10)))
                else:
                    pr_sc = 1.0 if inv.unit_price_net == 0 else 0.0
                sc = 0.5 * desc_sim + 0.3 * hsn_m + 0.2 * pr_sc
                if sc > best_score:
                    best_score = sc
            if best_score >= 0.60:
                covered_count += 1

        coverage = covered_count / len(inv_lines) if inv_lines else 0.0

        # Amount fit: 1 - min(1, abs(inv_net - po_remaining_net) / po_remaining_net)
        if po_rem_net > 0:
            fit_ratio = abs(inv_net - po_rem_net) / po_rem_net
            amount_fit = max(0.0, 1.0 - min(1.0, float(fit_ratio)))
        else:
            amount_fit = 0.0

        # Date bonus: 0.10 if a date parsed from po_reference_text equals po.po_date
        date_bonus = 0.10 if (ref_date and po.po_date == ref_date) else 0.0

        score = min(1.0, round(0.6 * coverage + 0.4 * amount_fit + date_bonus, 3))

        candidates_info.append(
            {
                "po_number": po.po_number,
                "po": po,
                "coverage": round(coverage, 3),
                "amount_fit": round(amount_fit, 3),
                "date_bonus": date_bonus,
                "score": score,
                "remaining_net": float(po_rem_net),
            }
        )

    # Sort candidates descending by score
    candidates_info.sort(key=lambda c: c["score"], reverse=True)

    best_candidate = candidates_info[0]
    best_score = best_candidate["score"]
    second_score = candidates_info[1]["score"] if len(candidates_info) > 1 else 0.0

    selected = (best_score >= 0.75) and ((best_score - second_score) >= 0.15)

    if normalized.po_number:
        # If PO was printed but not found in DB
        method = "printed_not_found"
        matched_po = best_candidate["po"] if selected else None
        return matched_po, method, candidates_info

    if selected:
        return best_candidate["po"], "inferred", candidates_info

    return None, "none", candidates_info
