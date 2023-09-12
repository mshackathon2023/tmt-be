import logging
import azure.functions as func
import uuid
import json

ProcessTopic = func.Blueprint()


@ProcessTopic.function_name(name="processtopic")
@ProcessTopic.service_bus_topic_trigger(arg_name="message", 
                            #    topic_name="SERVICEBUS_TOPIC_NAME", 
                               connection="SERVICEBUS_CONNECTION_STRING", 
                                topic_name="newDocument",
                                subscription_name="process_topic",
                            #    subscription_name="SERVICEBUS_SUBSCRIPTION_NAME"
                               )
def processtopic(message: func.ServiceBusMessage) -> func.HttpResponse:
    logging.info('Python ServiceBus trigger function processed a request.')

    try:
        message_body = message.get_body().decode("utf-8")
        logging.info("Python ServiceBus topic trigger processed message.")
        logging.info("Message Body: " + message_body)

    except ValueError:
        return func.HttpResponse(
             "Vaule Error",
             status_code=400
        )

    # Generate a unique ID for the new document
    guid = str(uuid.uuid4())

    # # Store raw document in Cosmos DB
    # rawDocuments.set(func.Document.from_dict({"id":guid, "text": text}))

    # # Create new topic record in Cosmos DB
    # topics.set(func.Document.from_dict({"id":guid, "state": "pending"}))

    # # Send message to Service Bus
    # message.set(json.dumps({"topic": guid}))

    return func.HttpResponse(
        json.dumps({"topic": guid, "state":"assessing"}),
        headers = {"Content-Type": "application/json"},
        status_code=202
    )