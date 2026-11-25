# Kafka Sustained-Load Benchmark

**Date:** 2026-11-25 | **Branch:** Aditya-Singh-Bisht
**Test type:** Controlled application-level sustained-load benchmark

## 1. Objective

Evaluate whether the AtmoSync application Kafka producer and consumer can process a controlled stream of telemetry events at a target rate of 50 events per second.

## 2. Test isolation and configuration

- Topic: `atmosync_aditya_sustained_20261125`
- Consumer group: `atmosync-aditya-sustained-20261125`
- Partitions: 1
- Target event count: 1,000
- Target producer rate: 50 events/second
- Initial topic end offset: 0
- Initial committed consumer offset: None
- Producer: Existing application `TelemetryProducer`
- Consumer: Existing application consumer implementation

The test used a dedicated topic and consumer group rather than the normal project telemetry topic.

## 3. Results

| Metric | Result |
|---|---:|
| Messages produced | 1,000 |
| Messages received | 1,000 |
| Messages processed | 1,000 |
| Messages rejected | 0 |
| Duplicate event IDs | 0 |
| Producer duration | 19.993 seconds |
| Consumer processing duration | 19.854 seconds |
| Overall duration | 20.025 seconds |
| Producer throughput | 50.02 events/second |
| Consumer throughput | 50.37 events/second |
| Overall throughput | 49.94 events/second |
| Mean event-to-consumer latency | 9.91 ms |
| P50 latency | 6.76 ms |
| P95 latency | 35.88 ms |
| P99 latency | 58.46 ms |
| Maximum sampled committed lag | 2 records |
| Lag sampling interval | Every 25 records |
| Final committed offset | 1,000 |
| Final topic end offset | 1,000 |
| Final consumer lag | 0 |

## 4. Outcome

**PASS**

All 1,000 produced events were received and processed. No events were rejected, and no duplicate event IDs were detected during this run.

The consumer kept pace with the producer at approximately 50 events per second. The final committed offset matched the final topic end offset, leaving zero records of consumer lag.

## 5. Scope and limitations

This result applies only to the tested local environment and workload.

- The test used one Kafka broker and one topic partition.
- The producer was paced at 50 events per second; maximum sustainable throughput was not established.
- Lag was sampled every 25 processed records, so the reported maximum is a sampled observation.
- This test did not simulate broker failure, network interruption, or consumer crashes during the sustained-load run.
- The result does not establish production-scale capacity or availability.

## 6. Conclusion

The existing AtmoSync application producer and consumer successfully completed a controlled 1,000-event sustained-load test at the target rate of 50 events per second, with zero rejects, zero detected duplicate event IDs, and zero final consumer lag.
