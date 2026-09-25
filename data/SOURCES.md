# Sources

Every contract here comes from the Contract Understanding Atticus Dataset (CUAD) v1, curated and maintained by The Atticus Project, Inc. CUAD is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The underlying contracts are public filings on SEC EDGAR.

- Dataset: https://www.atticusprojectai.org/cuad
- Download used: https://zenodo.org/records/4595826 (`CUAD_v1.zip`, `full_contract_txt/`)
- Paper: https://arxiv.org/abs/2103.06268

## Cases

The filer is the company whose SEC filing attached the contract, as named in the CUAD file name or the filing's own page footer. The reporting entity is the seller whose revenue each case analyzes, and it is often the other party.

| Case | CUAD file | Filer | Reporting entity (seller) |
|---|---|---|---|
| `egain-hosting` | `WEBHELPCOMINC_03_22_2000-EX-10.8-HOSTING AGREEMENT.txt` | WEBHELPCOMINC (EX-10.8) | eGain Communications Corporation |
| `garman-license-maintenance` | `SPARKLINGSPRINGWATERHOLDINGSLTD_07_03_2002-EX-10.13-SOFTWARE LICENSE AND MAINTENANCE AGREEMENT.txt` | SPARKLINGSPRINGWATERHOLDINGSLTD (EX-10.13) | Garman Routing Systems, Inc. |
| `jhu-patent-royalty` | `VirtuosoSurgicalInc_20191227_1-A_EX1A-6 MAT CTRCT_11933379_EX1A-6 MAT CTRCT_License Agreement.txt` | VIRTUOSO SURGICAL, INC. (1-A) | The Johns Hopkins University |
| `ssd-app-development` | `PelicanDeliversInc_20200211_S-1_EX-10.3_11975895_EX-10.3_Development Agreement2.txt` + `...Development Agreement1.txt` | PELICAN DELIVERS, INC. (S-1, EX-10.3) | DOT COM LLC, OBA Seattle Software Developers |
| `airsopure-franchise` | `AIRTECHINTERNATIONALGROUPINC_05_08_2000-EX-10.4-FRANCHISE AGREEMENT.txt` | AIRTECHINTERNATIONALGROUPINC (EX-10.4) | Airsopure International Group, Inc. |
| `fcc-terpene-supply` | `FLOTEKINDUSTRIESINCCN_05_09_2019-EX-10.1-SUPPLY AGREEMENT.txt` | FLOTEKINDUSTRIESINCCN (EX-10.1) | Florida Chemical Company, LLC |

`ssd-app-development` joins two CUAD files from one exhibit. `Development Agreement2` is the agreement body, and `Development Agreement1` is its Statement of Work (Appendix A), which holds the fee and milestone schedule. `airsopure-franchise` is the unsigned form agreement from the filing, so the franchisee is unnamed.

## How the clauses were made

`scripts/import_cuad.py` splits each CUAD text file on its section numbering and headings, drops page footers, page numbers and blank form lines, and keeps the clause text verbatim. It splits any clause over 2,500 characters and numbers clauses `c-001`, `c-002`, and so on. Rerunning it against the same CUAD files reproduces the clause ids exactly. The case metadata (title, parties, why the case is hard) was written by hand.

## How the labels were made

Each `reference.json` is a hand-labeled draft made by reading the full contract text and applying ASC 606 from the seller's side. It is not the filer's own accounting, and the filers' actual revenue policies were not consulted. Where the contract supports more than one reading, the rationale says "judgment call" and names the alternative. All labels carry `"status": "draft"` until a human reviewer signs off. `scripts/check_cases.py` validates every case against `sixohsix/schema.py` and confirms that each cited clause id exists.
