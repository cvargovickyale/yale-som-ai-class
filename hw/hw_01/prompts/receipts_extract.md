# Receipt extraction prompt

You extract structured purchase data from one business receipt PDF.

Return exactly one JSON object for the supplied receipt. Use only information
that is explicitly present in the document. Do not infer, estimate, or fill in
missing values. Put the JSON field name of every missing required value in
`fields_not_found`.

Required fields:

- `vendor`: the store or supplier name
- `date`: the transaction date, using the date as printed in the document
- `description`: a concise description of what was purchased
- `amount_usd`: the total for the receipt in US dollars, as a number without a
  dollar sign
- `category`: one concise expense label, such as `cogs_parts`,
  `tools_equipment`, `shipping`, `office_supplies`, or `other`
- `source_file`: the exact source PDF filename supplied by the caller
- `fields_not_found`: an array containing the names of any required fields that
  could not be determined from the document

For a missing scalar value, use `null`. Do not put a field in
`fields_not_found` if it is supported by the document. Preserve the receipt's
vendor, date, purchase description, and total faithfully. If a receipt has
multiple items, summarize them in `description` and use the receipt total for
`amount_usd`. Do not extract totals from a bank statement or credit-card
statement as though they were receipt totals.

Receipt filename: {source_file}

Receipt text:
{receipt_text}
