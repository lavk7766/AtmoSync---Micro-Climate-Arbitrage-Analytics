# AtmoSync Alert Design

## 1. Temperature Alerts
- Monitor container temperature.
- Trigger an alert when temperature crosses the team-approved threshold.
- Record sensor ID, timestamp and measured temperature.

## 2. Humidity Alerts
- Monitor relative humidity.
- Trigger an alert when humidity crosses the approved threshold.
- Record sensor ID, timestamp and measured humidity.

## 3. Sensor Data Alerts
- Detect missing or delayed sensor readings.
- Flag sensors that stop transmitting data.

## 4. Vibration Alerts
- Planned for future integration.
- Requires vibration sensor data and approved thresholds.

## 5. Alert Workflow
1. Receive processed sensor data.
2. Evaluate approved alert conditions.
3. Generate an alert event.
4. Send notification through the team-approved channel.
5. Record alert status for monitoring.

## 6. Team Responsibilities
- Dashboard and alert developer: Propose thresholds and implement alert logic.
- Team / Backend / DevOps: Decide notification channel and provide credentials.
- Dashboard and alert developer: Implement notification integration after approval.

## 7. Pending Decisions
- Temperature and humidity thresholds.
- Missing-data timeout.
- Notification channel (Slack or email).
- Notification credentials and ownership.
