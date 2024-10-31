from sinch import SinchClient

sinch_client = SinchClient(
    key_id="",
    key_secret="",
    project_id=""
)

send_batch_response = sinch_client.sms.batches.send(
    body="Hello from Sinch!",
    to=["+14062176239"],
    from_="+12067101062",
    delivery_report="none"
)

print(send_batch_response)

