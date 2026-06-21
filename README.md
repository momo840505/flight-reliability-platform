# U.S. Flight Reliability and Delay Intelligence Platform

An end-to-end data analytics and machine learning project analysing
the reliability of domestic flights in the United States.

## Project Goals

This project aims to:

- Build a reproducible flight data pipeline
- Validate and clean official aviation data
- Create a PostgreSQL analytical data warehouse
- Analyse airlines, airports, routes and delay causes
- Develop an interactive Power BI dashboard
- Predict whether a flight will arrive at least 15 minutes late

## Planned Architecture

BTS Raw Data
→ Python Validation
→ Data Cleaning
→ Parquet Staging
→ PostgreSQL Data Warehouse
→ SQL Analytics
→ Power BI Dashboard
→ Machine Learning Model

## Technology Stack

- Python
- Pandas
- PyArrow
- PostgreSQL
- SQL
- Power BI
- Scikit-learn
- Pytest
- Git and GitHub

## Current Status

- [x] Project structure created
- [x] Python virtual environment configured
- [x] Pilot dataset downloaded
- [x] Raw data profiling completed
- [x] Raw data quality validation completed
- [x] Data cleaning pipeline completed
- [x] Cleaned Parquet dataset created
- [x] PostgreSQL connection configured
- [x] Star schema created
- [x] Warehouse loading pipeline completed
- [x] Warehouse validation completed
- [x] SQL analytics views created
- [x] Power BI dashboard created
- [ ] Dashboard screenshots added to README
- [ ] Delay prediction model created