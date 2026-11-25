# Kafka Consumer-Group Rebalance Validation

Date: 25 November 2026
Developer: Aditya
Branch: Aditya-Singh-Bisht

## Objective

Validate Kafka consumer-group partition reassignment when consumers
join and leave a group, and verify successful message processing
after the group membership changes.

## Test Environment

- Kafka broker: Docker, apache/kafka:4.4.0
- Topic: atmosync_aditya_rebalance_20261125
- Consumer group: atmosync-aditya-rebalance-20261125
- Partitions: 2
- Replication factor: 1
- Broker count: 1
- Application consumer: kafka_client.consumer.consume_messages
- Producer: kafka-python KafkaProducer

The test used a dedicated topic and consumer group. The main
telemetry topic was not modified.

## Test 1: Topic Verification

- Topic creation confirmed.
- Partition 0 end offset: 0.
- Partition 1 end offset: 0.
- Both partitions had an online replica and leader.
- No offline replicas were reported.

Result: PASS.

## Test 2: Consumer-Group Partition Assignment

### Initial membership

Consumer A joined the group alone.

Observed assignment:
- Consumer A: partitions 0 and 1.

Result: PASS.

### Consumer B joins

Consumer B joined the same group.

Observed stable assignment:
- Consumer A: partition 0.
- Consumer B: partition 1.

The assignments were disjoint and covered both topic partitions.

Result: PASS.

### Consumer B leaves

Consumer B was closed gracefully.

Consumer A completed another rebalance and regained:
- Partition 0.
- Partition 1.

Result: PASS.

## Test 3: Message Processing After Rebalance

After Consumer B left and Consumer A regained both partitions,
12 test events were published:

- Partition 0: six events at offsets 0-5.
- Partition 1: six events at offsets 0-5.

The existing application consumer processed the messages.

Observed results:
- Messages received: 12.
- Messages processed: 12.
- Messages rejected: 0.

Result: PASS.

## Test 4: Final Offset Verification

Independent Kafka offset queries returned:

| Partition | Committed offset | End offset |
|---|---:|---:|
| 0 | 6 | 6 |
| 1 | 6 | 6 |

Both partitions were fully consumed and committed.

Result: PASS.

## Overall Results

- Two-partition topic creation and verification: PASS.
- Initial single-consumer assignment: PASS.
- Two-consumer partition distribution: PASS.
- Consumer departure and partition reassignment: PASS.
- Post-rebalance application processing: PASS.
- Final committed-offset reconciliation: PASS.
- Total events processed: 12.
- Rejected events: 0.

## Interpretation and Limitations

The test demonstrates Kafka consumer-group partition redistribution
when a second consumer joins and subsequently leaves the group.

It also demonstrates that the remaining application consumer can
process records from both partitions after reassignment.

The 12-message processing phase was performed after Consumer B
left the group. Simultaneous message processing by both consumer
instances was not measured in this test.

The environment used one Kafka broker and replication factor one.
Broker failure, multi-broker failover, forced consumer termination
during an active rebalance and sustained concurrent throughput
remain separate validation activities.

No changes to the application consumer implementation were needed.

The test does not establish exactly-once processing semantics.

## Git

All testing was performed using a dedicated local Kafka topic and
consumer group. No production telemetry topic was modified.
