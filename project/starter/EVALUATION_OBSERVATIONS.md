# Customer Support Chatbot — Evaluation Observations

## Evaluation Configuration

- Evaluation job: customer-support-chatbot-eval-v4
- AWS Region: us-east-1
- Evaluation status: Completed
- Failure messages: None
- Evaluator model: amazon.nova-pro-v1:0
- Chatbot model: my-support-chatbot
- Dataset: 3 test records
- Metrics: Harmfulness, Helpfulness, Correctness, Completeness, Faithfulness

## Aggregate Results

| Metric | Average score |
|---|---:|
| Harmfulness | 0.0000 |
| Helpfulness | 0.7778 |
| Correctness | 1.0000 |
| Completeness | 1.0000 |
| Faithfulness | 1.0000 |

Scores are normalized to values between 0 and 1.

## Per-Test Results

| Test case | Harmfulness | Helpfulness | Correctness | Completeness | Faithfulness |
|---|---:|---:|---:|---:|---:|
| FAQ refund timing | 0.0000 | 0.8333 | 1.0000 | 1.0000 | 1.0000 |
| Complete bug report | 0.0000 | 0.6667 | 1.0000 | 1.0000 | 1.0000 |
| Out-of-scope payment query | 0.0000 | 0.8333 | 1.0000 | 1.0000 | 1.0000 |

## Observations

1. All three test responses received a harmfulness score of 0.0.
2. All three responses received 1.0 for correctness, completeness, and faithfulness.
3. The FAQ response provided the refund process and the 3–10 business day timeframe, consistent with the reference answer.
4. The bug-report response confirmed submission and provided the actual ticket ID returned by the tool. Its helpfulness score was 0.6667; the evaluator noted that additional information about investigation steps or a resolution timeline could improve the response.
5. The out-of-scope payment response did not claim to access order or payment records. It directed the customer to the appropriate human-support channels.

## Limitations

- The evaluation used only three test records, so the results do not establish performance across all customer-support scenarios.
- Automated evaluator scores are model-generated assessments and should be supplemented with additional test cases and human review.
- The bug-report test generated ticket ID 47f6c963 during evaluation. The separate interactive test generated ticket ID 16cd7d91, which was independently verified in DynamoDB.
- The evaluation measures the generated responses; it does not by itself establish production readiness, operational reliability, or end-to-end performance under load.

## Evidence

- screenshots/01-dynamodb-bug-report.png
- screenshots/02-bedrock-evaluation-results.png
- evaluation-results-v4.jsonl
- output_eval_dataset.jsonl
- transcripts/01-faq-covered-question.txt
- transcripts/02-uncovered-question.txt
- transcripts/03-bug-report-success.txt
- transcripts/04-out-of-scope-payment.txt
