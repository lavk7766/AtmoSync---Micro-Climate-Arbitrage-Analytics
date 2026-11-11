# AtmoSync — Kafka Broker Recovery and Reliability Test

**Test date:** 11 November 2026  
**Component:** Python IoT Simulator and Apache Kafka  
**Owner:** Aditya Singh Bisht  
**Test environment:** Windows, Docker Desktop, Apache Kafka 4.4.0, Python 3.12.16

## 1. Objective

Verify whether the AtmoSync Kafka environment can recover from a broker container restart while retaining previously published messages and accepting new messages.

A separate Kafka topic, `atmosync_recovery_test`, was used to avoid interfering with the project's primary telemetry topic.

## 2. Test Environment

| Component | Configuration |
|---|---|
| Kafka container | `atmosync-kafka` |
| Kafka image | `apache/kafka:4.4.0` |
| Bootstrap server | `localhost:9092` |
| Test topic | `atmosync_recovery_test` |
| Partition count | 1 |
| Replication factor | 1 |
| Docker restart policy | `unless-stopped` |
| Kafka data volume | Mounted at `/var/lib/kafka/data` |

## 3. Broker Restart and Message Persistence Test

### Procedure

1. Verified that Kafka was running and the isolated recovery topic was available.
2. Published a baseline JSON message before restarting the broker.
3. Consumed the baseline message and confirmed successful retrieval.
4. Restarted the existing Kafka Docker container using `docker restart atmosync-kafka`.
5. Verified that the Kafka container returned to the running state.
6. Verified that the recovery topic was still available.
7. Consumed the original baseline message after restarting Kafka.
8. Published a second message after broker recovery.
9. Consumed both messages successfully.

### Results

| Test | Result |
|---|---|
| Baseline message published | PASS |
| Baseline message consumed | PASS |
| Kafka container restarted | PASS |
| Recovery topic remained available | PASS |
| Original message survived restart | PASS |
| New message accepted