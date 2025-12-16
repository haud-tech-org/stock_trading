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

## Extract historical data
```sh
python3 src/tools/extract_period_data.py \
    --input-file src/stockreports/data/VN30/vn30_response_251114.json \
    --start-time "13:40" \
    --end-time "13:58"
```

## Resistance and support levels of symbols

### path: src/tools/support_resistance_detector.py

### Command:
```sh
python3 src/tools/support_resistance_detector.py --symbols VN30 VN30F2512 --start-time "2025-11-01 09:00:00" --end-time "2025-12-15 14:30:00" --resolution 15 --min-touches 3 --update-settings
```


  