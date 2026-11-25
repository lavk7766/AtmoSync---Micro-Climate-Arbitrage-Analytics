# Kafka Consumer Restart and Recovery Validation

Date: 25 November 2026
Developer: Aditya
Branch: Aditya-Singh-Bisht

## Objective

Validate committed-offset recovery after a graceful consumer restart
and replay of uncommitted messages after an abrupt consumer termination.

## Test Environment

- Kafka broker: Docker, apache/kafka:4.4.0
- Topic: atmosync_aditya_consumer_restart_20261125
- Consumer group: atmosync-aditya-consumer-restart-20261125
- Partitions: 1
- Replication factor: 1
- Application consumer: kafka_client.consumer.consume_messages
- Producer: kafka_client.producer.TelemetryProducer

The test used a dedicated topic and consumer group.
The main telemetry topic was not modified.

## Test 1: Graceful Consumer Restart

1. Verified the topic was empty, with end offset 0.
2. Published 10 events at offsets 0-9.
3. Started consumer process A using the dedicated group.
4. Process A consumed and processed 10 events, with 0 rejected.
5. Verified the committed offset reached 10.
6. Closed process A gracefully.
7. Published another 10 events at offsets 10-19 while the consumer was stopped.
8. Verified the committed offset remained 10 and topic end offset became 20.
9. Started consumer process B using the same group.
10. Process B consumed and processed 10 events, with 0 rejected.
11. Verified final committed offset 20 and topic end offset 20.

Result: PASS.

The restarted consumer resumed from the previously committed offset.

## Test 2: Abrupt Termination Before Commit

1. Published one additional event at offset 20.

Event ID:
2bb0728d-1b9c-4b45-bcdb-9815ab1ca059

2. Verified committed offset 20 and topic end offset 21.
3. Started a separate Kafka consumer using the same group.
4. Received offset 20.
5. Deliberately terminated the process using os._exit(73), before processing or committing the event.
6. Verified committed offset remained 20 and topic end offset remained 21.
7. Restarted the existing application consumer using the same group.
8. The application consumer received the same event at offset 20.
9. It processed 1 message and rejected 0.
10. Verified final committed offset 21 and topic end offset 21.

Result: PASS.

The uncommitted message was replayed after abrupt termination and
subsequently committed by the application consumer.

## Overall Results

| Validation | Result |
|---|---|
| First batch consumption | 10 processed |
| Graceful process restart | PASS |
| Second batch consumption | 10 processed |
| Committed offset persistence | PASS |
| Abrupt process termination | Exit code 73 as intended |
| Uncommitted event replay | PASS |
| Final offset verification | 21 |
| Rejected messages | 0 |

## Interpretation and Limitations

The tests demonstrate at-least-once delivery behaviour with manual
offset commits.

They do not establish exactly-once processing. A downstream side
effect completed before an offset commit may be repeated after a crash.

The application consumer currently parses and prints events before
committing their offsets. Durable downstream side-effect idempotency
was not tested.

Multi-partition recovery, multi-consumer rebalancing, broker restart
during active processing and sustained-load performance remain
separate validation items.

No changes to the existing application consumer implementation
were required for these tests.

## Git

The test used a dedicated local Kafka topic and consumer group.
The main project telemetry topic was not modified.
