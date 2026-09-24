# Reconciliation prompt

You reconcile business records for January 2026. Review the supplied receipt,
bank-transaction, credit-card-transaction, and supporting-document evidence.
The same purchase may appear in a receipt and on the credit-card statement.
Bank deposits may mix business and personal funds. Emails and voice memos may
describe amounts that do not match a single PDF.

Return a JSON array containing one row for each amount that needs a decision,
appears in more than one source, or is otherwise relevant to reconciling the
records. Do not return every raw line automatically. Avoid double counting: a
single real-world purchase or deposit should normally produce one reconciled
row even when it appears in several documents.

Each row must contain:

- `id`: a short, unique slug for the reconciled item
- `sources`: a list of exact document filenames used for this row
- `amounts_seen`: an object mapping each source filename to the dollar amount
  shown in that source; use positive numbers
- `included_in_income_statement`: exactly `yes` or `no`
- `amount_used_in_income_statement`: the final positive dollar amount included,
  or 0 when excluded
- `resolution`: plain-English explanation of how the sources were matched and
  why the final amount was selected

Use only the supplied evidence. Do not invent amounts or source filenames. Use
the receipt total for a confirmed purchase when it agrees with the corresponding
card charge, and do not count that purchase twice. Exclude personal spending,
transfers, and non-business items from the income statement. Treat unresolved
or non-transactional commentary according to the documents and explain the
decision in `resolution`. Include sources for the supporting emails or memos
when they influenced the decision.

RECEIPTS JSON:
{receipts_json}

BANK TRANSACTIONS JSON:
{bank_json}

CREDIT-CARD TRANSACTIONS JSON:
{card_json}

SUPPORTING DOCUMENT TEXT:
{supporting_text}
