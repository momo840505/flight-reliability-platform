# Data Source

I used the U.S. Department of Transportation Bureau of Transportation Statistics **Reporting Carrier On-Time Performance (1987-present)** dataset from TranStats.

For the current version, I downloaded January 2024 and kept the project to one month while I was building and testing the pipeline. The file still has 547,271 scheduled flight rows, so it was enough to test the cleaning, validation, warehouse load, and Power BI report without making every rerun too slow.

Expected local file:

```text
data/raw/flights_2024_01.csv
```

The raw CSV is not committed to Git. The extract I used has 48 selected source columns.

I kept the BTS IDs below because they are more stable than display names or codes if I later extend the project to more months:

- `OP_CARRIER_AIRLINE_ID`
- `ORIGIN_AIRPORT_ID`
- `DEST_AIRPORT_ID`

If I add more monthly files later, I also want to keep a small source manifest with the download date, query settings, row count, file size, and SHA-256 checksum for each extract.
