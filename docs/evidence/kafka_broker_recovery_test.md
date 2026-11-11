# AtmoSync — Kafka Broker Recovery and Reliability Test

**Test date:** 11 November 2026  
**Component owner:** Aditya Singh Bisht  
**Component:** Python IoT Simulator and Apache Kafka  
**Environment:** Windows, Docker Desktop, Apache Kafka 4.4.0, Python 3.12.16  
**Test topic:** `atmosync_recovery_test`  
**Test status:** PASS

## 1. Objective

The objective was to verify that the AtmoSync Kafka environment could recover from a broker container restart, retain previously published messages and accept and deliver new messages after recovery.

A separate test topic, `atmosync_recovery_test`, was used to avoid interfering with the primary project telemetry topic, `container_sensor_telemetry`.

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
| Kafka storage | Persistent Docker volume at `/var/lib/kafka/data` |
| Consumer offset management | Manual |

## 3. Broker Restart and Message Persistence Test

### Procedure

1. Verified that the Kafka broker was running and the isolated recovery topic was available.
2. Published a baseline JSON message before restarting the broker.
3. Consumed the baseline message and confirmed successful retrieval.
4. Restarted the existing Kafka container using `docker restart atmosync-kafka`.
5. Confirmed that the container returned to the running state.
6. Verified that the recovery topic and its partition were available after restart.
7. Consumed the original baseline message again and confirmed that it remained stored.
8. Published a second JSON message after broker recovery.
9. Consumed both the original and newly published messages successfully.

### Results

| Test case | Expected behaviour | Actual result | Status |
|---|---|---|---|
| Initial broker availability | Broker responds to Kafka commands | Broker responded successfully | PASS |
| Baseline message publishing | Kafka accepts the original message | Original message published | PASS |
| Baseline message consumption | Original message is retrievable | Original message consumed successfully | PASS |
| Broker restart | Docker container restarts successfully | Container restarted successfully | PASS |
| Topic availability after restart | Recovery topic remains available | Topic and partition were available | PASS |
| Original message persistence | Previously stored message remains accessible | Original message survived restart | PASS |
| New message accepted | Broker accepts a new message after recovery | New message published successfully | PASS |
| Both messages consumed after restart | Original and new records are readable | Both messages retrieved successfully | PASS |

### Message verification

**Original message:**

```json
{
  "test_id": "recovery-before-20261111-01",
  "stage": "before_restart",
  "message": "baseline"
}
```

**New message published after broker recovery:**

```json
{
  "test_id": "recovery-after-20261111-01",
  "stage": "after_restart",
  "message": "recovery_success"
}
```

The console consumer subsequently retrieved both messages from the beginning of the isolated test topic.

**Result: PASS**

## 4. Python Producer and Consumer Verification

The Python Kafka client was tested independently against the recovered broker.

A structured telemetry event was generated containing:

- UUID event identifier.
- Container identifier.
- UTC timestamp.
- Temperature.
- Relative humidity.
- Vibration.
- Latitude and longitude.
- Synthetic source type.

The standalone Python producer successfully published the event, and the Python consumer retrieved the matching event.

The project's actual `TelemetryProducer` class was also tested separately. It successfully published an event and received broker acknowledgement.

The producer was subsequently updated to use `JsonSerializer` and `DefaultSerializer` from `kafka-python`, removing the earlier serializer deprecation warnings.

**Result: PASS**

## 5. Live Python Consumer Recovery Test

A separate live experiment verified the behaviour of the updated Python consumer while Kafka was restarted.

### Test sequence

1. Started the Python consumer using a fresh consumer group: `atmosync_live_recovery_20261111_04`.
2. Published a message before the broker interruption.
3. Confirmed that the running Python consumer received and processed the original message.
4. Restarted the Kafka Docker container while the same Python consumer process remained active.
5. Observed transient Kafka connection errors.
6. Confirmed that the consumer applied exponential backoff.
7. Published a new message after the broker became available.
8. Confirmed that the same Python consumer resumed processing without manual process restart.

### Observed connection recovery

The consumer encountered three transient socket disconnections.

| Retry attempt | Observed delay |
|---|---:|
| Attempt 1 | 1 second |
| Attempt 2 | 2 seconds |
| Attempt 3 | 4 seconds |

