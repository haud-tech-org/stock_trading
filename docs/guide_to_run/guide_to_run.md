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
python3 -m src.tools.centralized_report_generator.individual_trade_simulator \
  --execution-symbol VN30F1M \
  --alert-sources VN30 VN30F1M \
  --date 2026-01-06
```

## Consolidate simulation reports categorized by approach
```sh
python3 src/tools/centralized_report_generator/consolidate_reports.py --symbol 41I1FB000 --mode deployment --from-date 2026-01-06 --to-date 2026-01-07
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
python3 src/tools/centralized_report_generator/support_resistance_detector.py --symbols VN30 VN30F1M --start-time "2025-11-01 09:00:00" --end-time "2025-12-31 14:30:00" --resolution 15 --min-touches 3 --update-settings
```

## Update suggested price for alert notification files
### Command
```sh
python3 src/tools/maintenance/update_alert_field.py \
    --field performance_suggested_price \
    --from_date 2026-01-05 \
    --to_date 2026-01-08
```

```sh
py \
    --field structural_suggested_price \
    --from_date 2026-01-05 \
    --to_date 2026-01-08
```

## Centralized report generator
### Command for all tasks
```sh
python3 -m src.tools.centralized_report_generator.centralized_report_generator \
    --execution-symbol VN30F1M \
    --alert-sources VN30 VN30F1M \
    --from-date 2026-01-05 \
    --to-date 2026-01-05 \
    --mode deployment \
    --run-sr-detector \
    --sr-start-time "2026-01-01 09:00:00" \
    --sr-end-time "2026-01-15 15:00:00" \
    --sr-resolution 15 \
    --sr-min-touches 3 \
    --suggestion-type all \
    --update-price-alert-settings
```

### Only report generators
```sh
python3 -m src.tools.centralized_report_generator.centralized_report_generator \
    --execution-symbol VN30F1M \
    --alert-sources VN30 VN30F1M \
    --from-date 2026-01-05 \
    --to-date 2026-01-15 \
    --mode deployment \
    --update-price-alert-settings
```


