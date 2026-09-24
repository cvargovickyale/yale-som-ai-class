# Credit card statement extraction prompt

You extract every charge from the January 2026 credit-card statement into one
JSON object per charge. Use only information explicitly shown on the statement;
do not invent, combine, or omit charges.

Required fields:

- `date`: the charge date as printed on the statement
- `merchant`: the merchant name as shown on the statement
- `amount_usd`: the charge amount as a positive number
- `classification`: either `business` or `personal`
- `expense_category`: for business charges, use a useful category such as
  `rent`, `utilities`, `cogs_parts`, `shipping`, `tools_equipment`,
  `insurance`, `office_supplies`, `groceries`, or `other`; for personal charges,
  use null
- `source_file`: the exact source PDF filename
- `fields_not_found`: an array of required field names that could not be
  determined from the statement

The category is only a preliminary extraction. Do not force a personal charge
into a business category. Keep `amount_usd` positive. If a required value is
not supported by the statement, use null and list its field name in
`fields_not_found`.

Source filename: {source_file}

Credit-card statement text:
{statement_text}
