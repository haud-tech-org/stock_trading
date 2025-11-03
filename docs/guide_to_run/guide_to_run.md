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


  