After the broker became available, the consumer successfully processed the second message.

### Live test message identifiers

**Before restart:** `bond-before-04`

**After restart:** `bond-after-04`

### Final Python consumer summary

| Metric | Result |
|---|---:|
| Messages received | 2 |
| Messages processed | 2 |
| Messages rejected | 0 |

**Live consumer recovery result: PASS**

The experiment demonstrated that the same Python consumer process recovered from temporary broker disconnections and resumed message processing.

## 6. Error Handling and Reliability Improvements

The Python Kafka implementation was refined to include:

- Persistent polling through the Kafka consumer `poll()` interface.
- Configurable Kafka connection backoff.
- Application-level exponential retry delays.
- Configurable retry limits.
- Handling of retriable and non-retriable Kafka errors.
- Graceful consumer shutdown.
- Manual offset commits after processing or explicitly rejecting a message.
- Bounded retries for transient offset-commit failures.
- Updated Kafka producer serializer classes.

Malformed JSON messages follow an explicit reject-and-skip policy. Their offsets are committed after rejection to prevent repeated blocking. A dead-letter queue has not yet been implemented.

## 7. Automated Test Results

The automated consumer tests were expanded to cover:

- Valid message processing and manual offset commits.
- Malformed JSON handling.
- Consumer message limits.
- Temporary broker connection failures.
- Exponential backoff and retry limits.
- Non-retriable Kafka errors.
- Invalid reconnect configurations.
- Temporary offset-commit failures.
- Permanent offset-commit failures.

### Final test results

| Test category | Result |
|---|---|
| Consumer-specific tests | 10 passed |
| Complete project test suite | 31 passed |
| Failed tests | 0 |
| Python syntax verification | PASS |
| Git whitespace verification | PASS |

**Overall automated testing result: PASS**

## 8. Screenshots and Supporting Evidence

The following screenshots correspond to the live broker-recovery experiment performed on 11 November 2026.

| Screenshot | Evidence provided |
|---|---|
| `kafka_broker_restart.png` | Shows the pre-restart message publishing command and Kafka Docker container restart |
| `kafka_broker_readiness.png` | Shows the broker readiness verification and successful recovery confirmation |
| `kafka_live_consumer_recovery.png` | Shows the before-and-after messages, three reconnect attempts, exponential backoff and final consumer summary |

The live consumer screenshot contains the matching test identifiers `bond-before-04` and `bond-after-04`, connecting the observed recovery behaviour to the documented experiment.

Together, the screenshots provide supporting visual evidence for the broker restart, broker readiness and successful live consumer recovery.

## 9. Limitations and Observations

1. The Kafka environment uses a single broker and replication factor 1. High availability and automatic replica failover have not been tested.
2. Message persistence was verified across a normal Docker container restart using the existing persistent local data volume. Permanent disk failure or Docker host failure protection has not been demonstrated.
3. The live test used an isolated recovery topic and a dedicated consumer group, leaving the main telemetry topic and existing team consumer offsets undisturbed.
4. Producer publishing during an active broker outage has not yet been tested independently.
5. Consumer processing provides at-least-once delivery behaviour rather than an exactly-once guarantee. Messages may be processed again if processing succeeds but offset commitment fails.
6. Malformed JSON messages are rejected and skipped rather than forwarded to a dead-letter queue.
7. The live recovery test demonstrates the behaviour of the Python consumer after a temporary broker interruption; it does not establish production-scale throughput or high availability.

## 10. Overall Test Conclusion

**OVERALL RESULT: PASS**

The Kafka broker restart and recovery experiment completed successfully.

The original message remained available after the broker restart, the recovery topic was accessible, and a new message was accepted and consumed successfully after recovery.

The live Python consumer also demonstrated successful reconnection behaviour. It processed one message before the interruption, experienced three transient connection failures, applied exponential backoff and processed another message after Kafka recovered.

The final live consumer result was:

- Messages received: 2
- Messages processed: 2
- Messages rejected: 0

The updated implementation was additionally verified through 31 passing automated tests.

The experiment establishes successful recovery from a temporary broker interruption in the tested single-broker Docker environment, subject to the limitations documented above.

**Prepared by:** Aditya Singh Bisht  
**Branch:** `Aditya-Singh-Bisht`  
**Evidence location:** `docs/evidence/`