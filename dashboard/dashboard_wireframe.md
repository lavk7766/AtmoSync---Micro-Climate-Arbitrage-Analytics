# AtmoSync Dashboard Wireframe

## Section 1: Overview
- Total Sensors
- Average Temperature
- Average Humidity
- Data Quality Status

## Section 2: Climate Monitoring
- Temperature Trend: Time-series line chart
- Humidity Trend: Time-series line chart
- Sensor Comparison: Bar chart
- Temperature vs Humidity: Scatter plot

## Section 3: Cold-Chain Analytics
- Product Temperature (TP): Line chart
- Refrigerator Zone Comparison: Bar chart
- Temperature Exposure: Risk indicator

## Section 4: Market Analytics
- Commodity Price Trend: Line chart
- Monthly Price Change: Bar chart
- Commodity Price Volatility: Trend chart

## Section 5: Alerts and Risk
- Temperature Threshold Alerts
- Humidity Threshold Alerts
- Missing Sensor Data Alerts
- Vibration Alerts (after data integration)

## Dashboard Filters
- Date Range
- Sensor ID
- Commodity
- Refrigerator Type

## Implementation Notes
- Build charts using verified dataset fields.
- Keep household refrigerator analytics separate from container telemetry.
- Do not display vibration as measured until suitable data is available.
- Alert thresholds require team approval.
- Actual arbitrage calculations require local market prices and cost data.
