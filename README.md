# FRE-GY 9743 - Assignment 3

**Aditya Amit Shah | as22008**

[Completed notebook](hw3_products.ipynb) contains all written answers (Q1-Q3),
reproducible bond-futures calculations, a conditional CTD scenario example, and
executed cashflow creation/display examples. A [readable HTML copy](submission/Assignment_3_as22008.html) is also included. The written answers are included as
Markdown in the notebook, as permitted by the
[submission instructions](https://immense-chocolate-92e.notion.site/Github-Setup-HW-submission-2f1831d0b1d580eaacf8d8050867e9d9).

## Implementation

All six assigned TODOs are completed, preserving the FixedIncomeLib structure:

- [Cashflow products](fixedincomelib/product/linear_products.py): constructors for
  fixed-accrual and overnight-index contracts, plus both visitor dispatch methods.
- [Display visitor](fixedincomelib/product/product_display_visitor.py): ordered
  attributes for both product types.
- [Independent verification](tests/test_products.py): 20 tests for defaults,
  calendars, signed notionals, index/method handling, invalid inputs,
  serialization and visitor behavior.

## Results and conventions

For the written problem, the clean three-month forward is **99.50**, the
conversion factor is **0.862464869205427**, the normalized forward is
**115.3670178957**, and implied repo from the rounded 115.3670 quote is
**1.9999382625%**.

The notebook explicitly handles delivery accrued interest and explains the
spot-date conversion-factor convention intended by the quoted futures price.
It also distinguishes this simplified convention from actual exchange rules.
The CTD scenario uses a clearly labeled hypothetical two-bond basket because the
question does not supply an actual basket or future market observations.

## Run and verify

Use Python 3.11 or 3.12. From the repository root:

```sh
python -m pip install -r requirements.txt
jupyter notebook hw3_products.ipynb
```

Select that Python environment and run all cells in order. To run the independent
product checks separately:

```sh
python -m unittest discover -s tests -v
```

Verified with Python 3.12.14, NumPy 1.26.4, pandas 2.3.1 and QuantLib 1.41.
The notebook saves its numerical results and display tables. No live market data
connection is needed. Cashflow creation stores contractual fields; it does not
calculate overnight interest or present values without rates/fixings.

## Submission

Work is prepared on `Aditya_Shah_Branch`, following the required personal-branch
workflow. Publish that branch in your own fork of the instructor's repository,
then submit its GitHub branch URL through Brightspace. The complete repository
includes the notebook, library and tests; do not submit a ZIP or a single Python
file. Publishing and Brightspace submission remain separate actions.
