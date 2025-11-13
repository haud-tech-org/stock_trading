# GUIDE TO RUN

## Run alert management
```sh
exec caffeinate -i python3 -m src.stockreports.alert.symbol_alert_manager
```

## Simulation reports
```sh
python3 -m src.tools.consolidated_profitability_simulator \
  --execution-symbol 41I1FB000 \
  --alert-sources VN30 41I1FB000 \
  --date 2025-10-30
```

## Individual simulation reports
```sh
python3 -m src.tools.individual_trade_simulator \
  --execution-symbol 41I1FB000 \
  --alert-sources VN30 41I1FB000 \
  --date 2025-11-03
```

## Consolidate simulation reports categorized by approach
```sh
python3 src/tools/consolidate_reports.py --symbol 41I1FB000 --mode deployment --from-date 2025-11-11 --to-date 2025-11-11
```


  