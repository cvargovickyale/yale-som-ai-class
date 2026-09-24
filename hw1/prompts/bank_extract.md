# Bank statement extraction prompt

You extract every transaction line from the January 2026 business bank
statement into a JSON array. Return one JSON object per statement line. Use only
information explicitly shown on the statement; do not invent or combine lines.

Required fields for each transaction:

- `date`: the posting or transaction date as printed on the statement
- `description`: the transaction description exactly or nearly exactly as shown
- `amount_usd`: the absolute dollar amount as a positive number
- `classification`: either `business` or `personal`
- `direction`: either `credit` or `debit`
- `accounting_label`: one of `revenue`, `expense`, `owner_draw`, or `transfer`
- `expense_type`: when `accounting_label` is `expense`, use a useful subtype
  such as `rent`, `utilities`, `cogs_parts`, `shipping`, `tools_equipment`,
  `insurance`, or `other`; otherwise use null
- `source_file`: the exact source PDF filename
- `fields_not_found`: an array of required field names that could not be
  determined from the statement

Use a positive number for `amount_usd` regardless of whether the line is a
credit or debit. Use `direction` to preserve that distinction. Classify each
line as business or personal based on the statement and available transaction
context. Use `transfer` for transfers between accounts, not revenue or expense.
Use `owner_draw` for personal spending paid from the business account when it
is not a business expense. Use null and list the field in `fields_not_found`
when a required value cannot be supported by the document.

Source filename: {source_file}

Statement text:
{statement_text}
