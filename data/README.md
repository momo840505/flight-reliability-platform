# Data Source

## Airline On-Time Performance Data

This project uses the Airline On-Time Performance Data published by the
U.S. Department of Transportation, Bureau of Transportation Statistics.

Dataset table:

Reporting Carrier On-Time Performance (1987-present)

The dataset contains individual domestic flight records, including:

- Scheduled and actual departure times
- Scheduled and actual arrival times
- Departure and arrival delays
- Flight cancellations
- Flight diversions
- Taxi-in and taxi-out times
- Flight distance
- Causes of delay

## Pilot Dataset

The first development dataset contains flights from January 2024.

Expected raw file:

data/raw/flights_2024_01.csv

Raw data files are excluded from Git because of their size.

## Stable Identifiers

The following identifiers will be used for longitudinal analysis:

- DOT_ID_Reporting_Airline
- OriginAirportID
- DestAirportID